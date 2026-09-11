# n8n environment variables

Pinned n8n: 2.37.9 (Community Edition, queue mode). Every variable below is set in `docker-compose.base.yml` unless the row says it is deliberately omitted.

Do not set `N8N_MULTI_MAIN_SETUP_ENABLED`. Do not set `NODES_EXCLUDE=[]`. Do not set `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`.

## Set on n8n-main and both workers

| Variable | Value | Reason | Official docs |
|---|---|---|---|
| `DB_TYPE` | `postgresdb` | n8n metadata and credentials go to Postgres, not SQLite. Queue mode needs a shared database. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/database.md |
| `DB_POSTGRESDB_HOST` | `postgres` | Compose service name for the Postgres container. Default in docs is `localhost`, which would miss the container. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/database.md |
| `DB_POSTGRESDB_PORT` | `5432` | Default Postgres port, set explicitly. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/database.md |
| `DB_POSTGRESDB_DATABASE` | `n8n` (from `POSTGRES_DB_N8N`) | n8n's own database. Application schemas live in database `app`, not here. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/database.md |
| `DB_POSTGRESDB_USER` | from `.env` `POSTGRES_USER` | Postgres role for n8n. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/database.md |
| `DB_POSTGRESDB_PASSWORD` | from `.env` `POSTGRES_PASSWORD` | Postgres password for that role. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/database.md |
| `EXECUTIONS_MODE` | `queue` | Main enqueues work; workers execute. Must be `queue` on main and workers. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/executions.md https://docs.n8n.io/deploy/host-n8n/configure-n8n/scaling/enable-queue-mode.md |
| `QUEUE_BULL_REDIS_HOST` | `redis` | Redis broker for the Bull queue. Default `localhost` would miss the container. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/queue-mode.md https://docs.n8n.io/deploy/host-n8n/configure-n8n/scaling/enable-queue-mode.md |
| `QUEUE_BULL_REDIS_PORT` | `6379` | Default Redis port, set explicitly. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/queue-mode.md |
| `QUEUE_BULL_REDIS_PASSWORD` | from `.env` `REDIS_PASSWORD` | Redis is started with `--requirepass`. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/queue-mode.md |
| `N8N_ENCRYPTION_KEY` | from `.env` | Same key on main and workers so workers can decrypt credentials stored in Postgres. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/deployment.md https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/configuration-examples/set-a-custom-encryption-key.md https://docs.n8n.io/deploy/host-n8n/configure-n8n/scaling/enable-queue-mode.md |
| `OFFLOAD_MANUAL_EXECUTIONS_TO_WORKERS` | `true` | Manual editor runs go to workers, not the main process. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/queue-mode.md |
| `N8N_METRICS` | `true` | Enables the `/metrics` Prometheus endpoint. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/endpoints.md https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/configuration-examples/enable-prometheus-metrics.md |
| `N8N_METRICS_INCLUDE_QUEUE_METRICS` | `true` | Queue (Bull) job metrics in scaling mode. Present on this pin. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/endpoints.md https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/configuration-examples/enable-prometheus-metrics.md |
| `QUEUE_HEALTH_CHECK_ACTIVE` | `true` | Worker process serves `/healthz` (and `/healthz/readiness`). Official worker health. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/queue-mode.md https://docs.n8n.io/deploy/host-n8n/configure-n8n/scaling/enable-queue-mode.md |
| `WEBHOOK_URL` | `http://localhost:5678/` | Public webhook base URL for local HTTP. Required by the platform spec. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/scaling/enable-queue-mode.md |
| `N8N_WEBHOOK_URL` | `http://localhost:5678/` | Current name for the webhook base URL. `WEBHOOK_URL` is documented as deprecated from n8n 2.35.0 and remains an alias. Pin 2.37.9 is after that date, so both are set to the same value. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/endpoints.md https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/configuration-examples/configure-webhook-urls-with-reverse-proxy.md |
| `GENERIC_TIMEZONE` | `Europe/Helsinki` | Timezone for Schedule Trigger and other schedule nodes. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/timezone-and-localization.md |
| `TZ` | `Europe/Helsinki` | Container OS timezone (`date` and similar). Not listed on the n8n timezone env page; set because the official Docker install documents it next to `GENERIC_TIMEZONE`. | https://docs.n8n.io/deploy/host-n8n/install-options/install-with-docker.md |
| `N8N_DIAGNOSTICS_ENABLED` | `false` | No anonymous telemetry on local runs. Disables Ask AI in the Code node. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/deployment.md |
| `N8N_DEFAULT_BINARY_DATA_MODE` | `database` | n8n 2.0 queue-mode default. Filesystem mode is not supported in queue mode. In-memory `default` mode was removed in 2.0. Community Edition cannot use S3/Azure. | https://docs.n8n.io/changelog/v20-breaking-changes.md https://docs.n8n.io/deploy/host-n8n/configure-n8n/scaling/handle-binary-data.md https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/binary-data.md |
| `EXECUTIONS_DATA_PRUNE` | `true` | Delete old execution rows on a rolling basis. Docs default is already `true`; set so local retention is explicit. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/executions.md https://docs.n8n.io/deploy/host-n8n/configure-n8n/scaling/manage-execution-data.md |
| `EXECUTIONS_DATA_MAX_AGE` | `336` | Delete finished executions after 336 hours (14 days). Docs default. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/executions.md https://docs.n8n.io/deploy/host-n8n/configure-n8n/scaling/manage-execution-data.md |
| `EXECUTIONS_DATA_SAVE_ON_ERROR` | `all` | Always save failed executions. Docs default is `all`; set so it cannot be dropped accidentally. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/executions.md https://docs.n8n.io/deploy/host-n8n/configure-n8n/scaling/manage-execution-data.md |
| `N8N_HOST` | `localhost` | Host name used when building URLs. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/deployment.md |
| `N8N_PORT` | `5678` | HTTP port inside the container. Host bind is `127.0.0.1:5678`. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/deployment.md |
| `N8N_PROTOCOL` | `http` | Local stack is HTTP, not HTTPS. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/deployment.md |
| `N8N_EDITOR_BASE_URL` | `http://localhost:5678/` | Public editor URL (emails from n8n, UI links). | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/deployment.md |
| `N8N_SECURE_COOKIE` | `false` | Docs default is `true` (cookies only over HTTPS). Local editor is HTTP on 127.0.0.1, so the Secure flag would block the session cookie. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/security.md |
| `N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS` | `true` | Restrict the n8n settings file to owner read/write. Official Docker install sets this. | https://docs.n8n.io/deploy/host-n8n/install-options/install-with-docker.md https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/security.md https://docs.n8n.io/changelog/v20-breaking-changes.md |
| `N8N_RUNNERS_ENABLED` | `true` | Task runners execute Code nodes. 2.0 default; official Docker install still sets it. | https://docs.n8n.io/deploy/host-n8n/install-options/install-with-docker.md https://docs.n8n.io/changelog/v20-breaking-changes.md |
| `N8N_BLOCK_ENV_ACCESS_IN_NODE` | `true` | Code nodes and expressions must not read process environment. 2.0 breaking-changes page says this is the 2.x default. Set explicitly. Do not set `false`. | https://docs.n8n.io/changelog/v20-breaking-changes.md https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/security.md |

