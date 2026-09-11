from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_LIB = Path(__file__).resolve().parent
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

from errors import (  # noqa: E402
    BASE_DELAY_S,
    CAP_DELAY_S,
    MAX_ATTEMPTS,
    classify_error,
    compute_next_delay,
)

FIXTURE_PATH = _LIB.parent / "fixtures" / "error_cases.json"
FIXTURE = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def lcg(seed: int):
    state = seed & 0xFFFFFFFF

    def jitter() -> float:
        nonlocal state
        state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
        return state / 4294967296

    return jitter


@pytest.mark.parametrize("case", FIXTURE["cases"], ids=lambda case: case["id"])
def test_classify_error_fixture(case: dict) -> None:
    assert classify_error(case["input"]) == case["expected"]


def test_classify_error_none_is_unknown() -> None:
    assert classify_error(None) == {
        "class": "unknown",
        "retry": False,
        "idempotent_success": False,
    }


def test_classify_error_camel_case_idempotent_create() -> None:
    assert classify_error({"status": 409, "idempotentCreate": True}) == {
        "class": "success",
        "retry": False,
        "idempotent_success": True,
    }


def test_backoff_constants_match_fixture() -> None:
    backoff = FIXTURE["backoff"]
    assert MAX_ATTEMPTS == backoff["max_attempts"]
    assert BASE_DELAY_S == backoff["base_s"]
    assert CAP_DELAY_S == backoff["cap_s"]


@pytest.mark.parametrize(
    "row", FIXTURE["delay_ceilings"], ids=lambda row: f"attempt_{row['attempt']}"
)
def test_compute_next_delay_ceilings(row: dict) -> None:
    assert (
        compute_next_delay(row["attempt"], BASE_DELAY_S, CAP_DELAY_S, lambda: 1)
        == row["ceiling"]
    )


def test_compute_next_delay_zero_jitter() -> None:
    assert compute_next_delay(4, 2, 300, lambda: 0) == 0


def test_compute_next_delay_half_jitter() -> None:
    assert compute_next_delay(2, 2, 300, lambda: 0.5) == 4


def test_compute_next_delay_seeded_jitter() -> None:
    first = compute_next_delay(3, 2, 300, lcg(1))
    second = compute_next_delay(3, 2, 300, lcg(1))
    other = compute_next_delay(3, 2, 300, lcg(2))
    assert first == second
    assert 0 <= first <= 16
    assert other != first


def test_compute_next_delay_defaults() -> None:
    assert compute_next_delay(0, jitter_fn=lambda: 1) == 2
