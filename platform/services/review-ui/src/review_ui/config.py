from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    review_ui_user: str = "reviewer"
    review_ui_password: str = "change-me"
    review_hmac_secret: str = "change-me"
    review_receiver_url: str = "http://n8n-main:5678/webhook/plt/review-decision"
    review_ui_actor_id: str = "local-reviewer"
    database_url: str = ""

    def validate_local_auth(self) -> None:
        if not self.review_ui_user:
            raise RuntimeError("REVIEW_UI_USER is empty")
        if not self.review_ui_password:
            raise RuntimeError("REVIEW_UI_PASSWORD is empty")
        if not self.review_hmac_secret:
            raise RuntimeError("REVIEW_HMAC_SECRET is empty")
        if not self.review_receiver_url:
            raise RuntimeError("REVIEW_RECEIVER_URL is empty")


def load_settings() -> Settings:
    settings = Settings()
    settings.validate_local_auth()
    return settings
