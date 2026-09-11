"""Table-driven scoring tests against backend/config/scoring.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from p01_backend.score import LLM_SCORE_CAP, ScoreInput, ScoringConfig, load_config, score_lead

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "scoring.yaml"


@pytest.fixture(scope="module")
def config() -> ScoringConfig:
    return load_config(CONFIG_PATH)


def _base(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "company_size": "51-200",
        "industry": "saas",
        "budget_range": "50k+",
        "timeline": "now",
        "intent": "demo_request",
        "is_free_mail": False,
        "llm_status": "ok",
    }
    payload.update(overrides)
    return payload


def test_config_is_spec_defaults(config: ScoringConfig) -> None:
    assert config.version == 1
    assert config.max_score == 100
    assert int(config.components["ai_qualification"]["max"]) == LLM_SCORE_CAP
    assert [item["name"] for item in config.routes] == ["sales", "nurture", "archive"]
    when_keys = [tuple(sorted((item.get("when") or {}).items())) for item in config.overrides]
    assert ("intent", "spam") in when_keys[0]
    assert any("cap_score" in item for item in config.overrides)
    assert any("cap_route" in item for item in config.overrides)


def test_llm_cannot_pick_route(config: ScoringConfig) -> None:
    result = score_lead(
        {**_base(intent="spam"), "route": "sales", "suggested_route": "sales"}, config
    )
    assert result.route == "archive"
    assert result.breakdown["ai_qualification"] <= LLM_SCORE_CAP


def test_llm_points_hard_capped_at_20_if_config_raises_max(config: ScoringConfig) -> None:
    bumped = ScoringConfig(
        version=config.version,
        max_score=config.max_score,
        components={
            **config.components,
            "ai_qualification": {
                **config.components["ai_qualification"],
                "max": 40,
                "intent_points": {
                    **config.components["ai_qualification"]["intent_points"],
                    "demo_request": 40,
                },
            },
        },
        routes=config.routes,
        overrides=config.overrides,
    )
    result = score_lead(
        {
            "company_size": "unknown",
            "industry": "other",
            "budget_range": "unknown",
            "timeline": "unknown",
            "intent": "demo_request",
        },
        bumped,
    )
    assert result.breakdown["ai_qualification"] == LLM_SCORE_CAP


# Expected scores are the arithmetic of scoring.yaml (max 100, AI cap 20).
CASES: list[tuple[str, dict[str, Any], str, int]] = [
    ("sales_max", _base(), "sales", 100),
    ("pricing_intent", _base(intent="pricing"), "sales", 96),
    ("partnership", _base(intent="partnership"), "sales", 88),
    ("other_intent", _base(intent="other"), "sales", 84),
    ("support_override", _base(intent="support"), "support_forward", 80),
    ("job_override", _base(intent="job_application"), "hr_forward", 80),
    ("spam_override", _base(intent="spam"), "archive", 80),
    ("free_mail_cap", _base(is_free_mail=True), "nurture", 60),
    ("llm_failed_caps_route", _base(llm_status="failed"), "nurture", 80),
    ("unknown_size", _base(company_size=None), "sales", 80),
    ("size_1_10", _base(company_size="1-10"), "sales", 80),
    ("size_11_50", _base(company_size="11-50"), "sales", 90),
    ("size_201_1000", _base(company_size="201-1000"), "sales", 95),
    ("size_1000_plus", _base(company_size="1000+"), "sales", 85),
    ("industry_partial_retail", _base(industry="retail"), "sales", 90),
    ("industry_other", _base(industry="agriculture"), "sales", 80),
    ("budget_low", _base(budget_range="<5k"), "sales", 80),
    ("budget_mid", _base(budget_range="5k-20k"), "sales", 90),
    ("budget_unknown", _base(budget_range=None), "sales", 85),
    ("timeline_exploring", _base(timeline="exploring"), "sales", 87),
    ("timeline_3_6", _base(timeline="3-6 months"), "sales", 90),
    ("urgency_hint_now", _base(timeline=None, urgency_hint="now"), "sales", 100),
    ("software_fit", _base(industry="software"), "sales", 100),
    ("manufacturing_fit", _base(industry="manufacturing"), "sales", 100),
    ("logistics_fit", _base(industry="logistics"), "sales", 100),
    ("public_sector_partial", _base(industry="public_sector"), "sales", 90),
    ("budget_20_50", _base(budget_range="20k-50k"), "sales", 96),
    (
        "sales_80_exact",
        _base(industry="software", budget_range="20k-50k", intent="other"),
        "sales",
        80,
    ),
    ("free_mail_and_spam", _base(is_free_mail=True, intent="spam"), "archive", 60),
    ("job_plus_free_mail", _base(is_free_mail=True, intent="job_application"), "hr_forward", 60),
    ("support_plus_free_mail", _base(is_free_mail=True, intent="support"), "support_forward", 60),
    ("llm_failed_plus_free_mail", _base(is_free_mail=True, llm_status="failed"), "nurture", 60),
    ("llm_failed_plus_spam", _base(intent="spam", llm_status="failed"), "archive", 80),
    ("free_mail_already_below_cap", {"is_free_mail": True}, "archive", 13),
    (
        "low_combo_archive",
        _base(
            company_size="1-10",
            industry="agriculture",
            budget_range="<5k",
            timeline="exploring",
            intent="other",
        ),
        "archive",
        11,
    ),
    (
        "nurture_threshold_50",
        _base(
            company_size="1-10",
            industry="software",
            budget_range="20k-50k",
            timeline="3-6 months",
            intent="other",
        ),
        "nurture",
        50,
    ),
    (
        "archive_threshold_49",
        _base(
            company_size="1-10",
            industry="software",
            budget_range="5k-20k",
            timeline="1-3 months",
            intent="other",
        ),
        "archive",
        49,
    ),
    (
        "nurture_79",
        _base(
            company_size="51-200",
            industry="software",
            budget_range="20k-50k",
            timeline="1-3 months",
            intent="partnership",
        ),
        "nurture",
        79,
    ),
    ("all_unknown_archive", {}, "archive", 13),
    ("llm_failed_low_stays_archive", {"llm_status": "failed"}, "archive", 13),
    ("timeline_1_3", _base(timeline="1-3 months"), "sales", 95),
    ("urgency_hint_soon", _base(timeline="unknown", urgency_hint="soon"), "sales", 95),
    ("intent_pricing_unknown_rest", {"intent": "pricing"}, "archive", 29),
]


def test_at_least_30_table_cases() -> None:
    assert len(CASES) >= 30


@pytest.mark.parametrize(
    ("case_id", "payload", "expected_route", "expected_score"),
    CASES,
    ids=[item[0] for item in CASES],
)
def test_score_table(
    config: ScoringConfig,
    case_id: str,
    payload: dict[str, Any],
    expected_route: str,
    expected_score: int,
) -> None:
    result = score_lead(payload, config)
    assert result.score == expected_score, case_id
    assert result.route == expected_route, case_id
    assert result.breakdown["ai_qualification"] <= LLM_SCORE_CAP
    assert result.score <= 100
    assert "route=" in result.reasons[-1]


def test_ai_breakdown_zero_on_llm_failure(config: ScoringConfig) -> None:
    result = score_lead(
        ScoreInput(
            company_size="51-200",
            industry="software",
            budget_range="50k+",
            timeline="now",
            intent="demo_request",
            llm_status="failed",
        ),
        config,
    )
    assert result.breakdown["ai_qualification"] == 0
    assert result.breakdown["company_size"] == 25
    assert result.route == "nurture"


def test_component_band_values(config: ScoringConfig) -> None:
    size = score_lead({"company_size": "51-200"}, config)
    assert size.breakdown["company_size"] == 25
    budget = score_lead({"budget_range": "20k-50k"}, config)
    assert budget.breakdown["budget"] == 16
    urgency = score_lead({"timeline": "3-6 months"}, config)
    assert urgency.breakdown["urgency"] == 5
