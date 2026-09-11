# ADR 0003: n8n Community Edition only

Date: 2026-09-11
Status: Accepted

## Context

n8n is a product of n8n GmbH and is licensed separately from this repository (Sustainable Use License at the time `NOTICE` was written). This repo does not vendor or redistribute n8n. Self-hosted Community Edition is what a laptop clone can run from `make up` without a paid n8n plan. Enterprise features (Variables, external secrets, log streaming, source-control environments, SSO) would make the demos unreproducible for readers who only run Community Edition.

Project P05 describes a multi-tenant automation layout. Running n8n as a hosted service for paying clients may need a separate commercial agreement with n8n. That is a licence question for the owner and for n8n GmbH, not something this repo decides.

## Decision

Use only features of free self-hosted Community Edition on a pinned stable 2.x release. Do not depend on Enterprise features. P05 is labelled a reference architecture for learning and demonstration. READMEs and `NOTICE` point at the current n8n licence text. This repository's own code is MIT.

## Alternatives

1. Use n8n Cloud or Enterprise so Variables, SSO, and log streaming are available. Demos would not run from `.env.example` on a laptop. The portfolio would not match what most freelance clients self-host.
2. Ignore the n8n licence and describe P05 as a product you can sell hosted access to. That would be a false claim and a licensing risk.
3. Replace n8n with another orchestrator that is OSI-licensed. Out of scope for this portfolio.

## Consequences

- Workflows must use credentials, a settings table, or backend config instead of Enterprise Variables.
- Secrets stay in n8n credentials or in backends, not in execution data.
- P05 README must repeat the licence note. It is not a hosted product and not an offer to run n8n as a service for paying clients.
- TODO(verify): confirm the licence URL in `NOTICE` against the docs of the pinned n8n version (PLT-T02).
- Owner must read the current n8n licence before any public claim about commercial use. This ADR does not interpret that licence beyond "read it and do not claim Enterprise or hosted-product rights."
