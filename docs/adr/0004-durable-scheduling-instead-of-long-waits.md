# ADR 0004: Durable scheduling instead of long Wait nodes

Date: 2026-09-11
Status: Accepted

## Context

Lead follow-ups, invoice reminders, DLQ backoff, and heartbeats are due at a wall-clock time hours or days after the last event. n8n has a Wait node that can pause an execution. A paused execution holds workflow state in n8n, is tied to one process generation, and is a poor place to store "email this person on Tuesday" for many items. Worker restarts, pruning, and queue mode make long in-execution sleeps harder to reason about. Short waits (seconds) for an HTTP retry or a human click are a different case.

## Decision

Do not sleep an execution for hours or days with a Wait node. Store the due time in a Postgres table (`next_attempt_at`, or a project-specific schedule column). A scheduled workflow claims due rows (`FOR UPDATE SKIP LOCKED` where needed) and continues the work. Platform examples: `[PLT] DLQ Retrier` every minute, `[PLT] Heartbeat` every five minutes. Short waits measured in seconds remain allowed.

## Alternatives

1. Wait node with a long resume time per item. Simple on the canvas. Many paused executions, weak claim semantics, and a bad fit for queue mode plus execution pruning.
2. External cron on the host calling the n8n public API. Works, but duplicates what n8n Schedule Trigger already does inside the stack.
3. Backend-only schedulers (systemd, extra Go cron). Extra moving parts for work that is still an n8n workflow step after the due time.

## Consequences

- Due work survives worker death as a row, not as a paused execution.
- Concurrent schedulers need a claim pattern. Tests must cover two workers not processing the same row twice.
- The canvas will show a Schedule Trigger plus a database read, not a long Wait. Screenshots need a sticky note that says why.
- Pruning of old executions does not delete the follow-up. Retention jobs must still purge the schedule tables on purpose.
- Short Wait nodes (seconds) can stay in-flow for transient HTTP retries. That is not this ADR.
