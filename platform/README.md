# Platform

Shared n8n queue-mode stack, `ops` schema, mock services, and scripts.
Compose files arrive in PLT-T03. Until then this directory is a scaffold.

Services bind to `127.0.0.1` only. Do not publish ports on `0.0.0.0`.

## One-time local n8n owner setup

After `make up` works (PLT-T03):

1. Open the n8n editor URL printed by `make up` (planned: `http://127.0.0.1:5678`).
2. Create the owner account in the setup screen. This is local only.
3. Create an API key in the n8n settings and put it in `.env` as `N8N_API_KEY`.
4. Never commit `.env` or the key.

Exact menu names may differ in the pinned n8n 2.x version. Confirm them
against that version's docs during PLT-T03. TODO(verify): owner setup path
and API key creation UI for the pinned release.

## What is not here yet

Grafana and Prometheus wait for P04. Project backends wait for P01 to P05.
