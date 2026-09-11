.PHONY: help up down reset import export sync-snippets test e2e check demo eval chaos

P ?=
SCENARIO ?=

help:
	@echo "n8n-production-systems"
	@echo "  make up P=<project>       Start platform plus one project (PLT-T03)"
	@echo "  make down                 Stop the stack (PLT-T03)"
	@echo "  make reset                Destroy local volumes after confirm (PLT-T03)"
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
	$(error not implemented until PLT-T03)

down:
	$(error not implemented until PLT-T03)

reset:
	$(error not implemented until PLT-T03)

import:
	$(error not implemented until PLT-T07)

export:
	$(error not implemented until PLT-T07)

sync-snippets:
	$(error not implemented until PLT-T07)

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
