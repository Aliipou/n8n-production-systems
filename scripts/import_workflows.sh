#!/usr/bin/env bash
# Import test credentials and workflows into n8n-main, then publish each workflow.
#
# Flags from https://docs.n8n.io/deploy/host-n8n/configure-n8n/use-the-command-line
# (fetched 2026-09-11):
#   n8n import:credentials --input=<file>
#   n8n import:workflow --separate --input=<dir>
#   n8n publish:workflow --id=<id>
# TODO(verify): those flags against `n8n <command> --help` on n8n 2.37.9.
# Do not use update:workflow (deprecated in 2.0). publish:workflow has no --all.
#
# n8n 2.0 replaced update:workflow with publish:workflow (no --all):
#   https://docs.n8n.io/changelog/v20-breaking-changes.md
# Official note: CLI publish/unpublish writes the database; if n8n is already
# running, a restart may be required before the editor shows the new state.
# TODO(verify): whether restart is still required on the pinned image when
# compose exec talks to the live n8n-main process.
#
# If a pinned image rejects a flag, inspect live help instead of inventing flags:
#   docker compose exec n8n-main n8n import:workflow --help
#   docker compose exec n8n-main n8n publish:workflow --help
#
# Credentials: platform/ci/credentials.template.json with ${VAR} substituted.
# Values are mock URLs and test tokens only.
# TODO(verify): openAiApi data.url / header, httpHeaderAuth, and postgres
# field names against n8n 2.37.9 credential schemas.
#
# Usage: scripts/import_workflows.sh <platform|p01|p02|p03|p04|p05>
# Env: P (same as the first argument), COMPOSE_FILE, and credential placeholders.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT}"

if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
else
  PYTHON=python
fi

P="${1:-${P:-}}"
if [[ -z "${P}" ]]; then
  echo "usage: $0 <platform|p01|p02|p03|p04|p05>" >&2
  exit 2
fi

resolve_workflows_dir() {
  local p="$1"
  if [[ "${p}" == "platform" || "${p}" == "plt" || "${p}" == "PLT" ]]; then
    echo "${ROOT}/platform/workflows"
    return
  fi
  if [[ -d "${ROOT}/projects/${p}/workflows" ]]; then
    echo "${ROOT}/projects/${p}/workflows"
    return
  fi
  local match
  match="$(find "${ROOT}/projects" -maxdepth 1 -type d -name "${p}-*" 2>/dev/null | sort | head -n 1 || true)"
  if [[ -n "${match}" ]]; then
    echo "${match}/workflows"
    return
  fi
  echo "${ROOT}/projects/${p}/workflows"
}

SRC="$(resolve_workflows_dir "${P}")"
TEMPLATE="${ROOT}/platform/ci/credentials.template.json"

if [[ ! -d "${SRC}" ]]; then
  echo "error: workflow directory does not exist: ${SRC}" >&2
  exit 2
fi
if [[ ! -f "${TEMPLATE}" ]]; then
  echo "error: missing ${TEMPLATE}" >&2
  exit 2
fi

# Test-only defaults. Never put real tokens in this script.
export MOCK_LLM_API_KEY="${MOCK_LLM_API_KEY:-test-token-not-a-secret}"
export MOCK_LLM_URL="${MOCK_LLM_URL:-http://mock-llm:8090/v1}"
export INTERNAL_API_TOKEN="${INTERNAL_API_TOKEN:-test-token-not-a-secret}"
export POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
export POSTGRES_DB_APP="${POSTGRES_DB_APP:-app}"
export POSTGRES_USER="${POSTGRES_USER:-n8n_app}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-test-token-not-a-secret}"
export POSTGRES_PORT="${POSTGRES_PORT:-5432}"

compose() {
  local files=()
  if [[ -n "${COMPOSE_FILE:-}" ]]; then
    docker compose "$@"
    return
  fi
  if [[ -f "${ROOT}/platform/compose/docker-compose.base.yml" ]]; then
    files+=(-f "${ROOT}/platform/compose/docker-compose.base.yml")
  fi
  local overlay=""
  if [[ -f "${ROOT}/projects/${P}/docker-compose.yml" ]]; then
    overlay="${ROOT}/projects/${P}/docker-compose.yml"
  else
    overlay="$(find "${ROOT}/projects" -maxdepth 2 -type f -path "${ROOT}/projects/${P}-*/docker-compose.yml" 2>/dev/null | sort | head -n 1 || true)"
  fi
  if [[ -n "${overlay}" ]]; then
    files+=(-f "${overlay}")
  fi
  docker compose "${files[@]}" "$@"
}

HOST_TMP="$(mktemp -d "${TMPDIR:-/tmp}/n8n-import.XXXXXX")"
cleanup() { rm -rf "${HOST_TMP}"; }
trap cleanup EXIT

CREDS_RENDERED="${HOST_TMP}/credentials.json"
"${PYTHON}" - "${TEMPLATE}" "${CREDS_RENDERED}" <<'PY'
import json
import os
import re
import sys
from pathlib import Path

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
pattern = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

def repl(match):
    return os.environ.get(match.group(1), "")

text = pattern.sub(repl, src.read_text(encoding="utf-8"))
data = json.loads(text)
if isinstance(data, dict):
    data = [data]
for cred in data:
    fields = cred.get("data") if isinstance(cred, dict) else None
    if not isinstance(fields, dict):
        continue
    port = fields.get("port")
    if isinstance(port, str) and port.isdigit():
        fields["port"] = int(port)
dst.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY

CONTAINER_IMPORT="/tmp/n8n-import"
# TODO(verify): container user on the image pinned in platform/VERSIONS.md.
compose exec -T -u node n8n-main mkdir -p "${CONTAINER_IMPORT}/workflows"
compose cp "${CREDS_RENDERED}" "n8n-main:${CONTAINER_IMPORT}/credentials.json"
compose cp "${SRC}/." "n8n-main:${CONTAINER_IMPORT}/workflows/"

echo "importing credentials from credentials.template.json"
compose exec -T -u node n8n-main \
  n8n import:credentials --input="${CONTAINER_IMPORT}/credentials.json"

echo "importing workflows from ${SRC}"
compose exec -T -u node n8n-main \
  n8n import:workflow --separate --input="${CONTAINER_IMPORT}/workflows"

# Publish individually. publish:workflow has no --all (intentional in n8n 2.0).
published=0
shopt -s nullglob
for file in "${SRC}"/*.json; do
  id="$("${PYTHON}" -c "
import json, sys
with open(sys.argv[1], encoding='utf-8') as handle:
    data = json.load(handle)
if isinstance(data, dict) and data.get('id'):
    print(data['id'])
" "${file}")"
  if [[ -z "${id}" ]]; then
    echo "warning: no id in ${file}, skipping publish" >&2
    continue
  fi
  echo "publishing workflow id=${id} ($(basename "${file}"))"
  compose exec -T -u node n8n-main n8n publish:workflow --id="${id}"
  published=$((published + 1))
done

echo "imported credentials and published ${published} workflow(s)"
echo "if the editor still shows drafts, restart n8n-main (CLI publish writes the database)"
