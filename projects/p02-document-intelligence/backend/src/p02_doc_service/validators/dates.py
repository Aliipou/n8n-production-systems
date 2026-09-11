"""Invoice and due dates: Finnish d.m.yyyy and ISO YYYY-MM-DD."""

from __future__ import annotations

import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

from p02_doc_service.validators.result import RuleResult

RULE = "dates"
FIELD = "invoice_date"
FINNISH = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$")
ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def parse_date(value: str | None) -> date | None:
    raw = (value or "").strip()
    if not raw:
        return None
    match = FINNISH.fullmatch(raw)
    if match:
        day, month, year = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        try:
            return date(year, month, day)
        except ValueError:
            return None
    match = ISO.fullmatch(raw)
    if match:
        year, month, day = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        try:
            return date(year, month, day)
        except ValueError:
            return None
    return None


def dates(
    invoice_date: str | None,
    due_date: str | None,
    *,
    today: date,
) -> RuleResult:
    if not (invoice_date or "").strip():
        return RuleResult(
            rule=RULE,
            field=FIELD,
            passed=False,
            details={"reason": "missing_invoice_date"},
        )
    parsed_invoice = parse_date(invoice_date)
    if parsed_invoice is None:
        return RuleResult(
            rule=RULE,
            field=FIELD,
            passed=False,
            details={"reason": "unparsed_invoice_date", "value": invoice_date},
        )
    if parsed_invoice > today:
        return RuleResult(
            rule=RULE,
            field=FIELD,
            passed=False,
            details={
                "reason": "invoice_in_future",
                "invoice_date": parsed_invoice.isoformat(),
                "today": today.isoformat(),
            },
        )
    if not (due_date or "").strip():
        return RuleResult(
            rule=RULE,
            field=FIELD,
            passed=False,
            details={"reason": "missing_due_date", "invoice_date": parsed_invoice.isoformat()},
        )
    parsed_due = parse_date(due_date)
    if parsed_due is None:
        return RuleResult(
            rule=RULE,
            field=FIELD,
            passed=False,
            details={"reason": "unparsed_due_date", "value": due_date},
        )
    if parsed_due < parsed_invoice:
        return RuleResult(
            rule=RULE,
            field=FIELD,
            passed=False,
            details={
                "reason": "due_before_invoice",
                "invoice_date": parsed_invoice.isoformat(),
                "due_date": parsed_due.isoformat(),
            },
        )
    return RuleResult(
        rule=RULE,
        field=FIELD,
        passed=True,
        details={
            "invoice_date": parsed_invoice.isoformat(),
            "due_date": parsed_due.isoformat(),
            "today": today.isoformat(),
        },
    )


def today_helsinki() -> date:
    return datetime.now(ZoneInfo("Europe/Helsinki")).date()
