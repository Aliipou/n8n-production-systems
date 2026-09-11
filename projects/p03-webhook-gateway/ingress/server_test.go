package ingress

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

func testSecrets() Secrets {
	return Secrets{
		Stripe:  "stripe-secret",
		Shopify: "shopify-secret",
		GitHub:  "github-secret",
		Custom:  "custom-secret",
	}
}

func TestHooksTable(t *testing.T) {
	t.Parallel()
	now := time.Date(2026, 9, 11, 14, 31, 0, 0, time.UTC)
	ts := strconv.FormatInt(now.Unix(), 10)
	githubBody := `{"ref":"refs/heads/main"}`
	stripeBody := `{"id":"evt_123","type":"customer.created","created":1757591460}`
	shopifyBody := `{"id":9001}`
	customBody := `{"ping":true}`

	type headerSet map[string]string
	tests := []struct {
		name       string
		method     string
		path       string
		body       string
		headers    headerSet
		oversize   bool
		wantCode   int
		wantCount  int
		wantResult string
	}{
		{
			name:   "github valid signature",
			method: http.MethodPost,
			path:   "/hooks/github",
			body:   githubBody,
			headers: headerSet{
				headerGitHubSignature: githubMAC("github-secret", []byte(githubBody)),
				headerGitHubDelivery:  "del-1",
				headerGitHubEvent:     "push",
			},
			wantCode:   http.StatusOK,
			wantCount:  1,
			wantResult: "new",
		},
		{
			name:   "github bad signature",
			method: http.MethodPost,
			path:   "/hooks/github",
			body:   githubBody,
			headers: headerSet{
				headerGitHubSignature: githubMAC("wrong", []byte(githubBody)),
				headerGitHubDelivery:  "del-bad",
				headerGitHubEvent:     "push",
			},
			wantCode:  http.StatusUnauthorized,
			wantCount: 0,
		},
		{
			name:   "stripe valid hmac timestamp",
			method: http.MethodPost,
			path:   "/hooks/stripe",
			body:   stripeBody,
			headers: headerSet{
				headerStripeSignature: stripeMAC("stripe-secret", now.Unix(), []byte(stripeBody)),
			},
			wantCode:   http.StatusOK,
			wantCount:  1,
			wantResult: "new",
		},
		{
			name:   "stripe bad signature",
			method: http.MethodPost,
			path:   "/hooks/stripe",
			body:   stripeBody,
			headers: headerSet{
				headerStripeSignature: stripeMAC("wrong", now.Unix(), []byte(stripeBody)),
			},
			wantCode:  http.StatusUnauthorized,
			wantCount: 0,
		},
		{
			name:   "stripe timestamp outside 5min",
			method: http.MethodPost,
			path:   "/hooks/stripe",
			body:   stripeBody,
			headers: headerSet{
				headerStripeSignature: stripeMAC("stripe-secret", now.Add(-6*time.Minute).Unix(), []byte(stripeBody)),
			},
			wantCode:  http.StatusUnauthorized,
			wantCount: 0,
		},
		{
			name:   "shopify valid base64 hmac",
			method: http.MethodPost,
			path:   "/hooks/shopify",
			body:   shopifyBody,
			headers: headerSet{
				headerShopifyHMAC:      shopifyMAC("shopify-secret", []byte(shopifyBody)),
				headerShopifyWebhookID: "wh-1",
				headerShopifyTopic:     "orders/paid",
			},
			wantCode:   http.StatusOK,
			wantCount:  1,
			wantResult: "new",
		},
		{
			name:   "shopify bad signature",
			method: http.MethodPost,
			path:   "/hooks/shopify",
			body:   shopifyBody,
			headers: headerSet{
				headerShopifyHMAC:      shopifyMAC("wrong", []byte(shopifyBody)),
				headerShopifyWebhookID: "wh-bad",
				headerShopifyTopic:     "orders/paid",
			},
			wantCode:  http.StatusUnauthorized,
			wantCount: 0,
		},
		{
			name:   "custom valid timestamp.body",
			method: http.MethodPost,
			path:   "/hooks/custom",
			body:   customBody,
			headers: headerSet{
				headerCustomTimestamp: ts,
				headerCustomSignature: customMAC("custom-secret", ts, []byte(customBody)),
				headerCustomEventID:   "c-1",
				headerCustomEventType: "custom.ping",
			},
			wantCode:   http.StatusOK,
			wantCount:  1,
			wantResult: "new",
		},
		{
			name:   "custom stale timestamp",
			method: http.MethodPost,
			path:   "/hooks/custom",
			body:   customBody,
			headers: headerSet{
				headerCustomTimestamp: strconv.FormatInt(now.Add(-6*time.Minute).Unix(), 10),
				headerCustomSignature: customMAC("custom-secret", strconv.FormatInt(now.Add(-6*time.Minute).Unix(), 10), []byte(customBody)),
				headerCustomEventID:   "c-old",
				headerCustomEventType: "custom.ping",
			},
			wantCode:  http.StatusUnauthorized,
			wantCount: 0,
		},
		{
			name:      "unknown source",
			method:    http.MethodPost,
			path:      "/hooks/paypal",
			body:      `{}`,
			wantCode:  http.StatusNotFound,
			wantCount: 0,
		},
		{
			name:   "github missing delivery id",
			method: http.MethodPost,
			path:   "/hooks/github",
			body:   githubBody,
			headers: headerSet{
				headerGitHubSignature: githubMAC("github-secret", []byte(githubBody)),
				headerGitHubEvent:     "push",
			},
			wantCode:  http.StatusBadRequest,
			wantCount: 0,
		},
		{
			name:      "oversize body",
			method:    http.MethodPost,
			path:      "/hooks/github",
			oversize:  true,
			wantCode:  http.StatusRequestEntityTooLarge,
			wantCount: 0,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			store := NewMemoryStore()
			srv := NewServer(store, testSecrets())
			srv.Now = func() time.Time { return now }

			var body io.Reader
			if tt.oversize {
				body = bytes.NewReader(bytes.Repeat([]byte("a"), maxBodyBytes+1))
			} else {
				body = strings.NewReader(tt.body)
			}
			req := httptest.NewRequest(tt.method, tt.path, body)
			for k, v := range tt.headers {
				req.Header.Set(k, v)
			}
			rec := httptest.NewRecorder()
			srv.ServeHTTP(rec, req)
			if rec.Code != tt.wantCode {
				t.Fatalf("status %d, want %d, body %s", rec.Code, tt.wantCode, rec.Body.String())
			}
			if store.Count() != tt.wantCount {
				t.Fatalf("store count %d, want %d", store.Count(), tt.wantCount)
			}
			if tt.wantResult != "" {
				var got map[string]string
				if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
					t.Fatalf("json: %v", err)
				}
				if got["result"] != tt.wantResult {
					t.Fatalf("result %q, want %q", got["result"], tt.wantResult)
				}
			}
		})
	}
}

