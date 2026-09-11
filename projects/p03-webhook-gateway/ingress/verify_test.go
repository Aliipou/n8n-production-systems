package ingress

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"fmt"
	"strconv"
	"testing"
	"time"
)

func githubMAC(secret string, body []byte) string {
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write(body)
	return "sha256=" + hex.EncodeToString(mac.Sum(nil))
}

func stripeMAC(secret string, ts int64, body []byte) string {
	mac := hmac.New(sha256.New, []byte(secret))
	_, _ = fmt.Fprintf(mac, "%d", ts)
	mac.Write([]byte("."))
	mac.Write(body)
	return fmt.Sprintf("t=%d,v1=%s", ts, hex.EncodeToString(mac.Sum(nil)))
}

func shopifyMAC(secret string, body []byte) string {
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write(body)
	return base64.StdEncoding.EncodeToString(mac.Sum(nil))
}

func customMAC(secret, ts string, body []byte) string {
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(ts))
	mac.Write([]byte("."))
	mac.Write(body)
	return hex.EncodeToString(mac.Sum(nil))
}

func TestVerifiers(t *testing.T) {
	t.Parallel()
	now := time.Date(2026, 9, 11, 14, 31, 0, 0, time.UTC)
	body := []byte(`{"id":"evt_1","ok":true}`)
	ts := strconv.FormatInt(now.Unix(), 10)
	old := strconv.FormatInt(now.Add(-6*time.Minute).Unix(), 10)
	future := strconv.FormatInt(now.Add(6*time.Minute).Unix(), 10)

	tests := []struct {
		name string
		ok   bool
		fn   func() bool
	}{
		{
			name: "github hmac sha256 header matches",
			ok:   true,
			fn:   func() bool { return validGitHub(body, githubMAC("gh", body), "gh") },
		},
		{
			name: "github wrong secret",
			ok:   false,
			fn:   func() bool { return validGitHub(body, githubMAC("other", body), "gh") },
		},
		{
			name: "github missing sha256 prefix",
			ok:   false,
			fn: func() bool {
				mac := hmac.New(sha256.New, []byte("gh"))
				mac.Write(body)
				return validGitHub(body, hex.EncodeToString(mac.Sum(nil)), "gh")
			},
		},
		{
			name: "github empty secret",
			ok:   false,
			fn:   func() bool { return validGitHub(body, githubMAC("gh", body), "") },
		},
		{
			name: "stripe hmac plus timestamp",
			ok:   true,
			fn:   func() bool { return validStripe(body, stripeMAC("st", now.Unix(), body), "st", now) },
		},
		{
			name: "stripe wrong v1",
			ok:   false,
			fn: func() bool {
				return validStripe(body, fmt.Sprintf("t=%d,v1=%s", now.Unix(), hex.EncodeToString(make([]byte, 32))), "st", now)
			},
		},
		{
			name: "stripe timestamp older than 5min",
			ok:   false,
			fn: func() bool {
				t := now.Add(-6 * time.Minute).Unix()
				return validStripe(body, stripeMAC("st", t, body), "st", now)
			},
		},
		{
			name: "stripe timestamp 5min future",
			ok:   false,
			fn: func() bool {
				t := now.Add(6 * time.Minute).Unix()
				return validStripe(body, stripeMAC("st", t, body), "st", now)
			},
		},
		{
			name: "shopify base64 hmac",
			ok:   true,
			fn:   func() bool { return validShopify(body, shopifyMAC("sh", body), "sh") },
		},
		{
			name: "shopify hex instead of base64",
			ok:   false,
			fn: func() bool {
				mac := hmac.New(sha256.New, []byte("sh"))
				mac.Write(body)
				return validShopify(body, hex.EncodeToString(mac.Sum(nil)), "sh")
			},
		},
		{
			name: "shopify wrong secret",
			ok:   false,
			fn:   func() bool { return validShopify(body, shopifyMAC("other", body), "sh") },
		},
		{
			name: "custom timestamp.body within 5min",
			ok:   true,
			fn:   func() bool { return validCustom(body, ts, customMAC("cu", ts, body), "cu", now) },
		},
		{
			name: "custom timestamp older than 5min",
			ok:   false,
			fn:   func() bool { return validCustom(body, old, customMAC("cu", old, body), "cu", now) },
		},
		{
			name: "custom timestamp too new",
			ok:   false,
			fn:   func() bool { return validCustom(body, future, customMAC("cu", future, body), "cu", now) },
		},
		{
			name: "custom wrong signature",
			ok:   false,
			fn:   func() bool { return validCustom(body, ts, customMAC("other", ts, body), "cu", now) },
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			if got := tt.fn(); got != tt.ok {
				t.Fatalf("got %v, want %v", got, tt.ok)
			}
		})
	}
}
