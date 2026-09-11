"""VAT arithmetic table tests. Rates here are math fixtures, not vero.fi rates."""

from __future__ import annotations

from decimal import Decimal

import pytest

from p02_doc_service.config import VatRateEntry, VatRatesConfig
from p02_doc_service.validators.vat import VatLine, vat_math, vat_rates

TOL = Decimal("0.01")


def _line(rate: str, base: str, vat: str) -> VatLine:
    return VatLine(rate=Decimal(rate), base=Decimal(base), vat=Decimal(vat))


MATH_CASES: list[tuple[str, str, str, str, list[VatLine], bool, str]] = [
    ("net_plus_vat", "100.00", "10.00", "110.00", [_line("10", "100.00", "10.00")], True, "ok"),
    ("zero_vat", "50.00", "0.00", "50.00", [_line("0", "50.00", "0.00")], True, "ok"),
    (
        "two_lines",
        "200.00",
        "30.00",
        "230.00",
        [_line("10", "100.00", "10.00"), _line("20", "100.00", "20.00")],
        True,
        "ok",
    ),
    ("empty_breakdown_totals_ok", "10.00", "1.00", "11.00", [], True, "ok"),
    ("tolerance_hit", "10.00", "1.00", "11.01", [_line("10", "10.00", "1.00")], True, "ok"),
    (
        "gross_too_high",
        "100.00",
        "10.00",
        "111.00",
        [_line("10", "100.00", "10.00")],
        False,
        "net_plus_vat",
    ),
    (
        "gross_too_low",
        "100.00",
        "10.00",
        "109.00",
        [_line("10", "100.00", "10.00")],
        False,
        "net_plus_vat",
    ),
    (
        "line_vat_wrong",
        "100.00",
        "10.00",
        "110.00",
        [_line("10", "100.00", "9.00")],
        False,
        "line_vat",
    ),
    (
        "vat_sum_wrong",
        "200.00",
        "30.00",
        "230.00",
        [_line("10", "100.00", "10.00"), _line("10", "100.00", "10.00")],
        False,
        "vat_sum",
    ),
    ("negative_net", "-1.00", "0.00", "-1.00", [], False, "negative"),
    ("missing_gross", "10.00", "1.00", "", [], False, "missing_totals"),
    ("over_tolerance", "10.00", "1.00", "11.02", [], False, "net_plus_vat"),
    (
        "fractional_cents_within",
        "33.33",
        "3.33",
        "36.66",
        [_line("10", "33.33", "3.33")],
        True,
        "ok",
    ),
]


@pytest.mark.parametrize(
    ("case_id", "net", "vat", "gross", "lines", "passed", "reason"),
    MATH_CASES,
    ids=[item[0] for item in MATH_CASES],
)
def test_vat_math_table(
    case_id: str,
    net: str,
    vat: str,
    gross: str,
    lines: list[VatLine],
    passed: bool,
    reason: str,
) -> None:
    net_v: Decimal | None = Decimal(net) if net else None
    vat_v: Decimal | None = Decimal(vat) if vat else None
    gross_v: Decimal | None = Decimal(gross) if gross else None
    if case_id == "missing_gross":
        gross_v = None
    result = vat_math(net_v, vat_v, gross_v, lines, tolerance=TOL, rate_unit="percent")
    assert result.passed is passed, case_id
    assert result.rule == "vat_math"
    if passed:
        return
    assert result.details["reason"] == reason, case_id


def _fixture_rates() -> VatRatesConfig:
    # Test double only. Not Finnish legal rates. See vat_rates.yaml TODO(verify).
    return VatRatesConfig(
        version=1,
        rate_unit="percent",
        rates=(
            VatRateEntry(rate=Decimal("10"), valid_from="2000-01-01", label="fixture_only"),
            VatRateEntry(rate=Decimal("0"), valid_from="2000-01-01", label="fixture_zero"),
        ),
    )


def test_vat_rates_fail_closed_when_yaml_unverified() -> None:
    empty = VatRatesConfig(version=1, rate_unit="percent", rates=())
    result = vat_rates([_line("10", "100", "10")], empty)
    assert result.passed is False
    assert result.details["reason"] == "unverified_config"


def test_vat_rates_accepts_fixture_rate() -> None:
    result = vat_rates([_line("10", "100", "10")], _fixture_rates(), invoice_date="2020-01-01")
    assert result.passed is True


def test_vat_rates_rejects_unknown_fixture_rate() -> None:
    result = vat_rates([_line("99", "100", "99")], _fixture_rates(), invoice_date="2020-01-01")
    assert result.passed is False
    assert result.details["reason"] == "unknown_rate"


def test_vat_rates_empty_breakdown_fails_when_verified() -> None:
    result = vat_rates([], _fixture_rates(), invoice_date="2020-01-01")
    assert result.passed is False
    assert result.details["reason"] == "empty_breakdown"
