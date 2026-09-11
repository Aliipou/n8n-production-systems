"""Table-driven Finnish Y-tunnus tests. Numbers are synthetic, not real companies."""

from __future__ import annotations

import pytest

from p02_doc_service.validators.business_id import business_id_checksum

CASES: list[tuple[str, str | None, bool, str]] = [
    ("valid_1234567_1", "1234567-1", True, "ok"),
    ("valid_2222222_9", "2222222-9", True, "ok"),
    ("valid_3333333_8", "3333333-8", True, "ok"),
    ("valid_check_zero", "1503224-0", True, "ok"),
    ("valid_9999999_2", "9999999-2", True, "ok"),
    ("valid_1000001_2", "1000001-2", True, "ok"),
    ("valid_leading_zero", "0123456-2", True, "ok"),
    ("valid_1000000_4", "1000000-4", True, "ok"),
    ("valid_2000000_8", "2000000-8", True, "ok"),
    ("valid_4567890_7", "4567890-7", True, "ok"),
    ("valid_stripped", " 1234567-1 ", True, "ok"),
    ("remainder_1_1111111", "1111111-1", False, "remainder_1"),
    ("remainder_1_0000006", "0000006-0", False, "remainder_1"),
    ("remainder_1_3456789", "3456789-8", False, "remainder_1"),
    ("wrong_check_digit", "1234567-9", False, "checksum"),
    ("missing_hyphen", "12345671", False, "format"),
    ("too_short", "123456-1", False, "format"),
    ("letters", "abcdefg-1", False, "format"),
    ("empty", "", False, "empty"),
    ("none", None, False, "empty"),
    ("vat_id_not_ytunnus", "FI12345671", False, "format"),
]


@pytest.mark.parametrize(
    ("case_id", "value", "passed", "reason"),
    CASES,
    ids=[item[0] for item in CASES],
)
def test_business_id_table(case_id: str, value: str | None, passed: bool, reason: str) -> None:
    result = business_id_checksum(value)
    assert result.passed is passed, case_id
    assert result.rule == "business_id_checksum"
    if passed:
        return
    assert result.details["reason"] == reason, case_id
