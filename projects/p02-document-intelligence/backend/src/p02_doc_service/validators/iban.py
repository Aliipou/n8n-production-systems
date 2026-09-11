"""ISO 13616 IBAN checksum. FI IBANs must be 18 characters."""

from __future__ import annotations

from p02_doc_service.validators.result import RuleResult

RULE = "iban_checksum"
FIELD = "iban"
FI_LENGTH = 18


def _compact(value: str) -> str:
    return "".join(value.split()).upper()


def _mod97(iban: str) -> int:
    rearranged = iban[4:] + iban[:4]
    digits: list[str] = []
    for char in rearranged:
        if char.isdigit():
            digits.append(char)
        elif "A" <= char <= "Z":
            digits.append(str(ord(char) - 55))
        else:
            return -1
    return int("".join(digits)) % 97


def iban_checksum(value: str | None) -> RuleResult:
    raw = (value or "").strip()
    if not raw:
        return RuleResult(rule=RULE, field=FIELD, passed=False, details={"reason": "empty"})
    compact = _compact(raw)
    if len(compact) < 15 or len(compact) > 34:
        return RuleResult(
            rule=RULE,
            field=FIELD,
            passed=False,
            details={"reason": "length", "length": len(compact)},
        )
    if not compact[:2].isalpha() or not compact[2:4].isdigit():
        return RuleResult(
            rule=RULE,
            field=FIELD,
            passed=False,
            details={"reason": "format"},
        )
    if compact.startswith("FI") and len(compact) != FI_LENGTH:
        return RuleResult(
            rule=RULE,
            field=FIELD,
            passed=False,
            details={"reason": "fi_length", "length": len(compact), "expected": FI_LENGTH},
        )
    remainder = _mod97(compact)
    if remainder < 0:
        return RuleResult(rule=RULE, field=FIELD, passed=False, details={"reason": "charset"})
    if remainder != 1:
        return RuleResult(
            rule=RULE,
            field=FIELD,
            passed=False,
            details={"reason": "checksum", "remainder": remainder},
        )
    return RuleResult(
        rule=RULE,
        field=FIELD,
        passed=True,
        details={"country": compact[:2], "length": len(compact)},
    )
