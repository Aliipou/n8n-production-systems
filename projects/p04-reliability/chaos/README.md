# Chaos scenarios (P04)

Scripts will live in this directory and run with:

```text
make chaos SCENARIO=<name>
```

`make chaos` is still a stub in the root Makefile (P04-T10). Do not treat
the names below as implemented.

Each script is supposed to record timestamps, trigger the fault, generate
load, heal, wait for recovery, and write a report skeleton to
`docs/failure-modes/<name>.md`. The observed section is filled from the
real run. If observed differs from expected, write it down and open a
task; do not edit the expectation to match.

Reports (once written) include: setup, command, expected behaviour,
observed behaviour (from logs, metrics, database counts), recovery time,
data lost (count), duplicates (count), alerts fired, fixes made afterwards.
Recovery time and counts are "not measured yet" until that scenario is run.

## Scenario names (from `docs/specs/04-reliability.md`)

| Scenario | Fault |
|---|---|
| `api-500-burst` | flaky-api returns 500 for 2 minutes during P01 traffic |
| `api-429-storm` | flaky-api returns 429 with `Retry-After: 20` |
| `api-auth-revoked` | flaky-api returns 401 |
| `api-latency` | 10 s latency on CRM calls |
| `worker-kill` | `docker kill` one worker during P02 processing |
| `redis-restart` | Restart Redis during P01 traffic |
| `postgres-restart` | Restart Postgres during P03 traffic |
| `n8n-main-restart` | Restart n8n main during P03 traffic |
| `n8n-down-drain` | Stop all n8n containers for 5 minutes during P03 traffic |

Related names in other specs (not this folder until those project scripts exist):
`dispatcher-kill` (P03), `worker-kill-p02` (P02), `worker-kill-p01` (P01).
