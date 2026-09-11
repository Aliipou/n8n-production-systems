package main

import (
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"
)

func testServer() *Server {
	return NewServer(slog.New(slog.NewJSONHandler(io.Discard, nil)))
}

func doRequest(t *testing.T, h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	var rdr io.Reader
	if body != "" {
		rdr = strings.NewReader(body)
	}
	req := httptest.NewRequest(method, path, rdr)
	if body != "" {
		req.Header.Set("Content-Type", contentTypeJSON)
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func decodeBody(t *testing.T, rec *httptest.ResponseRecorder) map[string]any {
	t.Helper()
	var out map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &out); err != nil {
		t.Fatalf("decode body: %v (%s)", err, rec.Body.String())
	}
	return out
}

func TestHealthz(t *testing.T) {
	s := testServer()
	tests := []struct {
		name   string
		path   string
		want   int
		status string
	}{
		{name: "healthz", path: "/healthz", want: http.StatusOK, status: "ok"},
		{name: "health alias", path: "/health", want: http.StatusOK, status: "ok"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := doRequest(t, s, http.MethodGet, tt.path, "")
			if rec.Code != tt.want {
				t.Fatalf("status %d, want %d", rec.Code, tt.want)
			}
			got := decodeBody(t, rec)
			if got["status"] != tt.status {
				t.Fatalf("body %#v", got)
			}
		})
	}
}

func TestAdminModeValidation(t *testing.T) {
	s := testServer()
	tests := []struct {
		name string
		body string
		want int
	}{
		{name: "missing route", body: `{"status":500}`, want: http.StatusBadRequest},
		{name: "unknown route", body: `{"route":"DELETE /items","status":500}`, want: http.StatusBadRequest},
		{name: "bad error_rate", body: `{"route":"POST /items","error_rate":1.5}`, want: http.StatusBadRequest},
		{name: "negative latency", body: `{"route":"POST /items","latency_ms":-1}`, want: http.StatusBadRequest},
		{name: "negative retry_after", body: `{"route":"POST /items","retry_after_s":-1}`, want: http.StatusBadRequest},
		{name: "bad status", body: `{"route":"POST /items","status":999}`, want: http.StatusBadRequest},
		{name: "invalid json", body: `{`, want: http.StatusBadRequest},
		{name: "ok route field", body: `{"route":"POST /items","status":500,"error_rate":1}`, want: http.StatusOK},
		{name: "ok method path", body: `{"method":"GET","path":"/items/{id}","auth_fail":true}`, want: http.StatusOK},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := doRequest(t, s, http.MethodPost, "/admin/mode", tt.body)
			if rec.Code != tt.want {
				t.Fatalf("status %d, want %d body %s", rec.Code, tt.want, rec.Body.String())
			}
		})
	}
}

func TestItemsCRUD(t *testing.T) {
	s := testServer()

	list := doRequest(t, s, http.MethodGet, "/items", "")
	if list.Code != http.StatusOK {
		t.Fatalf("list status %d", list.Code)
	}
	if got := decodeBody(t, list)["items"].([]any); len(got) != 0 {
		t.Fatalf("expected empty list, got %#v", got)
	}

	created := doRequest(t, s, http.MethodPost, "/items", `{"name":"alpha"}`)
	if created.Code != http.StatusCreated {
		t.Fatalf("create status %d body %s", created.Code, created.Body.String())
	}
	item := decodeBody(t, created)
	id, _ := item["id"].(string)
	if id == "" {
		t.Fatalf("missing id: %#v", item)
	}

	got := doRequest(t, s, http.MethodGet, "/items/"+id, "")
	if got.Code != http.StatusOK {
		t.Fatalf("get status %d", got.Code)
	}
	if decodeBody(t, got)["name"] != "alpha" {
		t.Fatalf("get body %s", got.Body.String())
	}

	put := doRequest(t, s, http.MethodPut, "/items", `{"id":"`+id+`","name":"beta"}`)
	if put.Code != http.StatusOK {
		t.Fatalf("put status %d body %s", put.Code, put.Body.String())
	}
	if decodeBody(t, put)["name"] != "beta" {
		t.Fatalf("put body %s", put.Body.String())
	}

	missing := doRequest(t, s, http.MethodGet, "/items/missing", "")
	if missing.Code != http.StatusNotFound {
		t.Fatalf("missing status %d", missing.Code)
	}

	conflict := doRequest(t, s, http.MethodPost, "/items", `{"id":"`+id+`","name":"dup"}`)
	if conflict.Code != http.StatusConflict {
		t.Fatalf("conflict status %d", conflict.Code)
	}

	noID := doRequest(t, s, http.MethodPut, "/items", `{"name":"nope"}`)
	if noID.Code != http.StatusBadRequest {
		t.Fatalf("put without id status %d", noID.Code)
	}
}

