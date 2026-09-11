# 0001. Shared n8n instance for tenant-aware workflows

## Context

P05 runs the same lead-handling process for many clients (tenants). Two
deployment models are common:

1. One n8n instance shared by all tenants, with tenant-aware workflows and
   isolation in the database and in an integration proxy.
2. One n8n instance per tenant (separate containers or a cluster), with a
   copy of workflows and credentials per tenant.

Copying workflows per client means N copies to fix, credentials scattered
across workflows, one client's traffic slowing others, and no clean way to
remove a client's data when the contract ends.

n8n licence (must be read, not interpreted here): n8n is distributed under
its own licence (Sustainable Use License), not an OSI open-source licence.
Running n8n as a hosted service for paying clients may need a separate
commercial agreement with n8n. This project is a reference architecture
for learning and demonstration. It is not a hosted product and is not an
offer to run n8n as a service for paying clients. Read the current licence
text published by n8n GmbH:

https://docs.n8n.io/sustainable-use-license/

TODO(verify): confirm that URL still matches the docs for the pinned n8n
version (`platform/VERSIONS.md`).

This ADR does not decide whether a given use is allowed under that
licence. Read the licence. Ask n8n GmbH if you need a commercial
agreement.

## Decision

Primary model: **one shared n8n Community Edition instance** with generic,
tenant-aware workflows.

- Tenant identity is established at `tenant-gateway` (`/t/{slug}/...` plus
  API key), then `tenant_id` is attached for the rest of the execution.
- Tenant configuration is versioned in Postgres (`p05.tenant_configs`).
  Config is never edited in place.
- Tenant secrets live in `p05.tenant_secrets` (encrypted). n8n never
  stores them in credentials and never writes them to execution data.
  External calls go through `integration-proxy`.
- Tenant data lives in schema `p05` with row-level security:
  `tenant_id = current_setting('app.tenant_id')::uuid`.
  The application role has no `BYPASSRLS`. n8n does not query tenant
  tables directly.
- A new tenant is onboarded from a YAML file (`tenantctl apply`).
  Offboarding deletes tenant data and secrets, revokes keys, and keeps an
  audit record without personal data.

Isolation is therefore: gateway auth and quotas, session GUC plus RLS,
encrypted secrets outside n8n, and per-tenant metrics labels bounded by
tenant slug.

## Alternatives

### Instance per tenant (documented, not primary)

One n8n process (or compose project) per tenant. Stronger process
isolation: a crash or a runaway execution is more likely to stay inside
that tenant's containers. Credentials can stay in that instance's
credential store.

Rejected as the primary model for this repository because:

- Isolation: stronger at the process boundary, weaker at "one codebase to
  fix". N workflow copies drift.
- Upgrade effort: N n8n versions and N credential stores to bump. The
  shared model upgrades one pair of main plus workers.
- Operations work: N databases or N schemas, N webhook URLs at the n8n
  layer, N owner accounts. The shared model has one n8n and many slugs
  on the gateway.
- Cost: not measured. Qualitatively, N copies of n8n, Postgres, and Redis
  use more RAM and disk than one shared instance on the same laptop.
  Do not read this as a cloud price.
- Noisy-neighbour risk: lower between tenants (separate queues), higher
  operationally (more moving parts). The shared model must prove
  noisy-neighbour limits with a test (`test_noisy_neighbour`). That test
  is not written yet. Limits are not measured yet.

Stretch (P05-T13): a Helm chart for instance-per-tenant on a local kind
cluster, with a written comparison after both paths can be started. That
chart is not in this draft.

### Copy P01 workflows per tenant on one instance

Rejected: N copies to patch, no single config version, easy to mix
credentials in execution data.

## Consequences

- Workflows in P05 are generic (`[P05] Tenant Lead Intake` and the rest
  listed in the spec). They fetch non-secret config from the tenant
  backend once per execution and record the config version they used.
- The follow-up scheduler must batch fairly per tenant (round-robin), not
  one global oldest-first query that a large tenant can dominate.
- RLS tests are written before any service uses the tables
  (`db/tests/test_rls_no_context.sql`, `db/tests/test_rls_cross_read.sql`).
- README and this ADR both state the licence note. Public text must not
  present P05 as a product others can buy hosted access to.
- Integration-proxy language (FastAPI vs Go) is not decided here. Owner
  picks that in a later ADR (spec P05-T01). Until then, no proxy code.
- Community Edition only ([0003](../../../docs/adr/0003-community-edition-only.md)):
  no n8n Variables, external secrets, or multi-main.
