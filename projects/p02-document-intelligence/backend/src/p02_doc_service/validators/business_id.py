"""Finnish Y-tunnus checksum (PRH / YTJ). Pure function."""

from __future__ import annotations

import re

from p02_doc_service.validators.result import RuleResult

RULE = "business_id_checksum"
FIELD = "supplier_business_id"
WEIGHTS = (7, 9, 10, 5, 8, 4, 2)
PATTERN = re.compile(r"^(\d{7})-(\d)$")


def business_id_checksum(value: str | None) -> RuleResult:
    raw = (value or "").strip()
    if not raw:
        return RuleResult(
            rule=RULE,
            field=FIELD,
            passed=False,
            details={"reason": "empty"},
        )
    match = PATTERN.fullmatch(raw)
    if match is None:
        return RuleResult(
            rule=RULE,
            field=FIELD,
            passed=False,
            details={"reason": "format", "expected": "NNNNNNN-N"},
        )
    body, check_s = match.group(1), match.group(2)
    total = sum(int(digit) * weight for digit, weight in zip(body, WEIGHTS, strict=True))
    remainder = total % 11
    if remainder == 1:
        return RuleResult(
            rule=RULE,
            field=FIELD,
            passed=False,
            details={"reason": "remainder_1", "remainder": remainder, "sum": total},
        )
    expected = 0 if remainder == 0 else 11 - remainder
    actual = int(check_s)
    if actual != expected:
        return RuleResult(
            rule=RULE,
            field=FIELD,
            passed=False,
            details={
                "reason": "checksum",
                "expected_check_digit": expected,
                "actual_check_digit": actual,
                "remainder": remainder,
            },
        )
    return RuleResult(
        rule=RULE,
        field=FIELD,
        passed=True,
        details={"check_digit": actual, "remainder": remainder},
    )
