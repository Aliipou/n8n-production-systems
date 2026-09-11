"""PLT-T13 helpers. Skip when the local stack or workflow JSON is missing."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS_DIR = REPO_ROOT / "platform" / "workflows"
N8N_HEALTH = os.environ.get("N8N_HEALTH_URL", "http://127.0.0.1:5678/healthz")
FLAKY_HEALTH = os.environ.get("FLAKY_API_HEALTH_URL", "http://127.0.0.1:8091/health")
MAILPIT_MESSAGES = os.environ.get(
    "MAILPIT_MESSAGES_URL",
    "http://127.0.0.1:8025/api/v1/messages",
)


def _get(url: str, timeout: float = 2.0) -> tuple[int, bytes]:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(resp.status), resp.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, b""


def stack_reachable() -> bool:
    n8n_status, _ = _get(N8N_HEALTH)
    flaky_status, _ = _get(FLAKY_HEALTH)
    return n8n_status == 200 and flaky_status == 200


def committed_workflows() -> list[Path]:
    if not WORKFLOWS_DIR.is_dir():
        return []
    return sorted(p for p in WORKFLOWS_DIR.glob("*.json") if p.is_file())


@pytest.fixture(scope="session")
def require_stack() -> Iterator[None]:
    if not stack_reachable():
        pytest.skip(
            "n8n and flaky-api are not reachable on 127.0.0.1 "
            "(Docker is required for PLT-T03/T13)"
        )
    yield


@pytest.fixture(scope="session")
def require_workflows(require_stack: None) -> list[Path]:
    files = committed_workflows()
    if not files:
        pytest.skip(
            "No platform workflow JSON yet (PLT-T09/T11). "
            "JSON cannot be committed until import and e2e pass."
        )
    return files


def post_json(url: str, payload: dict[str, object], timeout: float = 5.0) -> tuple[int, bytes]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(resp.status), resp.read()
    except urllib.error.HTTPError as exc:
        return int(exc.code), exc.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, b""
