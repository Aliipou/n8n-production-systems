"""Finnish 7-3-1 reference and ISO 11649 RF creditor reference."""

from __future__ import annotations

import pytest

from p02_doc_service.validators.reference import reference_number

CASES: list[tuple[str, str | None, bool, str]] = [
    ("fi_12345672", "12345672", True, "ok"),
    ("fi_min_length", "1232", True, "ok"),
    ("fi_spaces", "12345 672", True, "ok"),
    ("fi_check_zero", "0000", True, "ok"),
    ("fi_11111111", "11111111", True, "ok"),
    ("fi_9999992", "9999992", True, "ok"),
    ("fi_20_digits", "12345678901234567894", True, "ok"),
    ("rf_iso_example", "RF18539007547034", True, "ok"),
    ("rf_spaced", "RF18 5390 0754 7034", True, "ok"),
    ("rf_from_finnish_body", "RF8512345672", True, "ok"),
    ("rf_alpha_payload", "RF47ABC123", True, "ok"),
    ("fi_wrong_check", "12345673", False, "checksum"),
    ("fi_too_short", "123", False, "length"),
    ("fi_too_long", "123456789012345678901", False, "length"),
    ("fi_letters", "1234567A", False, "charset"),
    ("rf_wrong_check", "RF18539007547035", False, "checksum"),
    ("rf_too_short", "RF18", False, "length"),
    ("empty", "", False, "empty"),
    ("none", None, False, "empty"),
]


@pytest.mark.parametrize(
    ("case_id", "value", "passed", "reason"),
    CASES,
    ids=[item[0] for item in CASES],
)
def test_reference_table(case_id: str, value: str | None, passed: bool, reason: str) -> None:
    result = reference_number(value)
    assert result.passed is passed, case_id
    assert result.rule == "reference_number"
    if passed:
        return
    assert result.details["reason"] == reason, case_id
