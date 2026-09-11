"""PLT-T13: flaky-api 500, DLQ, Mailpit notify, heal, retry, one success.

Runs only when compose is up and platform workflow JSON exists.
Without those, the tests skip so unit CI stays usable on machines without Docker.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import pytest

from conftest import MAILPIT_MESSAGES, _get, post_json

FLAKY_ADMIN_MODE = os.environ.get(
    "FLAKY_API_ADMIN_MODE_URL",
    "http://127.0.0.1:8091/admin/mode",
)
FLAKY_ADMIN_RESET = os.environ.get(
    "FLAKY_API_ADMIN_RESET_URL",
    "http://127.0.0.1:8091/admin/reset",
)
FLAKY_ADMIN_STATS = os.environ.get(
    "FLAKY_API_ADMIN_STATS_URL",
    "http://127.0.0.1:8091/admin/stats",
)
PROBE_WEBHOOK = os.environ.get("PLT_PROBE_WEBHOOK_URL", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Poll budget for schedule-driven DLQ replay. One minute cadence plus jitter.
POLL_TIMEOUT_S = float(os.environ.get("PLT_E2E_POLL_TIMEOUT_S", "90"))
POLL_INTERVAL_S = float(os.environ.get("PLT_E2E_POLL_INTERVAL_S", "2"))


def _json_get(url: str) -> dict[str, Any]:
    status, body = _get(url, timeout=5.0)
    if status != 200:
        return {}
    try:
        parsed = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


@pytest.mark.usefixtures("require_workflows")
def test_stack_health_endpoints_are_ok() -> None:
    status, _ = _get("http://127.0.0.1:5678/healthz")
    assert status == 200
    status, _ = _get("http://127.0.0.1:8091/health")
    assert status == 200


@pytest.mark.usefixtures("require_workflows")
def test_flaky_500_then_heal_records_exactly_one_success() -> None:
    """Spec 00 section 10 PLT-T13.

    Needs:
    - published `[PLT] Flaky Probe` webhook URL in PLT_PROBE_WEBHOOK_URL
    - `[PLT] Error Handler`, `[PLT] Notify`, `[PLT] DLQ Retrier`
    - DATABASE_URL to database `app` for dead_letter and execution_log checks
    """
    if not PROBE_WEBHOOK:
        pytest.skip("PLT_PROBE_WEBHOOK_URL is unset until workflows are imported")
    if not DATABASE_URL:
        pytest.skip("DATABASE_URL is unset; cannot assert ops.dead_letter rows")

    psycopg = pytest.importorskip("psycopg")

    reset_status, _ = post_json(FLAKY_ADMIN_RESET, {})
    if reset_status not in {200, 204}:
        pytest.fail(f"flaky-api /admin/reset returned {reset_status}")

    mode_status, _ = post_json(
        FLAKY_ADMIN_MODE,
        {"route": "GET /items", "status": 500, "error_rate": 1},
    )
    assert mode_status in {200, 204}

    probe_status, _ = post_json(PROBE_WEBHOOK, {"probe": "plt-t13"})
    assert probe_status in {202, 200, 500}

    deadline = time.monotonic() + POLL_TIMEOUT_S
    dead_letter_seen = False
    with psycopg.connect(DATABASE_URL) as conn:
        conn.autocommit = True
        while time.monotonic() < deadline:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM ops.dead_letter "
                    "WHERE status IN ('pending_retry', 'dead')"
                )
                row = cur.fetchone()
                if row is not None and int(row[0]) >= 1:
                    dead_letter_seen = True
                    break
            time.sleep(POLL_INTERVAL_S)
    assert dead_letter_seen, "expected a dead_letter row after flaky-api 500"

    mail = _json_get(MAILPIT_MESSAGES)
    messages = mail.get("messages")
    if not isinstance(messages, list) or len(messages) < 1:
        pytest.fail("expected at least one Mailpit message after the failure notify")

    heal_status, _ = post_json(FLAKY_ADMIN_RESET, {})
    assert heal_status in {200, 204}

    replayed = False
    deadline = time.monotonic() + POLL_TIMEOUT_S
    with psycopg.connect(DATABASE_URL) as conn:
        conn.autocommit = True
        while time.monotonic() < deadline:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM ops.dead_letter WHERE status = 'replayed'"
                )
                row = cur.fetchone()
                if row is not None and int(row[0]) >= 1:
                    replayed = True
                    break
            time.sleep(POLL_INTERVAL_S)
    assert replayed, "DLQ retrier did not mark a row replayed after heal"

    stats = _json_get(FLAKY_ADMIN_STATS)
    # TODO(verify): exact stats JSON shape on the running flaky-api image.
    success_count = stats.get("success") or stats.get("ok") or 0
    if isinstance(success_count, int):
        assert success_count == 1
    else:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM ops.execution_log WHERE event = 'probe_success'"
                )
                row = cur.fetchone()
        assert row is not None and int(row[0]) == 1
