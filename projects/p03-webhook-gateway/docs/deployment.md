# Deployment

Not tested outside unit tests on a laptop.

Planned local shape:
- Ingress container, host port `127.0.0.1:8103`.
- Postgres database `app`, schema `p03` from `db/migrations/` via dbmate.
- n8n in queue mode from the platform compose file (not in this folder).

Host bind stays on `127.0.0.1`. Secrets only in `.env` (see `.env.example`).

Production sketch (not run): two ingress replicas behind a load balancer, Postgres with backups, dispatcher replicas using `SKIP LOCKED`. Upgrade by shipping a new ingress image; migrations run before traffic. Revisit Kafka only after a measured inbox lag number says Postgres is the bottleneck.

The `cmd/ingress` binary currently uses `MemoryStore`. That is for tests and for bringing the HTTP surface up without Postgres. A real deploy must use `SQLStore` and `InsertInboxSQL`.