func TestFaultInjection(t *testing.T) {
	tests := []struct {
		name       string
		mode       string
		method     string
		path       string
		body       string
		wantStatus int
		retryAfter string
	}{
		{
			name:       "status 500 without error_rate",
			mode:       `{"route":"POST /items","status":500}`,
			method:     http.MethodPost,
			path:       "/items",
			body:       `{"name":"x"}`,
			wantStatus: http.StatusInternalServerError,
		},
		{
			name:       "error_rate 1 defaults to 500",
			mode:       `{"route":"GET /items","error_rate":1}`,
			method:     http.MethodGet,
			path:       "/items",
			wantStatus: http.StatusInternalServerError,
		},
		{
			name:       "429 retry after",
			mode:       `{"route":"POST /items","status":429,"retry_after_s":20,"error_rate":1}`,
			method:     http.MethodPost,
			path:       "/items",
			body:       `{"name":"x"}`,
			wantStatus: http.StatusTooManyRequests,
			retryAfter: "20",
		},
		{
			name:       "auth_fail",
			mode:       `{"route":"GET /items/{id}","auth_fail":true}`,
			method:     http.MethodGet,
			path:       "/items/1",
			wantStatus: http.StatusUnauthorized,
		},
		{
			name:       "error_rate 0 is healthy",
			mode:       `{"route":"GET /items","error_rate":0,"status":0}`,
			method:     http.MethodGet,
			path:       "/items",
			wantStatus: http.StatusOK,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			s := testServer()
			modeRec := doRequest(t, s, http.MethodPost, "/admin/mode", tt.mode)
			if modeRec.Code != http.StatusOK {
				t.Fatalf("mode status %d body %s", modeRec.Code, modeRec.Body.String())
			}
			rec := doRequest(t, s, tt.method, tt.path, tt.body)
			if rec.Code != tt.wantStatus {
				t.Fatalf("status %d, want %d body %s", rec.Code, tt.wantStatus, rec.Body.String())
			}
			if tt.retryAfter != "" && rec.Header().Get(headerRetryAfter) != tt.retryAfter {
				t.Fatalf("Retry-After %q, want %q", rec.Header().Get(headerRetryAfter), tt.retryAfter)
			}
		})
	}
}

func TestLatency(t *testing.T) {
	s := testServer()
	mode := doRequest(t, s, http.MethodPost, "/admin/mode", `{"route":"GET /items","latency_ms":40}`)
	if mode.Code != http.StatusOK {
		t.Fatalf("mode status %d", mode.Code)
	}
	start := time.Now()
	rec := doRequest(t, s, http.MethodGet, "/items", "")
	elapsed := time.Since(start)
	if rec.Code != http.StatusOK {
		t.Fatalf("status %d", rec.Code)
	}
	if elapsed < 40*time.Millisecond {
		t.Fatalf("elapsed %s, want at least 40ms", elapsed)
	}
}

