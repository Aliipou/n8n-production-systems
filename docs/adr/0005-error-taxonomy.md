# ADR 0005: Shared error taxonomy

Date: 2026-09-11
Status: Accepted

## Context

Workflows and backends both call flaky HTTP APIs. Without one set of classes, a Code node might retry a 401 while a Python service dead-letters a 503. Retrying invalid data hammers providers. Dropping a timeout looks like a permanent failure. n8n Retry On Fail uses a fixed delay and does not classify status codes. Classification needs the same answer in JavaScript (Code nodes) and Python (backends).

## Decision

Use six classes with a shared fixture table `platform/libs/fixtures/error_cases.json`. Implementations: `code-snippets/classify_error.js` and `platform/libs/python/errors.py`. A test loads the fixture in both languages and requires the same class.

| Class | Signals | Default action |
|---|---|---|
| `transient` | HTTP 500, 502, 503, 504, timeouts, connection reset or refused, temporary DNS failure | Retry with backoff |
| `rate_limited` | HTTP 429, provider rate-limit error codes | Wait for `Retry-After` (capped), then retry |
| `invalid_data` | HTTP 400, 422, schema validation failure | Quarantine to review queue, no retry |
| `auth` | HTTP 401, 403 | Alert, open circuit for that dependency, no retry |
| `permanent` | HTTP 404, 410, 501, 409 on non-idempotent create | Dead letter, no retry |
| `unknown` | Anything else | Dead letter and alert |

Backoff: full jitter, base 2 s, cap 300 s, max 6 attempts, configurable per dependency. A 409 on an idempotent create counts as success, not `permanent`.

`[PLT] Error Handler` classifies, logs, writes dead letters when the item is recoverable, and notifies with 10-minute dedupe. `[PLT] DLQ Retrier` applies the same backoff on `next_attempt_at`.

## Alternatives

1. Retry every HTTP error three times, then fail. Simple. Turns 400s into load and hides 401s until someone reads executions.
2. Classify only in Python and keep Code nodes dumb. Then platform workflows that never hit a backend cannot classify.
3. Use provider-specific error enums only. Accurate per API, not shareable across P01 to P05 and `flaky-api`.
4. Map everything unknown to `transient`. Unsafe: unknown 409s and 403s would retry.

## Consequences

- New HTTP mappings need a fixture row and both implementations. Do not special-case one language.
- Circuit breaking for `auth` is a later platform concern (P04). The class is reserved now so P01 does not retry 401s.
- `unknown` is noisy on purpose. It should shrink as fixtures grow, not be used as a default success path.
- Backoff numbers are defaults, not measured SLOs. Do not publish them as production recovery times.
- Code nodes must call the snippet, not a private copy of the table.
