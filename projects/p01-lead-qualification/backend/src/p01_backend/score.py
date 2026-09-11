"""Deterministic lead scoring. Pure function over scoring.yaml. LLM never picks the route."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

# Hard cap: the model may contribute at most 20 of 100 points (AGENTS.md section 6).
LLM_SCORE_CAP = 20
LADDER_ROUTES: tuple[str, ...] = ("archive", "nurture", "sales")

# LLM urgency_hint values do not match form timeline bands. Map before lookup.
URGENCY_HINT_TO_BAND: dict[str, str] = {
    "now": "now",
    "soon": "1-3 months",
    "later": "3-6 months",
    "unknown": "unknown",
}


class ScoreInput(BaseModel):
    """Fields the scorer reads. Extra keys such as `route` are ignored."""

    model_config = ConfigDict(extra="ignore")

    company_size: str | None = None
    industry: str | None = None
    budget_range: str | None = None
    timeline: str | None = None
    urgency_hint: str | None = None
    intent: str | None = None
    is_free_mail: bool = False
    llm_status: str | None = None


class ScoreResult(BaseModel):
    score: int
    breakdown: dict[str, int]
    route: str
    reasons: list[str]


@dataclass(frozen=True)
class ScoringConfig:
    version: int
    max_score: int
    components: dict[str, Any]
    routes: tuple[dict[str, Any], ...]
    overrides: tuple[dict[str, Any], ...]


def load_config(path: Path) -> ScoringConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        msg = f"scoring config must be a mapping: {path}"
        raise ValueError(msg)
    routes = raw.get("routes") or []
    overrides = raw.get("overrides") or []
    if not isinstance(routes, list) or not isinstance(overrides, list):
        raise ValueError("scoring config routes and overrides must be lists")
    return ScoringConfig(
        version=int(raw["version"]),
        max_score=int(raw["max_score"]),
        components=dict(raw["components"]),
        routes=tuple(routes),
        overrides=tuple(overrides),
    )


def score_lead(
    payload: ScoreInput | Mapping[str, Any],
    config: ScoringConfig,
) -> ScoreResult:
    """Return score, breakdown, route, and reasons. No I/O. Route is not taken from the payload."""
    inp = payload if isinstance(payload, ScoreInput) else ScoreInput.model_validate(payload)
    reasons: list[str] = []
    breakdown = {
        "company_size": _company_size_points(inp, config, reasons),
        "industry_fit": _industry_points(inp, config, reasons),
        "budget": _budget_points(inp, config, reasons),
        "urgency": _urgency_points(inp, config, reasons),
        "ai_qualification": _ai_points(inp, config, reasons),
    }
    total = min(sum(breakdown.values()), config.max_score)
    route = _route_from_score(total, config)
    forced_route = False

    for override in config.overrides:
        when = override.get("when") or {}
        if not isinstance(when, dict) or not _matches(when, inp):
            continue
        if "cap_score" in override:
            cap = int(override["cap_score"])
            if total > cap:
                reasons.append(f"override cap_score={cap} (was {total})")
                total = cap
            else:
                reasons.append(f"override cap_score={cap} (score already {total})")
            if not forced_route:
                route = _route_from_score(total, config)
        if "route" in override:
            route = str(override["route"])
            forced_route = True
            reasons.append(f"override route={route}")
        if "cap_route" in override:
            cap_route = str(override["cap_route"])
            capped = _cap_route(route, cap_route)
            if capped != route:
                reasons.append(f"override cap_route={cap_route} (was {route})")
                route = capped
            else:
                reasons.append(f"override cap_route={cap_route} (route stays {route})")

    reasons.append(f"route={route} score={total}")
    return ScoreResult(score=total, breakdown=breakdown, route=route, reasons=reasons)


def _matches(when: Mapping[str, Any], inp: ScoreInput) -> bool:
    for key, expected in when.items():
        actual = getattr(inp, key, None)
        if key == "is_free_mail":
            if bool(actual) != bool(expected):
                return False
            continue
        if actual != expected:
            return False
    return True


def _route_from_score(score: int, config: ScoringConfig) -> str:
    ordered = sorted(config.routes, key=lambda item: int(item["min"]), reverse=True)
    for item in ordered:
        if score >= int(item["min"]):
            return str(item["name"])
    return "archive"


def _cap_route(current: str, cap: str) -> str:
    if current not in LADDER_ROUTES or cap not in LADDER_ROUTES:
        return current
    if LADDER_ROUTES.index(current) > LADDER_ROUTES.index(cap):
        return cap
    return current


def _band_points(
    bands: Mapping[str, Any], key: str | None, unknown_key: str = "unknown"
) -> tuple[int, str]:
    lookup = {str(name): int(value) for name, value in bands.items()}
    if key is None or str(key).strip() == "":
        used = unknown_key
        return lookup.get(used, 0), used
    normalized = str(key).strip()
    if normalized in lookup:
        return lookup[normalized], normalized
    return lookup.get(unknown_key, 0), unknown_key


def _cap_component(name: str, points: int, component: Mapping[str, Any]) -> int:
    capped = min(points, int(component["max"]))
    if name == "ai_qualification":
        capped = min(capped, LLM_SCORE_CAP)
    return capped


def _company_size_points(inp: ScoreInput, config: ScoringConfig, reasons: list[str]) -> int:
    component = config.components["company_size"]
    points, used = _band_points(component["bands"], inp.company_size)
    points = _cap_component("company_size", points, component)
    reasons.append(f"company_size={used} -> {points}")
    return points


def _industry_points(inp: ScoreInput, config: ScoringConfig, reasons: list[str]) -> int:
    component = config.components["industry_fit"]
    industry = (inp.industry or "").strip().lower()
    fit = {str(item).lower() for item in component["fit"]}
    partial = {str(item).lower() for item in component["partial"]}
    if industry in fit:
        points = int(component["fit_points"])
        label = "fit"
    elif industry in partial:
        points = int(component["partial_points"])
        label = "partial"
    else:
        points = int(component["other_points"])
        label = "other"
        industry = industry or "unknown"
    points = _cap_component("industry_fit", points, component)
    reasons.append(f"industry={industry} ({label}) -> {points}")
    return points


def _budget_points(inp: ScoreInput, config: ScoringConfig, reasons: list[str]) -> int:
    component = config.components["budget"]
    field = str(component.get("form_field", "budget_range"))
    raw = getattr(inp, field, None)
    points, used = _band_points(component["bands"], raw if isinstance(raw, str) else None)
    points = _cap_component("budget", points, component)
    reasons.append(f"budget={used} -> {points}")
    return points


def _urgency_points(inp: ScoreInput, config: ScoringConfig, reasons: list[str]) -> int:
    component = config.components["urgency"]
    field = str(component.get("form_field", "timeline"))
    raw = getattr(inp, field, None)
    timeline = raw.strip() if isinstance(raw, str) and raw.strip() else None
    if timeline is None or timeline == "unknown":
        hint = (inp.urgency_hint or "").strip()
        fallback_field = str(component.get("llm_fallback_field", "urgency_hint"))
        if hint:
            timeline = URGENCY_HINT_TO_BAND.get(hint, "unknown")
            reasons.append(f"urgency used {fallback_field}={hint} as {timeline}")
    points, used = _band_points(component["bands"], timeline)
    points = _cap_component("urgency", points, component)
    reasons.append(f"urgency={used} -> {points}")
    return points


def _ai_points(inp: ScoreInput, config: ScoringConfig, reasons: list[str]) -> int:
    component = config.components["ai_qualification"]
    if inp.llm_status == "failed":
        reasons.append("llm_status=failed -> ai_qualification=0")
        return 0
    intent_points = {str(k): int(v) for k, v in component["intent_points"].items()}
    intent = (inp.intent or "").strip()
    if not intent:
        reasons.append("ai_qualification missing intent -> 0")
        return 0
    raw = intent_points.get(intent, 0)
    points = _cap_component("ai_qualification", raw, component)
    reasons.append(f"intent={intent} -> {points} (LLM cap {LLM_SCORE_CAP})")
    return points
