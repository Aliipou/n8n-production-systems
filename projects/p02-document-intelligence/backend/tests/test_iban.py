"""Table-driven IBAN tests. ISO examples and invented FI numbers, not real invoices."""

from __future__ import annotations

import pytest

from p02_doc_service.validators.iban import iban_checksum

CASES: list[tuple[str, str | None, bool, str]] = [
    ("fi_iso_example", "FI2112345600000785", True, "ok"),
    ("fi_spaced", "FI21 1234 5600 0007 85", True, "ok"),
    ("fi_lowercase", "fi2112345600000785", True, "ok"),
    ("fi_invented_3191", "FI7631913000000001", True, "ok"),
    ("fi_invented_7998", "FI3679988800001234", True, "ok"),
    ("fi_all_ones", "FI4411111111111111", True, "ok"),
    ("de_iso_example", "DE89370400440532013000", True, "ok"),
    ("gb_iso_example", "GB82WEST12345698765432", True, "ok"),
    ("nl_iso_example", "NL91ABNA0417164300", True, "ok"),
    ("fi_too_short", "FI211234560000078", False, "fi_length"),
    ("fi_too_long", "FI21123456000007851", False, "fi_length"),
    ("wrong_checksum", "FI2012345600000785", False, "checksum"),
    ("empty", "", False, "empty"),
    ("none", None, False, "empty"),
    ("no_country", "2112345600000785", False, "format"),
    ("too_short_generic", "FI21", False, "length"),
    ("symbols", "FI21****5600000785", False, "charset"),
]


@pytest.mark.parametrize(
    ("case_id", "value", "passed", "reason"),
    CASES,
    ids=[item[0] for item in CASES],
)
def test_iban_table(case_id: str, value: str | None, passed: bool, reason: str) -> None:
    result = iban_checksum(value)
    assert result.passed is passed, case_id
    assert result.rule == "iban_checksum"
    if passed:
        assert result.details["country"] == (value or "").replace(" ", "").upper()[:2]
        return
    assert result.details["reason"] == reason, case_id