## Deliberately omitted

| Variable | Why it is not set | Official docs |
|---|---|---|
| `N8N_MULTI_MAIN_SETUP_ENABLED` | Enterprise multi-main. Community Edition uses one main. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/scaling/enable-queue-mode.md https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/queue-mode.md |
| `NODES_EXCLUDE` | Docs default already excludes Execute Command and LocalFileTrigger. Setting `NODES_EXCLUDE=[]` would re-enable them. Leave the default. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/nodes.md https://docs.n8n.io/changelog/v20-breaking-changes.md |
| `N8N_AVAILABLE_BINARY_DATA_MODES` | Removed in n8n 2.0. Mode is only `N8N_DEFAULT_BINARY_DATA_MODE`. | https://docs.n8n.io/changelog/v20-breaking-changes.md |
| `QUEUE_WORKER_MAX_STALLED_COUNT` | Removed in n8n 2.0. Setting it has no effect. | https://docs.n8n.io/changelog/v20-breaking-changes.md https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/queue-mode.md |
| `N8N_LISTEN_ADDRESS` | Docs default is `::`, which is correct inside Docker so the published `127.0.0.1:5678` mapping can reach the process. Do not set `127.0.0.1` inside the container. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/deployment.md |
| `QUEUE_HEALTH_CHECK_PORT` | Docs default `5678`. Workers do not publish that port on the host. | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/queue-mode.md |

## Worker process

Workers use the same environment as main. Command is `worker` (Docker: `n8nio/n8n worker`).

https://docs.n8n.io/deploy/host-n8n/configure-n8n/scaling/enable-queue-mode.md

Compose runs two worker services (`n8n-worker-1`, `n8n-worker-2`) so each container has a stable name without Swarm replicas.

## Health endpoints

- Main: `GET /healthz` (`N8N_ENDPOINT_HEALTH` default `healthz`). https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/endpoints.md
- Workers: `/healthz` when `QUEUE_HEALTH_CHECK_ACTIVE=true`. https://docs.n8n.io/deploy/host-n8n/configure-n8n/scaling/enable-queue-mode.md

## TODO(verify)

- Security env page still lists `N8N_BLOCK_ENV_ACCESS_IN_NODE` default `false`. Breaking-changes page says 2.0 default `true`. Compose sets `true`.
- Confirm 2.37.9 logs a deprecation warning for `WEBHOOK_URL` while `N8N_WEBHOOK_URL` is also set.
- Confirm main `/healthz` responds without extra flags (worker `/healthz` is documented under `QUEUE_HEALTH_CHECK_ACTIVE`).
