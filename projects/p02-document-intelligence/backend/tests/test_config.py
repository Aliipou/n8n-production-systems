"""Config loaders. VAT rates stay empty until vero.fi is copied in."""

from __future__ import annotations

from pathlib import Path

from p02_doc_service.config import default_config_dir, load_decision, load_vat_rates

CONFIG = Path(__file__).resolve().parents[1] / "config"


def test_vat_rates_yaml_is_unverified_placeholder() -> None:
    loaded = load_vat_rates(CONFIG / "vat_rates.yaml")
    assert loaded.version == 1
    assert loaded.rates == ()
    assert loaded.verified is False
    text = (CONFIG / "vat_rates.yaml").read_text(encoding="utf-8")
    assert "TODO(verify)" in text
    assert "vero.fi" in text


def test_decision_yaml_matches_spec_defaults() -> None:
    loaded = load_decision(CONFIG / "decision.yaml")
    assert loaded.version == 1
    assert loaded.min_confidence == 0.90
    assert str(loaded.max_gross_eur) == "5000"
    assert loaded.allowed_currencies == ("EUR",)
    assert loaded.iban_mismatch_always_review is True
    assert loaded.foreign_currency_never_auto_approve is True
    assert "iban" in loaded.critical_fields


def test_default_config_dir_points_at_backend_config() -> None:
    assert default_config_dir() == CONFIG