func TestStatsAndReset(t *testing.T) {
	s := testServer()
	doRequest(t, s, http.MethodPost, "/items", `{"name":"a"}`)
	doRequest(t, s, http.MethodPost, "/items", `{"name":"b"}`)
	doRequest(t, s, http.MethodGet, "/items", "")
	doRequest(t, s, http.MethodGet, "/items/1", "")

	stats := doRequest(t, s, http.MethodGet, "/admin/stats", "")
	if stats.Code != http.StatusOK {
		t.Fatalf("stats status %d", stats.Code)
	}
	body := decodeBody(t, stats)
	counts, _ := body["request_counts"].(map[string]any)
	if counts[routePostItems] != float64(2) {
		t.Fatalf("POST /items count %#v", counts[routePostItems])
	}
	if counts[routeGetItems] != float64(1) {
		t.Fatalf("GET /items count %#v", counts[routeGetItems])
	}
	if counts[routeGetItemByID] != float64(1) {
		t.Fatalf("GET /items/{id} count %#v", counts[routeGetItemByID])
	}
	if counts[routePutItems] != float64(0) {
		t.Fatalf("PUT /items count %#v", counts[routePutItems])
	}

	reset := doRequest(t, s, http.MethodPost, "/admin/reset", "")
	if reset.Code != http.StatusOK {
		t.Fatalf("reset status %d", reset.Code)
	}
	after := decodeBody(t, doRequest(t, s, http.MethodGet, "/admin/stats", ""))
	afterCounts, _ := after["request_counts"].(map[string]any)
	if afterCounts[routePostItems] != float64(0) {
		t.Fatalf("counts after reset %#v", afterCounts)
	}
	list := decodeBody(t, doRequest(t, s, http.MethodGet, "/items", ""))
	if items, _ := list["items"].([]any); len(items) != 0 {
		t.Fatalf("store not cleared: %#v", items)
	}
}

func TestMetricsPlainText(t *testing.T) {
	s := testServer()
	doRequest(t, s, http.MethodGet, "/items", "")
	rec := doRequest(t, s, http.MethodGet, "/metrics", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status %d", rec.Code)
	}
	ct := rec.Header().Get("Content-Type")
	if !strings.HasPrefix(ct, "text/plain") {
		t.Fatalf("content-type %q", ct)
	}
	body := rec.Body.String()
	if !strings.Contains(body, "# TYPE flaky_api_http_requests_total counter") {
		t.Fatalf("missing type line: %s", body)
	}
	if !strings.Contains(body, `flaky_api_http_requests_total{code="200",route="GET /items"} 1`) {
		t.Fatalf("missing sample: %s", body)
	}
}

func TestStatsConcurrent(t *testing.T) {
	s := testServer()
	const n = 40
	var wg sync.WaitGroup
	wg.Add(n)
	for i := 0; i < n; i++ {
		go func() {
			defer wg.Done()
			req := httptest.NewRequest(http.MethodGet, "/items", nil)
			rec := httptest.NewRecorder()
			s.ServeHTTP(rec, req)
		}()
	}
	wg.Wait()
	counts := s.stats.snapshot()
	if counts[routeGetItems] != n {
		t.Fatalf("count %d, want %d", counts[routeGetItems], n)
	}
}

func TestLoadConfig(t *testing.T) {
	tests := []struct {
		name    string
		addr    string
		set     bool
		want    string
		wantErr bool
	}{
		{name: "default", want: ":8091"},
		{name: "empty", set: true, addr: "", want: ":8091"},
		{name: "custom", set: true, addr: "127.0.0.1:9000", want: "127.0.0.1:9000"},
		{name: "invalid", set: true, addr: "nope", wantErr: true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if tt.set {
				t.Setenv("FLAKY_API_ADDR", tt.addr)
			} else {
				t.Setenv("FLAKY_API_ADDR", "")
			}
			cfg, err := loadConfig()
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error")
				}
				return
			}
			if err != nil {
				t.Fatal(err)
			}
			if cfg.Addr != tt.want {
				t.Fatalf("addr %q, want %q", cfg.Addr, tt.want)
			}
		})
	}
}
