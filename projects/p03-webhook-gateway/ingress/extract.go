package ingress

import (
	"encoding/json"
	"net/http"
	"strconv"
	"time"
)

var allowedSources = map[string]struct{}{
	"stripe":  {},
	"shopify": {},
	"github":  {},
	"custom":  {},
}

var headerAllow = map[string][]string{
	"github": {
		headerGitHubDelivery,
		headerGitHubEvent,
		"User-Agent",
		"X-GitHub-Hook-ID",
	},
	"shopify": {
		headerShopifyWebhookID,
		headerShopifyTopic,
		headerShopifyShop,
		headerShopifyAPIVersion,
		headerShopifyTriggered,
		headerShopifyEventID,
	},
	"stripe": {
		"Stripe-Account",
		"User-Agent",
	},
	"custom": {
		headerCustomEventID,
		headerCustomEventType,
		headerCustomTimestamp,
	},
}

type stripeBody struct {
	ID      string `json:"id"`
	Type    string `json:"type"`
	Created int64  `json:"created"`
}

func extractEvent(source string, body []byte, h http.Header) (InboxEvent, bool) {
	ev := InboxEvent{
		Source:  source,
		Payload: json.RawMessage(append([]byte(nil), body...)),
		Headers: allowHeaders(source, h),
	}
	switch source {
	case "github":
		ev.ExternalEventID = h.Get(headerGitHubDelivery)
		ev.EventType = h.Get(headerGitHubEvent)
	case "shopify":
		ev.ExternalEventID = h.Get(headerShopifyWebhookID)
		ev.EventType = h.Get(headerShopifyTopic)
		if raw := h.Get(headerShopifyTriggered); raw != "" {
			if t, err := time.Parse(time.RFC3339Nano, raw); err == nil {
				utc := t.UTC()
				ev.SourceTS = &utc
			} else if t, err := time.Parse(time.RFC3339, raw); err == nil {
				utc := t.UTC()
				ev.SourceTS = &utc
			}
		}
	case "stripe":
		var p stripeBody
		if err := json.Unmarshal(body, &p); err != nil {
			return InboxEvent{}, false
		}
		ev.ExternalEventID = p.ID
		ev.EventType = p.Type
		if p.Created > 0 {
			t := time.Unix(p.Created, 0).UTC()
			ev.SourceTS = &t
		}
	case "custom":
		ev.ExternalEventID = h.Get(headerCustomEventID)
		ev.EventType = h.Get(headerCustomEventType)
		if ev.EventType == "" {
			ev.EventType = "custom"
		}
		if raw := h.Get(headerCustomTimestamp); raw != "" {
			if unix, err := strconv.ParseInt(raw, 10, 64); err == nil {
				t := time.Unix(unix, 0).UTC()
				ev.SourceTS = &t
			}
		}
	default:
		return InboxEvent{}, false
	}
	if ev.ExternalEventID == "" || ev.EventType == "" {
		return InboxEvent{}, false
	}
	return ev, true
}

func allowHeaders(source string, h http.Header) map[string]string {
	out := make(map[string]string)
	for _, name := range headerAllow[source] {
		if v := h.Get(name); v != "" {
			out[name] = v
		}
	}
	return out
}
