# 0002. Ingress lives outside n8n

## Context

Signature checks need the raw body. Providers expect a fast 2xx. n8n may be down, restarting, or busy with workers.

## Decision

A Go process owns `POST /hooks/{stripe,shopify,github,custom}`. It verifies HMAC, caps the body at 1 MB, and writes the inbox. n8n is not on that path.

## Alternatives

n8n Webhook node plus a Code node HMAC. Rejected: raw body handling is easy to get wrong, secrets can leak into execution data, and n8n downtime becomes provider-visible loss.

Put business logic in the ingress. Rejected: the ingress must stay small and testable.

## Consequences

One extra service and port (`127.0.0.1:8103`). Dispatcher (later) signs an internal POST to the n8n router. Demo: stop n8n, send events, start n8n, drain the inbox.
