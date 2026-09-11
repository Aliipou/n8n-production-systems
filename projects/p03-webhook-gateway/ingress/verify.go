package ingress

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"fmt"
	"strconv"
	"strings"
	"time"
)

const (
	maxBodyBytes = 1 << 20
	sigTolerance = 5 * time.Minute

	headerGitHubSignature   = "X-Hub-Signature-256"
	headerGitHubDelivery    = "X-GitHub-Delivery"
	headerGitHubEvent       = "X-GitHub-Event"
	headerStripeSignature   = "Stripe-Signature"
	headerShopifyHMAC       = "X-Shopify-Hmac-Sha256"
	headerShopifyWebhookID  = "X-Shopify-Webhook-Id"
	headerShopifyTopic      = "X-Shopify-Topic"
	headerShopifyTriggered  = "X-Shopify-Triggered-At"
	headerShopifyShop       = "X-Shopify-Shop-Domain"
	headerShopifyAPIVersion = "X-Shopify-API-Version"
	headerShopifyEventID    = "X-Shopify-Event-Id"
	headerCustomTimestamp   = "X-Timestamp"
	headerCustomSignature   = "X-Signature"
	headerCustomEventID     = "X-Event-Id"
	headerCustomEventType   = "X-Event-Type"
)

func validGitHub(body []byte, header, secret string) bool {
	header = strings.TrimSpace(header)
	if secret == "" || !strings.HasPrefix(header, "sha256=") {
		return false
	}
	got, err := hex.DecodeString(header[len("sha256="):])
	if err != nil {
		return false
	}
	mac := hmac.New(sha256.New, []byte(secret))
	_, _ = mac.Write(body)
	return hmac.Equal(got, mac.Sum(nil))
}

// validStripe checks Stripe-Signature using HMAC-SHA256 over "{unix}.{raw body}".
// TODO(verify): replace with stripe-go webhook.ConstructEvent / ConstructEventWithTolerance
// (github.com/stripe/stripe-go/webhook, DefaultTolerance 300s) after confirming the
// pinned stripe-go major. This copy follows the same t=,v1= header scheme.
func validStripe(body []byte, header, secret string, now time.Time) bool {
	if secret == "" || strings.TrimSpace(header) == "" {
		return false
	}
	var ts int64
	var haveTS bool
	var sigs [][]byte
	for _, part := range strings.Split(header, ",") {
		kv := strings.SplitN(strings.TrimSpace(part), "=", 2)
		if len(kv) != 2 {
			return false
		}
		switch kv[0] {
		case "t":
			n, err := strconv.ParseInt(kv[1], 10, 64)
			if err != nil {
				return false
			}
			ts = n
			haveTS = true
		case "v1":
			b, err := hex.DecodeString(kv[1])
			if err != nil {
				continue
			}
			sigs = append(sigs, b)
		}
	}
	if !haveTS || len(sigs) == 0 {
		return false
	}
	t := time.Unix(ts, 0).UTC()
	if !withinTolerance(t, now, sigTolerance) {
		return false
	}
	mac := hmac.New(sha256.New, []byte(secret))
	_, _ = fmt.Fprintf(mac, "%d", ts)
	_, _ = mac.Write([]byte("."))
	_, _ = mac.Write(body)
	expected := mac.Sum(nil)
	for _, sig := range sigs {
		if hmac.Equal(expected, sig) {
			return true
		}
	}
	return false
}

func validShopify(body []byte, header, secret string) bool {
	header = strings.TrimSpace(header)
	if secret == "" || header == "" {
		return false
	}
	got, err := base64.StdEncoding.DecodeString(header)
	if err != nil {
		return false
	}
	mac := hmac.New(sha256.New, []byte(secret))
	_, _ = mac.Write(body)
	return hmac.Equal(got, mac.Sum(nil))
}

func validCustom(body []byte, ts, sig, secret string, now time.Time) bool {
	if secret == "" {
		return false
	}
	unix, err := strconv.ParseInt(strings.TrimSpace(ts), 10, 64)
	if err != nil {
		return false
	}
	t := time.Unix(unix, 0).UTC()
	if !withinTolerance(t, now, sigTolerance) {
		return false
	}
	got, err := hex.DecodeString(strings.TrimSpace(sig))
	if err != nil {
		return false
	}
	mac := hmac.New(sha256.New, []byte(secret))
	_, _ = mac.Write([]byte(strings.TrimSpace(ts)))
	_, _ = mac.Write([]byte("."))
	_, _ = mac.Write(body)
	return hmac.Equal(got, mac.Sum(nil))
}

func withinTolerance(t, now time.Time, d time.Duration) bool {
	delta := now.Sub(t)
	if delta < 0 {
		delta = -delta
	}
	return delta <= d
}
