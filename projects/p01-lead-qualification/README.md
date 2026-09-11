# P01 Lead Qualification

Personal portfolio project (reference implementation, synthetic data only). Not client work. Not a production deployment.

n8n orchestrates intake, routing, CRM sync, review, and follow-ups. This backend normalizes form fields and scores leads with a pure function over `backend/config/scoring.yaml`. The LLM may add at most 20 of 100 score points. It does not pick the route.

Status: not runnable until the platform compose stack exists (`platform/compose/docker-compose.base.yml`, PLT-T03) and `make up P=p01` can start it.

Results: not measured yet.
