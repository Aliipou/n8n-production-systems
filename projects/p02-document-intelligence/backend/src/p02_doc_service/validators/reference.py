"""Finnish reference number (7-3-1) and RF creditor reference (ISO 11649)."""

from __future__ import annotations

from p02_doc_service.validators.iban import _mod97
from p02_doc_service.validators.result import RuleResult

RULE = "reference_number"
FIELD = "reference_number"
FI_WEIGHTS = (7, 3, 1)
FI_MIN_LEN = 4
FI_MAX_LEN = 20
RF_MIN_LEN = 5
RF_MAX_LEN = 25


def _compact(value: str) -> str:
    return "".join(value.split()).upper()


def _finnish_check_digit(body: str) -> int:
    total = 0
    for index, char in enumerate(reversed(body)):
        total += int(char) * FI_WEIGHTS[index % 3]
    return (10 - (total % 10)) % 10


def _finnish_reference(compact: str) -> RuleResult:
    if not compact.isdigit():
        return RuleResult(
            rule=RULE,
            field=FIELD,
            passed=False,
            details={"reason": "charset", "kind": "finnish"},
        )
    if not (FI_MIN_LEN <= len(compact) <= FI_MAX_LEN):
        return RuleResult(
            rule=RULE,
            field=FIELD,
            passed=False,
            details={"reason": "length", "kind": "finnish", "length": len(compact)},
        )
    body, actual = compact[:-1], int(compact[-1])
    expected = _finnish_check_digit(body)
    if actual != expected:
        return RuleResult(
            rule=RULE,
            field=FIELD,
            passed=False,
            details={
                "reason": "checksum",
                "kind": "finnish",
                "expected_check_digit": expected,
                "actual_check_digit": actual,
            },
        )
    return RuleResult(
        rule=RULE,
        field=FIELD,
        passed=True,
        details={"kind": "finnish", "check_digit": actual},
    )


def _rf_reference(compact: str) -> RuleResult:
    if not (RF_MIN_LEN <= len(compact) <= RF_MAX_LEN):
        return RuleResult(
            rule=RULE,
            field=FIELD,
            passed=False,
            details={"reason": "length", "kind": "rf", "length": len(compact)},
        )
    if not compact[2:4].isdigit():
        return RuleResult(
            rule=RULE,
            field=FIELD,
            passed=False,
            details={"reason": "format", "kind": "rf"},
        )
    payload = compact[4:]
    if not payload or not payload.isalnum():
        return RuleResult(
            rule=RULE,
            field=FIELD,
            passed=False,
            details={"reason": "charset", "kind": "rf"},
        )
    remainder = _mod97(compact)
    if remainder < 0:
        return RuleResult(
            rule=RULE,
            field=FIELD,
            passed=False,
            details={"reason": "charset", "kind": "rf"},
        )
    if remainder != 1:
        return RuleResult(
            rule=RULE,
            field=FIELD,
            passed=False,
            details={"reason": "checksum", "kind": "rf", "remainder": remainder},
        )
    return RuleResult(
        rule=RULE,
        field=FIELD,
        passed=True,
        details={"kind": "rf", "length": len(compact)},
    )


def reference_number(value: str | None) -> RuleResult:
    raw = (value or "").strip()
    if not raw:
        return RuleResult(rule=RULE, field=FIELD, passed=False, details={"reason": "empty"})
    compact = _compact(raw)
    if compact.startswith("RF"):
        return _rf_reference(compact)
    return _finnish_reference(compact)
