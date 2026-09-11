from __future__ import annotations

from fastapi import HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from review_ui.config import Settings
from review_ui.signing import constant_time_equals

basic_scheme = HTTPBasic(realm="review-ui")


def require_basic(
    credentials: HTTPBasicCredentials,
    settings: Settings,
) -> str:
    user_ok = constant_time_equals(credentials.username, settings.review_ui_user)
    password_ok = constant_time_equals(
        credentials.password, settings.review_ui_password
    )
    if not user_ok or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
            headers={"WWW-Authenticate": 'Basic realm="review-ui"'},
        )
    return settings.review_ui_actor_id
