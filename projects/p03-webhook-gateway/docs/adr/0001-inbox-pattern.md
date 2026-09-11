# 0001. Inbox pattern

## Context

Providers retry. n8n restarts. Handlers fail halfway. We still need one stored event per provider delivery id and a place to replay from.

## Decision

Persist every authentic webhook in `p03.inbox_events` with unique `(source, external_event_id)` and `INSERT ON CONFLICT DO NOTHING` before returning 2xx. Processing reads from the inbox, not from the provider a second time.

## Alternatives

Deduplicate in n8n static data or in-memory maps. Rejected: lost on restart, racy under concurrent retries.

Acknowledge first, insert later. Rejected: 2xx without a committed row loses events when the process dies.

An extra broker (Kafka). Rejected at this volume. Postgres plus `SKIP LOCKED` is enough until measured otherwise.

## Consequences

Ingress stays boring. Dispatcher and handlers must be idempotent because at-least-once delivery will retry. Unique constraint is the source of truth for "already seen".
