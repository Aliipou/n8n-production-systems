.PHONY: help up down reset import export sync-snippets test e2e check demo eval chaos

P ?=
SCENARIO ?=

COMPOSE_FILE := platform/compose/docker-compose.base.yml
COMPOSE := docker compose --project-directory . -f $(COMPOSE_FILE)

P_DIR := $(P)
ifeq ($(P),p01)
P_DIR := p01-lead-qualification
endif
ifeq ($(P),p02)
P_DIR := p02-document-intelligence
endif
ifeq ($(P),p03)
P_DIR := p03-webhook-gateway
endif
ifeq ($(P),p04)
P_DIR := p04-reliability
endif
ifeq ($(P),p05)
P_DIR := p05-multi-tenant
endif

ifneq ($(P_DIR),)
COMPOSE += -f projects/$(P_DIR)/docker-compose.yml
endif

PYTHON ?= python

help:
	@echo "n8n-production-systems"
	@echo "  make up P=<p01|p02|p03|p04|p05>  Start platform plus one project"
	@echo "  make up                   Start platform only"
	@echo "  make down                 Stop the stack"
	@echo "  make reset                Destroy local volumes after confirm"
	@echo "  make import P=<project>   Import and publish workflows"
	@echo "  make export P=<project>   Export, sanitize, lint"
	@echo "  make sync-snippets        Copy code-snippets into Code nodes"
	@echo "  make test                 Python, Go, and snippet unit tests"
	@echo "  make e2e P=<project>      End-to-end tests (skip without stack)"
	@echo "  make check                Unit tests plus workflow lint"
	@echo "  make demo P=<project>     Scripted demo when the project has one"
	@echo "  make eval P=p02           Evaluation run, never in CI (P02)"
	@echo "  make chaos SCENARIO=<n>   Chaos scenario (P04)"

up:
	@test -f .env || (echo "Copy .env.example to .env and set secrets first." && exit 1)
ifneq ($(P_DIR),)
	@test -f projects/$(P_DIR)/docker-compose.yml || (echo "missing projects/$(P_DIR)/docker-compose.yml" && exit 1)
endif
	$(COMPOSE) --env-file .env up -d --build --wait --wait-timeout 180
	@echo "n8n        http://127.0.0.1:5678"
	@echo "Mailpit    http://127.0.0.1:8025"
	@echo "mock-llm   http://127.0.0.1:8090"
	@echo "flaky-api  http://127.0.0.1:8091"
	@echo "review-ui  http://127.0.0.1:8092"
	@echo "P01        http://127.0.0.1:8101"
	@echo "P02        http://127.0.0.1:8102"
	@echo "P03        http://127.0.0.1:8103"

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
	P=$(if $(P),$(P),platform) ./scripts/import_workflows.sh

export:
	P=$(if $(P),$(P),platform) ./scripts/export_workflows.sh

sync-snippets:
	$(PYTHON) scripts/sync_snippets.py

test:
	$(PYTHON) scripts/run_unit_tests.py

e2e:
	$(PYTHON) -m pytest -q platform/tests/e2e
ifneq ($(P_DIR),)
	@if [ -d projects/$(P_DIR)/tests/e2e ]; then $(PYTHON) -m pytest -q projects/$(P_DIR)/tests/e2e; fi
endif

check:
	$(PYTHON) scripts/run_unit_tests.py
	@if find platform/workflows projects -name '*.json' -type f 2>/dev/null | grep -q .; then \
		$(PYTHON) scripts/lint_workflows.py; \
	else \
		echo "No workflow JSON yet; skipping lint_workflows.py"; \
	fi
	@if command -v pre-commit >/dev/null 2>&1; then pre-commit run --all-files; else echo "pre-commit not installed"; fi

demo:
	@if [ -z "$(P_DIR)" ]; then echo "usage: make demo P=p01" >&2; exit 2; fi
	@if [ ! -f projects/$(P_DIR)/scripts/demo.sh ]; then \
		echo "error: projects/$(P_DIR)/scripts/demo.sh is not implemented yet" >&2; \
		exit 1; \
	fi
	P=$(P_DIR) ./projects/$(P_DIR)/scripts/demo.sh

eval:
	@if [ "$(P)" != "p02" ] && [ "$(P_DIR)" != "p02-document-intelligence" ]; then \
		echo "usage: make eval P=p02" >&2; exit 2; \
	fi
	@if [ ! -f projects/p02-document-intelligence/scripts/eval.sh ]; then \
		echo "error: P02 eval script is not implemented yet" >&2; \
		exit 1; \
	fi
	./projects/p02-document-intelligence/scripts/eval.sh

chaos:
	@if [ -z "$(SCENARIO)" ]; then echo "usage: make chaos SCENARIO=<name>" >&2; exit 2; fi
	@if [ ! -f projects/p04-reliability/chaos/$(SCENARIO) ]; then \
		echo "error: chaos scenario $(SCENARIO) is not implemented yet" >&2; \
		exit 1; \
	fi
	./projects/p04-reliability/chaos/$(SCENARIO)
