"""Typed loaders for vat_rates.yaml and decision.yaml."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml


def default_config_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "config"


@dataclass(frozen=True)
class VatRateEntry:
    rate: Decimal
    valid_from: str
    label: str


@dataclass(frozen=True)
class VatRatesConfig:
    version: int
    rate_unit: str
    rates: tuple[VatRateEntry, ...]

    @property
    def verified(self) -> bool:
        return len(self.rates) > 0


@dataclass(frozen=True)
class DecisionConfig:
    version: int
    money_tolerance: Decimal
    min_confidence: float
    max_gross_eur: Decimal
    allowed_currencies: tuple[str, ...]
    require_all_validators_pass: bool
    require_supplier_known: bool
    require_iban_match: bool
    require_no_duplicate: bool
    require_critical_fields: bool
    critical_fields: tuple[str, ...]
    iban_mismatch_always_review: bool
    unknown_supplier_always_review: bool
    foreign_currency_never_auto_approve: bool


def _require_mapping(raw: Any, path: Path) -> dict[str, Any]:
    if not isinstance(raw, dict):
        msg = f"config must be a mapping: {path}"
        raise ValueError(msg)
    return raw


def load_vat_rates(path: Path) -> VatRatesConfig:
    raw = _require_mapping(yaml.safe_load(path.read_text(encoding="utf-8")), path)
    unit = str(raw.get("rate_unit") or "percent")
    if unit not in {"percent", "fraction"}:
        msg = f"rate_unit must be percent or fraction: {path}"
        raise ValueError(msg)
    entries: list[VatRateEntry] = []
    rates = raw.get("rates") or []
    if not isinstance(rates, list):
        raise ValueError(f"rates must be a list: {path}")
    for item in rates:
        if not isinstance(item, dict):
            raise ValueError(f"each rate must be a mapping: {path}")
        rate_raw = item.get("rate")
        valid_from = item.get("valid_from")
        label = item.get("label")
        if rate_raw is None or valid_from is None or label is None:
            # Incomplete placeholder rows are ignored. Fail closed via empty list.
            continue
        entries.append(
            VatRateEntry(
                rate=Decimal(str(rate_raw)),
                valid_from=str(valid_from),
                label=str(label),
            )
        )
    return VatRatesConfig(
        version=int(raw["version"]),
        rate_unit=unit,
        rates=tuple(entries),
    )


def load_decision(path: Path) -> DecisionConfig:
    raw = _require_mapping(yaml.safe_load(path.read_text(encoding="utf-8")), path)
    auto = raw.get("auto_approve") or {}
    tolerances = raw.get("tolerances") or {}
    rules = raw.get("rules") or {}
    fields = raw.get("critical_fields") or []
    if not isinstance(auto, dict) or not isinstance(tolerances, dict):
        raise ValueError(f"auto_approve and tolerances must be mappings: {path}")
    if not isinstance(rules, dict) or not isinstance(fields, list):
        raise ValueError(f"rules must be a mapping and critical_fields a list: {path}")
    currencies = auto.get("allowed_currencies") or []
    if not isinstance(currencies, list):
        raise ValueError(f"allowed_currencies must be a list: {path}")
    return DecisionConfig(
        version=int(raw["version"]),
        money_tolerance=Decimal(str(tolerances.get("money", "0.01"))),
        min_confidence=float(auto["min_confidence"]),
        max_gross_eur=Decimal(str(auto["max_gross_eur"])),
        allowed_currencies=tuple(str(c) for c in currencies),
        require_all_validators_pass=bool(auto.get("require_all_validators_pass", True)),
        require_supplier_known=bool(auto.get("require_supplier_known", True)),
        require_iban_match=bool(auto.get("require_iban_match", True)),
        require_no_duplicate=bool(auto.get("require_no_duplicate", True)),
        require_critical_fields=bool(auto.get("require_critical_fields", True)),
        critical_fields=tuple(str(f) for f in fields),
        iban_mismatch_always_review=bool(rules.get("iban_mismatch_always_review", True)),
        unknown_supplier_always_review=bool(rules.get("unknown_supplier_always_review", True)),
        foreign_currency_never_auto_approve=bool(
            rules.get("foreign_currency_never_auto_approve", True)
        ),
    )
