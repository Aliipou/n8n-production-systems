package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"math/rand/v2"
	"net/http"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"
)

const (
	routeGetItems    = "GET /items"
	routePostItems   = "POST /items"
	routePutItems    = "PUT /items"
	routeGetItemByID = "GET /items/{id}"
	headerRetryAfter = "Retry-After"
	contentTypeJSON  = "application/json"
	contentTypeText  = "text/plain; charset=utf-8"
	maxBodyBytes     = 1 << 20
)

var itemRoutes = []string{
	routeGetItems,
	routePostItems,
	routePutItems,
	routeGetItemByID,
}

type routeMode struct {
	ErrorRate   float64 `json:"error_rate"`
	Status      int     `json:"status"`
	LatencyMS   int     `json:"latency_ms"`
	RetryAfterS int     `json:"retry_after_s"`
	AuthFail    bool    `json:"auth_fail"`
}

type modeRequest struct {
	Route       string  `json:"route"`
	Method      string  `json:"method"`
	Path        string  `json:"path"`
	ErrorRate   float64 `json:"error_rate"`
	Status      int     `json:"status"`
	LatencyMS   int     `json:"latency_ms"`
	RetryAfterS int     `json:"retry_after_s"`
	AuthFail    bool    `json:"auth_fail"`
}

type modeStore struct {
	mu    sync.RWMutex
	modes map[string]routeMode
}

func newModeStore() *modeStore {
	return &modeStore{modes: make(map[string]routeMode)}
}

func (m *modeStore) set(route string, mode routeMode) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.modes[route] = mode
}

func (m *modeStore) get(route string) routeMode {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.modes[route]
}

func (m *modeStore) reset() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.modes = make(map[string]routeMode)
}

type statStore struct {
	mu     sync.Mutex
	counts map[string]uint64
}

func newStatStore() *statStore {
	return &statStore{counts: make(map[string]uint64)}
}

func (s *statStore) inc(route string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.counts[route]++
}

func (s *statStore) snapshot() map[string]uint64 {
	out := make(map[string]uint64, len(itemRoutes))
	for _, route := range itemRoutes {
		out[route] = 0
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	for route, n := range s.counts {
		out[route] = n
	}
	return out
}

func (s *statStore) reset() {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.counts = make(map[string]uint64)
}

type metricKey struct {
	route string
	code  string
}

type metricStore struct {
	mu     sync.Mutex
	counts map[metricKey]uint64
}

func newMetricStore() *metricStore {
	return &metricStore{counts: make(map[metricKey]uint64)}
}

func (m *metricStore) inc(route string, status int) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.counts[metricKey{route: route, code: strconv.Itoa(status)}]++
}

func (m *metricStore) reset() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.counts = make(map[metricKey]uint64)
}

func (m *metricStore) render() string {
	m.mu.Lock()
	keys := make([]metricKey, 0, len(m.counts))
	for k := range m.counts {
		keys = append(keys, k)
	}
	sort.Slice(keys, func(i, j int) bool {
		if keys[i].route != keys[j].route {
			return keys[i].route < keys[j].route
		}
		return keys[i].code < keys[j].code
	})
	var b strings.Builder
	b.WriteString("# HELP flaky_api_http_requests_total HTTP requests handled by flaky-api, labeled by route and status code.\n")
	b.WriteString("# TYPE flaky_api_http_requests_total counter\n")
	for _, k := range keys {
		fmt.Fprintf(&b, "flaky_api_http_requests_total{code=%q,route=%q} %d\n", k.code, k.route, m.counts[k])
	}
	m.mu.Unlock()
	return b.String()
}

type statusWriter struct {
	http.ResponseWriter
	status int
}

func (w *statusWriter) WriteHeader(code int) {
	w.status = code
	w.ResponseWriter.WriteHeader(code)
}

func (w *statusWriter) Write(b []byte) (int, error) {
	if w.status == 0 {
		w.status = http.StatusOK
	}
	return w.ResponseWriter.Write(b)
}

func (w *statusWriter) Unwrap() http.ResponseWriter {
	return w.ResponseWriter
}

type Server struct {
	log     *slog.Logger
	store   *store
	modes   *modeStore
	stats   *statStore
	metrics *metricStore
	mux     *http.ServeMux
}

func NewServer(log *slog.Logger) *Server {
	if log == nil {
		log = slog.New(slog.NewJSONHandler(io.Discard, nil))
	}
	s := &Server{
		log:     log,
		store:   newStore(),
		modes:   newModeStore(),
		stats:   newStatStore(),
		metrics: newMetricStore(),
		mux:     http.NewServeMux(),
	}
	s.mux.HandleFunc("GET /healthz", s.handleHealthz)
	s.mux.HandleFunc("GET /health", s.handleHealthz)
	s.mux.HandleFunc("GET /metrics", s.handleMetrics)
	s.mux.HandleFunc("POST /admin/mode", s.handleAdminMode)
	s.mux.HandleFunc("POST /admin/reset", s.handleAdminReset)
	s.mux.HandleFunc("GET /admin/stats", s.handleAdminStats)
	s.mux.HandleFunc("GET /items", s.withFaults(routeGetItems, s.handleListItems))
	s.mux.HandleFunc("POST /items", s.withFaults(routePostItems, s.handleCreateItem))
	s.mux.HandleFunc("PUT /items", s.withFaults(routePutItems, s.handlePutItem))
	s.mux.HandleFunc("GET /items/{id}", s.withFaults(routeGetItemByID, s.handleGetItem))
	return s
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	defer func() {
		if rec := recover(); rec != nil {
			s.log.Error("panic", "err", fmt.Sprint(rec))
			writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal error"})
		}
	}()
	s.mux.ServeHTTP(w, r)
}

