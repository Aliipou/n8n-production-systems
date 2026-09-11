"""VAT arithmetic. Rates on the invoice are inputs; Finnish legal rates live in yaml."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from p02_doc_service.config import VatRatesConfig
from p02_doc_service.validators.dates import parse_date
from p02_doc_service.validators.result import RuleResult

RULE_MATH = "vat_math"
RULE_RATES = "vat_rates"
FIELD_GROSS = "gross_total"
FIELD_RATES = "vat_breakdown"

ZERO = Decimal("0")
DEFAULT_TOLERANCE = Decimal("0.01")


@dataclass(frozen=True)
class VatLine:
    rate: Decimal
    base: Decimal
    vat: Decimal


def _as_decimal(value: Decimal | int | str) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _within(actual: Decimal, expected: Decimal, tolerance: Decimal) -> bool:
    return abs(actual - expected) <= tolerance


def _line_vat(line: VatLine, *, rate_unit: str) -> Decimal:
    if rate_unit == "fraction":
        return line.base * line.rate
    return line.base * line.rate / Decimal("100")


def vat_math(
    net_total: Decimal | int | str | None,
    vat_total: Decimal | int | str | None,
    gross_total: Decimal | int | str | None,
    vat_breakdown: Sequence[VatLine] | None = None,
    *,
    tolerance: Decimal = DEFAULT_TOLERANCE,
    rate_unit: str = "percent",
) -> RuleResult:
    if net_total is None or vat_total is None or gross_total is None:
        return RuleResult(
            rule=RULE_MATH,
            field=FIELD_GROSS,
            passed=False,
            details={"reason": "missing_totals"},
        )
    net = _as_decimal(net_total)
    vat = _as_decimal(vat_total)
    gross = _as_decimal(gross_total)
    if net < ZERO or vat < ZERO or gross < ZERO:
        return RuleResult(
            rule=RULE_MATH,
            field=FIELD_GROSS,
            passed=False,
            details={"reason": "negative", "net": str(net), "vat": str(vat), "gross": str(gross)},
        )
    expected_gross = net + vat
    if not _within(gross, expected_gross, tolerance):
        return RuleResult(
            rule=RULE_MATH,
            field=FIELD_GROSS,
            passed=False,
            details={
                "reason": "net_plus_vat",
                "net": str(net),
                "vat": str(vat),
                "gross": str(gross),
                "expected_gross": str(expected_gross),
                "tolerance": str(tolerance),
            },
        )
    lines = tuple(vat_breakdown or ())
    mismatches: list[dict[str, str | int]] = []
    vat_sum = ZERO
    for index, line in enumerate(lines):
        expected_line_vat = _line_vat(line, rate_unit=rate_unit)
        vat_sum += line.vat
        if not _within(line.vat, expected_line_vat, tolerance):
            mismatches.append(
                {
                    "index": index,
                    "rate": str(line.rate),
                    "base": str(line.base),
                    "vat": str(line.vat),
                    "expected_vat": str(expected_line_vat),
                }
            )
    if mismatches:
        return RuleResult(
            rule=RULE_MATH,
            field=FIELD_GROSS,
            passed=False,
            details={"reason": "line_vat", "mismatches": mismatches},
        )
    if lines and not _within(vat_sum, vat, tolerance):
        return RuleResult(
            rule=RULE_MATH,
            field=FIELD_GROSS,
            passed=False,
            details={
                "reason": "vat_sum",
                "vat_total": str(vat),
                "sum_of_lines": str(vat_sum),
                "tolerance": str(tolerance),
            },
        )
    return RuleResult(
        rule=RULE_MATH,
        field=FIELD_GROSS,
        passed=True,
        details={"net": str(net), "vat": str(vat), "gross": str(gross), "lines": len(lines)},
    )


def vat_rates(
    vat_breakdown: Sequence[VatLine] | None,
    config: VatRatesConfig,
    *,
    invoice_date: str | None = None,
) -> RuleResult:
    """Fail closed when vero.fi rates have not been filled in vat_rates.yaml."""
    lines = tuple(vat_breakdown or ())
    if not config.verified:
        return RuleResult(
            rule=RULE_RATES,
            field=FIELD_RATES,
            passed=False,
            details={
                "reason": "unverified_config",
                "todo": "TODO(verify): copy official rates from vero.fi into config/vat_rates.yaml",
            },
        )
    parsed_invoice = parse_date(invoice_date) if invoice_date else None
    allowed = {entry.rate for entry in config.rates}
    if parsed_invoice is not None:
        allowed = set()
        for entry in config.rates:
            started = parse_date(entry.valid_from)
            if started is not None and started <= parsed_invoice:
                allowed.add(entry.rate)
        if not allowed:
            return RuleResult(
                rule=RULE_RATES,
                field=FIELD_RATES,
                passed=False,
                details={"reason": "no_rate_in_force", "invoice_date": parsed_invoice.isoformat()},
            )
    unknown: list[str] = []
    for line in lines:
        if line.rate not in allowed:
            unknown.append(str(line.rate))
    if unknown:
        return RuleResult(
            rule=RULE_RATES,
            field=FIELD_RATES,
            passed=False,
            details={"reason": "unknown_rate", "rates": unknown},
        )
    if not lines:
        return RuleResult(
            rule=RULE_RATES,
            field=FIELD_RATES,
            passed=False,
            details={"reason": "empty_breakdown"},
        )
    return RuleResult(
        rule=RULE_RATES,
        field=FIELD_RATES,
        passed=True,
        details={"accepted": [str(line.rate) for line in lines]},
    )
