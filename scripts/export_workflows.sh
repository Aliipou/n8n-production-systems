#!/usr/bin/env bash
# Export workflows from the n8n-main container, then sanitize and lint.
#
# Flags from https://docs.n8n.io/deploy/host-n8n/configure-n8n/use-the-command-line
# (fetched 2026-09-11):
#   n8n export:workflow --all --pretty --separate --output=<dir>
#   --separate writes one file per workflow and requires --output as a directory.
#   --pretty formats JSON. --all exports every workflow.
# TODO(verify): on n8n 2.37.9, whether git exports should also pass --published
# (docs: exports the published version; with --all, unpublished workflows skip).
# This script exports the current editor copy (draft) so local canvas work is kept.
#
# n8n 2.0 publishing (used by import_workflows.sh, not here):
#   update:workflow is deprecated. Use publish:workflow --id=<id> (no --all).
#
# If a pinned image rejects a flag, inspect live help instead of inventing flags:
#   docker compose exec n8n-main n8n export:workflow --help
#
# Usage: scripts/export_workflows.sh <platform|p01|p02|p03|p04|p05>
# Env: P (same as the first argument), COMPOSE_FILE / extra compose -f files.

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

name_prefix() {
  local p="$1"
  case "${p}" in
    platform|plt|PLT) echo "[PLT]" ;;
    p01|P01) echo "[P01]" ;;
    p02|P02) echo "[P02]" ;;
    p03|P03) echo "[P03]" ;;
    p04|P04) echo "[P04]" ;;
    p05|P05) echo "[P05]" ;;
    *) echo "[${p^^}]" ;;
  esac
}

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

PREFIX="$(name_prefix "${P}")"
DEST="$(resolve_workflows_dir "${P}")"
mkdir -p "${DEST}"

compose() {
  local files=()
  if [[ -n "${COMPOSE_FILE:-}" ]]; then
    # Caller supplied COMPOSE_FILE; docker compose reads it itself.
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

CONTAINER_EXPORT="/tmp/n8n-export-workflows"

echo "exporting workflows from n8n-main to ${DEST} (keeping names starting with ${PREFIX})"

# Official Docker CLI examples use -u node. -T is for non-interactive CI.
# TODO(verify): container user on the image pinned in platform/VERSIONS.md.
compose exec -T -u node n8n-main mkdir -p "${CONTAINER_EXPORT}"
compose exec -T -u node n8n-main sh -c "rm -rf '${CONTAINER_EXPORT}'/*"
compose exec -T -u node n8n-main \
  n8n export:workflow --all --pretty --separate --output="${CONTAINER_EXPORT}"

HOST_TMP="$(mktemp -d "${TMPDIR:-/tmp}/n8n-export.XXXXXX")"
cleanup() { rm -rf "${HOST_TMP}"; }
trap cleanup EXIT

compose cp "n8n-main:${CONTAINER_EXPORT}/." "${HOST_TMP}/"

copied=0
shopt -s nullglob
for file in "${HOST_TMP}"/*.json; do
  if "${PYTHON}" -c "
import json, sys
path = sys.argv[1]
prefix = sys.argv[2]
with open(path, encoding='utf-8') as handle:
    data = json.load(handle)
name = data.get('name', '') if isinstance(data, dict) else ''
sys.exit(0 if name.startswith(prefix) else 1)
" "${file}" "${PREFIX}"; then
    cp "${file}" "${DEST}/$(basename "${file}")"
    copied=$((copied + 1))
  fi
done

echo "copied ${copied} workflow file(s) into ${DEST}"

"${PYTHON}" "${ROOT}/scripts/sanitize_workflows.py" --in-place "${DEST}"
"${PYTHON}" "${ROOT}/scripts/lint_workflows.py" --dir "${DEST}"