func (s *Server) withFaults(route string, next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		s.stats.inc(route)
		sw := &statusWriter{ResponseWriter: w}
		mode := s.modes.get(route)
		if mode.LatencyMS > 0 {
			time.Sleep(time.Duration(mode.LatencyMS) * time.Millisecond)
		}
		if mode.AuthFail {
			writeJSON(sw, http.StatusUnauthorized, map[string]string{"error": "unauthorized"})
			s.observe(route, sw.status, start)
			return
		}
		if shouldFail(mode) {
			status := mode.Status
			if status == 0 {
				status = http.StatusInternalServerError
			}
			if mode.RetryAfterS > 0 {
				sw.Header().Set(headerRetryAfter, strconv.Itoa(mode.RetryAfterS))
			}
			writeJSON(sw, status, map[string]string{"error": http.StatusText(status)})
			s.observe(route, sw.status, start)
			return
		}
		next(sw, r)
		s.observe(route, sw.status, start)
	}
}

func (s *Server) observe(route string, status int, start time.Time) {
	if status == 0 {
		status = http.StatusOK
	}
	s.metrics.inc(route, status)
	s.log.Info("request",
		"route", route,
		"status", status,
		"duration_ms", time.Since(start).Milliseconds(),
	)
}

func shouldFail(mode routeMode) bool {
	if mode.ErrorRate < 0 {
		return false
	}
	if mode.ErrorRate > 0 {
		if mode.ErrorRate >= 1 {
			return true
		}
		return rand.Float64() < mode.ErrorRate
	}
	return mode.Status != 0
}

func (s *Server) handleHealthz(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) handleMetrics(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", contentTypeText)
	w.WriteHeader(http.StatusOK)
	_, _ = io.WriteString(w, s.metrics.render())
}

func (s *Server) handleAdminMode(w http.ResponseWriter, r *http.Request) {
	var req modeRequest
	if err := decodeJSON(r, &req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}
	route, err := normalizeRoute(req)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}
	if req.ErrorRate < 0 || req.ErrorRate > 1 {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "error_rate must be between 0 and 1"})
		return
	}
	if req.LatencyMS < 0 {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "latency_ms must be >= 0"})
		return
	}
	if req.RetryAfterS < 0 {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "retry_after_s must be >= 0"})
		return
	}
	if req.Status != 0 && (req.Status < 100 || req.Status > 599) {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "status must be a valid HTTP status"})
		return
	}
	s.modes.set(route, routeMode{
		ErrorRate:   req.ErrorRate,
		Status:      req.Status,
		LatencyMS:   req.LatencyMS,
		RetryAfterS: req.RetryAfterS,
		AuthFail:    req.AuthFail,
	})
	s.log.Info("mode set", "route", route, "status", req.Status, "error_rate", req.ErrorRate)
	writeJSON(w, http.StatusOK, map[string]any{"ok": true, "route": route})
}

func (s *Server) handleAdminReset(w http.ResponseWriter, _ *http.Request) {
	s.modes.reset()
	s.stats.reset()
	s.metrics.reset()
	s.store.reset()
	s.log.Info("reset")
	writeJSON(w, http.StatusOK, map[string]bool{"ok": true})
}

func (s *Server) handleAdminStats(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"request_counts": s.stats.snapshot()})
}

func (s *Server) handleListItems(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"items": s.store.list()})
}

func (s *Server) handleCreateItem(w http.ResponseWriter, r *http.Request) {
	item, err := decodeItem(r)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}
	created, err := s.store.create(item)
	if errors.Is(err, errConflict) {
		writeJSON(w, http.StatusConflict, map[string]string{"error": "item already exists"})
		return
	}
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}
	writeJSON(w, http.StatusCreated, created)
}

func (s *Server) handlePutItem(w http.ResponseWriter, r *http.Request) {
	item, err := decodeItem(r)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}
	updated, err := s.store.upsert(item)
	if errors.Is(err, errMissingID) {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "id is required"})
		return
	}
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, updated)
}

func (s *Server) handleGetItem(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	if id == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "id is required"})
		return
	}
	item, ok := s.store.get(id)
	if !ok {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "not found"})
		return
	}
	writeJSON(w, http.StatusOK, item)
}

func normalizeRoute(req modeRequest) (string, error) {
	route := strings.TrimSpace(req.Route)
	if route == "" {
		method := strings.ToUpper(strings.TrimSpace(req.Method))
		path := strings.TrimSpace(req.Path)
		if method == "" || path == "" {
			return "", fmt.Errorf("route is required")
		}
		route = method + " " + path
	}
	parts := strings.Fields(route)
	if len(parts) != 2 {
		return "", fmt.Errorf("route must be METHOD /path")
	}
	route = strings.ToUpper(parts[0]) + " " + parts[1]
	for _, known := range itemRoutes {
		if route == known {
			return route, nil
		}
	}
	return "", fmt.Errorf("unknown route %q", route)
}

func decodeJSON(r *http.Request, dest any) error {
	defer r.Body.Close()
	dec := json.NewDecoder(io.LimitReader(r.Body, maxBodyBytes))
	if err := dec.Decode(dest); err != nil {
		return fmt.Errorf("invalid JSON: %w", err)
	}
	return nil
}

func decodeItem(r *http.Request) (map[string]any, error) {
	var item map[string]any
	if err := decodeJSON(r, &item); err != nil {
		return nil, err
	}
	if item == nil {
		return nil, fmt.Errorf("object required")
	}
	return item, nil
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", contentTypeJSON)
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}
