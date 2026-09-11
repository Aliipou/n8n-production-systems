.PHONY: help up down reset import export sync-snippets test e2e check demo eval chaos

P ?=
SCENARIO ?=

COMPOSE_FILE := platform/compose/docker-compose.base.yml
COMPOSE := docker compose --project-directory . -f $(COMPOSE_FILE)

ifneq ($(P),)
COMPOSE += -f projects/$(P)/docker-compose.yml
endif

help:
	@echo "n8n-production-systems"
	@echo "  make up P=<project>       Start platform plus one project"
	@echo "  make up                   Start platform only"
	@echo "  make down                 Stop the stack"
	@echo "  make reset                Destroy local volumes after confirm"
	@echo "  make import P=<project>   Import and publish workflows (PLT-T07)"
	@echo "  make export P=<project>   Export, sanitize, lint (PLT-T07)"
	@echo "  make sync-snippets        Copy code-snippets into Code nodes (PLT-T07)"
	@echo "  make test                 Unit tests (later tasks)"
	@echo "  make e2e P=<project>      End-to-end tests (later tasks)"
	@echo "  make check                Lint, unit tests, secret scan, workflow lint"
	@echo "  make demo P=<project>     Scripted demo (project tasks)"
	@echo "  make eval P=p02           Evaluation run, never in CI (P02)"
	@echo "  make chaos SCENARIO=<n>   Chaos scenario (P04)"

up:
	@test -f .env || (echo "Copy .env.example to .env and set secrets first." && exit 1)
ifneq ($(P),)
	@test -f projects/$(P)/docker-compose.yml || (echo "missing projects/$(P)/docker-compose.yml" && exit 1)
endif
	$(COMPOSE) --env-file .env up -d --build --wait --wait-timeout 180
	@echo "n8n        http://127.0.0.1:5678"
	@echo "Mailpit    http://127.0.0.1:8025"
	@echo "mock-llm   http://127.0.0.1:8090"
	@echo "flaky-api  http://127.0.0.1:8091"
	@echo "review-ui  http://127.0.0.1:8092"

down:
	@test -f .env || (echo "Copy .env.example to .env and set secrets first." && exit 1)
	$(COMPOSE) --env-file .env down

reset:
	@test -f .env || (echo "Copy .env.example to .env and set secrets first." && exit 1)
	@echo "This deletes compose volumes (postgres, redis, n8n, mailpit data)."
	@echo "Type yes to continue"
	@read confirm; \
	if [ "$$confirm" != "yes" ]; then echo "aborted"; exit 1; fi
	$(COMPOSE) --env-file .env down -v

import:
	@if [ ! -f scripts/import_workflows.sh ]; then \
		echo "error: not implemented until PLT-T07 (scripts/import_workflows.sh missing)" >&2; \
		exit 1; \
	fi
	P=$(P) ./scripts/import_workflows.sh

export:
	@if [ ! -f scripts/export_workflows.sh ]; then \
		echo "error: not implemented until PLT-T07 (scripts/export_workflows.sh missing)" >&2; \
		exit 1; \
	fi
	P=$(P) ./scripts/export_workflows.sh

sync-snippets:
	python scripts/sync_snippets.py

test:
	$(error not implemented until backend and snippet tests exist)

e2e:
	$(error not implemented until PLT-T13)

check:
	@echo "PLT-T01 skeleton check: gitleaks/pre-commit when installed; full make check lands in later tasks"
	@if command -v pre-commit >/dev/null 2>&1; then pre-commit run --all-files; else echo "pre-commit not installed"; fi

demo:
	$(error not implemented until the project demo script exists)

eval:
	$(error not implemented until P02)

chaos:
	$(error not implemented until P04)
