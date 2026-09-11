"""Invoice and due date parsing. Frozen today is 2026-09-11."""

from __future__ import annotations

from datetime import date

import pytest

from p02_doc_service.validators.dates import dates, parse_date

TODAY = date(2026, 9, 11)

CASES: list[tuple[str, str | None, str | None, bool, str]] = [
    ("iso_pair", "2024-01-15", "2024-01-31", True, "ok"),
    ("finnish_pair", "15.1.2024", "31.1.2024", True, "ok"),
    ("finnish_padded", "15.01.2024", "31.01.2024", True, "ok"),
    ("mixed_formats", "15.1.2024", "2024-01-31", True, "ok"),
    ("due_same_day", "2024-06-01", "2024-06-01", True, "ok"),
    ("invoice_today", "2026-09-11", "2026-09-12", True, "ok"),
    ("due_before_invoice", "2024-01-31", "2024-01-15", False, "due_before_invoice"),
    ("invoice_tomorrow", "2026-09-12", "2026-09-13", False, "invoice_in_future"),
    ("invalid_february", "31.2.2024", "1.3.2024", False, "unparsed_invoice_date"),
    ("invalid_iso_month", "2024-13-01", "2024-13-02", False, "unparsed_invoice_date"),
    ("us_slash_rejected", "01/15/2024", "01/31/2024", False, "unparsed_invoice_date"),
    ("missing_invoice", None, "2024-01-31", False, "missing_invoice_date"),
    ("missing_due", "2024-01-15", None, False, "missing_due_date"),
    ("empty_invoice", "", "2024-01-31", False, "missing_invoice_date"),
    ("unparsed_due", "2024-01-15", "not-a-date", False, "unparsed_due_date"),
    ("iso_datetime_rejected", "2024-01-15T00:00:00", "2024-01-31", False, "unparsed_invoice_date"),
]


@pytest.mark.parametrize(
    ("case_id", "invoice", "due", "passed", "reason"),
    CASES,
    ids=[item[0] for item in CASES],
)
def test_dates_table(
    case_id: str,
    invoice: str | None,
    due: str | None,
    passed: bool,
    reason: str,
) -> None:
    result = dates(invoice, due, today=TODAY)
    assert result.passed is passed, case_id
    assert result.rule == "dates"
    if passed:
        return
    assert result.details["reason"] == reason, case_id


def test_parse_date_finnish_and_iso() -> None:
    assert parse_date("1.2.2024") == date(2024, 2, 1)
    assert parse_date("2024-02-01") == date(2024, 2, 1)
    assert parse_date("29.2.2024") == date(2024, 2, 29)
    assert parse_date("29.2.2023") is None
