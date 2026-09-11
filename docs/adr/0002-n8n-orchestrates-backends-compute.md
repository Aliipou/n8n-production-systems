# ADR 0002: n8n orchestrates, backends compute

Date: 2026-09-11
Status: Accepted

## Context

n8n is strong at triggers, routing, credentials, human steps, and calling other systems. Scoring, validation, parsing, OCR, cryptography, tenant isolation, and anything that needs table-driven tests or durable state are a poor fit for long Code nodes. Code node output is stored in execution data. Secrets and large payloads must not travel through that path. n8n 2.x Community Edition also blocks environment access from Code nodes and disables Execute Command.

## Decision

n8n is the orchestration layer. Python (FastAPI) and Go services do computation, persistence, and security-sensitive work. Workflows stay short: trigger, validate or ack, call a backend, branch on the result, notify or wait for a human. Business rules live in backends with unit tests. Code nodes are JavaScript, short, and pure (no network). Logic longer than 15 lines lives in `code-snippets/` with Vitest tests.

Every project README states this split: what n8n does, what the backend does, and why.

## Alternatives

1. Put scoring, HMAC, OCR, and SQL in Code nodes or Function nodes. Faster to demo. Hard to test, easy to leak secrets into execution data, blocked by 2.x security defaults if the node needs env vars or a shell.
2. Skip n8n and write only backends plus a custom scheduler. Loses the editor, credentials store, and the workflow screenshots the portfolio needs.
3. Use n8n only as a webhook forwarder with no editor-visible logic. Weak as a portfolio of n8n operations.

## Consequences

- Backends can be tested without the editor. CI runs pytest and `go test -race` on those packages.
- Workflow JSON stays smaller. The 25-node soft limit and 40-node hard limit are easier to keep.
- Local demos need compose: n8n, Postgres, Redis, and the project backend. `make up` is mandatory, not optional.
- Readers who only open the canvas will not see the full rule set. READMEs and `docs/workflows.md` have to point at the backend.
- If the pinned n8n OpenAI credential cannot take a custom base URL, LLM calls go through the project backend (see AGENTS.md section 6). That is the same split, not an exception.
