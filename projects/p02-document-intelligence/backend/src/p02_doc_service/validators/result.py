"""Shared validation result type."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RuleResult(BaseModel):
    rule: str
    field: str
    passed: bool
    details: dict[str, Any] = Field(default_factory=dict)
