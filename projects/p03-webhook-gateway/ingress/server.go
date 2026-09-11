package ingress

import (
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"net/http"
	"time"
)

type Secrets struct {
	Stripe  string
	Shopify string
	GitHub  string
	Custom  string
}

type Server struct {
	Store   Store
	Secrets Secrets
	Now     func() time.Time
	Log     *slog.Logger
	mux     *http.ServeMux
}

func NewServer(store Store, secrets Secrets) *Server {
	s := &Server{
		Store:   store,
		Secrets: secrets,
		Log:     slog.New(slog.NewJSONHandler(io.Discard, nil)),
	}
	s.mux = http.NewServeMux()
	s.mux.HandleFunc("POST /hooks/{source}", s.handleHook)
	s.mux.HandleFunc("GET /healthz", s.handleHealthz)
	return s
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	s.mux.ServeHTTP(w, r)
}

func (s *Server) now() time.Time {
	if s.Now != nil {
		return s.Now()
	}
	return time.Now().UTC()
}

func (s *Server) handleHealthz(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) handleHook(w http.ResponseWriter, r *http.Request) {
	source := r.PathValue("source")
	if _, ok := allowedSources[source]; !ok {
		http.NotFound(w, r)
		return
	}

	r.Body = http.MaxBytesReader(w, r.Body, maxBodyBytes)
	body, err := io.ReadAll(r.Body)
	if err != nil {
		var maxErr *http.MaxBytesError
		if errors.As(err, &maxErr) {
			writeJSON(w, http.StatusRequestEntityTooLarge, map[string]string{"error": "too large"})
			return
		}
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid body"})
		return
	}

	if !s.verify(source, body, r.Header) {
		s.log().Info("bad signature", "source", source)
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "bad signature"})
		return
	}
	if !json.Valid(body) {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid json"})
		return
	}

	ev, ok := extractEvent(source, body, r.Header)
	if !ok {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "missing id"})
		return
	}

	inserted, err := s.Store.Insert(r.Context(), ev)
	if err != nil {
		s.log().Error("inbox insert", "source", source, "event_id", ev.ExternalEventID, "err", err.Error())
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"error": "unavailable"})
		return
	}
	result := "duplicate"
	if inserted {
		result = "new"
	}
	s.log().Info("inbox accepted",
		"source", source,
		"event_id", ev.ExternalEventID,
		"event_type", ev.EventType,
		"result", result,
	)
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok", "result": result})
}

func (s *Server) verify(source string, body []byte, h http.Header) bool {
	now := s.now()
	switch source {
	case "github":
		return validGitHub(body, h.Get(headerGitHubSignature), s.Secrets.GitHub)
	case "stripe":
		return validStripe(body, h.Get(headerStripeSignature), s.Secrets.Stripe, now)
	case "shopify":
		return validShopify(body, h.Get(headerShopifyHMAC), s.Secrets.Shopify)
	case "custom":
		return validCustom(body, h.Get(headerCustomTimestamp), h.Get(headerCustomSignature), s.Secrets.Custom, now)
	default:
		return false
	}
}

func (s *Server) log() *slog.Logger {
	if s.Log != nil {
		return s.Log
	}
	return slog.New(slog.NewJSONHandler(io.Discard, nil))
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}
