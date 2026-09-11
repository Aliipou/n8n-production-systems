"""Environment config. Fail fast if the internal token is missing."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    internal_api_token: str = Field(default="")
    p01_scoring_config: str = ""
    mx_check: bool = False

    @field_validator("internal_api_token")
    @classmethod
    def token_not_blank(cls, value: str) -> str:
        token = value.strip()
        if not token:
            raise ValueError("INTERNAL_API_TOKEN is missing or empty")
        return token

    def scoring_path(self) -> Path:
        raw = self.p01_scoring_config.strip()
        if raw:
            return Path(raw)
        return Path(__file__).resolve().parents[2] / "config" / "scoring.yaml"