func TestHookDuplicateOnConflict(t *testing.T) {
	t.Parallel()
	now := time.Date(2026, 9, 11, 14, 31, 0, 0, time.UTC)
	body := `{"ref":"refs/heads/main"}`
	headers := map[string]string{
		headerGitHubSignature: githubMAC("github-secret", []byte(body)),
		headerGitHubDelivery:  "del-dup",
		headerGitHubEvent:     "push",
	}

	mem := NewMemoryStore()
	fake := NewFakeSQLStore()
	tests := []struct {
		name  string
		store Store
		count func() int
	}{
		{name: "memory", store: mem, count: mem.Count},
		{name: "fake sql", store: &SQLStore{DB: fake}, count: fake.Count},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			srv := NewServer(tt.store, testSecrets())
			srv.Now = func() time.Time { return now }
			post := func() *httptest.ResponseRecorder {
				req := httptest.NewRequest(http.MethodPost, "/hooks/github", strings.NewReader(body))
				for k, v := range headers {
					req.Header.Set(k, v)
				}
				rec := httptest.NewRecorder()
				srv.ServeHTTP(rec, req)
				return rec
			}
			first := post()
			second := post()
			if first.Code != http.StatusOK || second.Code != http.StatusOK {
				t.Fatalf("status first=%d second=%d", first.Code, second.Code)
			}
			var a, b map[string]string
			if err := json.Unmarshal(first.Body.Bytes(), &a); err != nil {
				t.Fatal(err)
			}
			if err := json.Unmarshal(second.Body.Bytes(), &b); err != nil {
				t.Fatal(err)
			}
			if a["result"] != "new" || b["result"] != "duplicate" {
				t.Fatalf("results %q then %q", a["result"], b["result"])
			}
			if tt.count() != 1 {
				t.Fatalf("count %d, want 1", tt.count())
			}
		})
	}
}

func TestConcurrentDuplicates(t *testing.T) {
	t.Parallel()
	body := `{"ref":"refs/heads/main"}`
	store := NewMemoryStore()
	srv := NewServer(store, testSecrets())
	var inserted atomic.Int64
	var wg sync.WaitGroup
	for i := 0; i < 50; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			req := httptest.NewRequest(http.MethodPost, "/hooks/github", strings.NewReader(body))
			req.Header.Set(headerGitHubSignature, githubMAC("github-secret", []byte(body)))
			req.Header.Set(headerGitHubDelivery, "storm-1")
			req.Header.Set(headerGitHubEvent, "push")
			rec := httptest.NewRecorder()
			srv.ServeHTTP(rec, req)
			if rec.Code != http.StatusOK {
				t.Errorf("status %d", rec.Code)
				return
			}
			var got map[string]string
			if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
				t.Errorf("json: %v", err)
				return
			}
			if got["result"] == "new" {
				inserted.Add(1)
			}
		}()
	}
	wg.Wait()
	if inserted.Load() != 1 {
		t.Fatalf("new inserts %d, want 1", inserted.Load())
	}
	if store.Count() != 1 {
		t.Fatalf("store count %d, want 1", store.Count())
	}
}

func TestHealthz(t *testing.T) {
	t.Parallel()
	srv := NewServer(NewMemoryStore(), testSecrets())
	req := httptest.NewRequest(http.MethodGet, "/healthz", nil)
	rec := httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("status %d", rec.Code)
	}
}

func TestStoreErrorReturns503(t *testing.T) {
	t.Parallel()
	fake := NewFakeSQLStore()
	fake.failWith = io.ErrUnexpectedEOF
	srv := NewServer(&SQLStore{DB: fake}, testSecrets())
	body := `{"ref":"x"}`
	req := httptest.NewRequest(http.MethodPost, "/hooks/github", strings.NewReader(body))
	req.Header.Set(headerGitHubSignature, githubMAC("github-secret", []byte(body)))
	req.Header.Set(headerGitHubDelivery, "del-503")
	req.Header.Set(headerGitHubEvent, "push")
	rec := httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	if rec.Code != http.StatusServiceUnavailable {
		t.Fatalf("status %d, want 503", rec.Code)
	}
}
