from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from starlette.responses import Response

from review_ui.auth import basic_scheme, require_basic
from review_ui.config import Settings, load_settings
from review_ui.db import (
    DatabaseUnavailable,
    apply_decision,
    get_item,
    iter_kinds,
    list_pending,
)
from review_ui.decisions import decision_body
from review_ui.receiver import ReceiverError, post_decision

LOGGER = logging.getLogger("review_ui")


def _settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        raise RuntimeError("review-ui settings are not configured")
    return settings


def _actor(
    request: Request,
    credentials: Annotated[HTTPBasicCredentials, Depends(basic_scheme)],
) -> str:
    return require_basic(credentials, _settings(request))


def templates_dir() -> Path:
    package_dir = Path(__file__).resolve().parent
    candidates = (
        Path("/app/templates"),
        package_dir.parent.parent / "templates",
        package_dir / "templates",
    )
    for path in candidates:
        if (path / "base.html").is_file():
            return path
    return candidates[1]


def _pretty_json(value: Any) -> str:
    return json.dumps(value, indent=2, default=str, sort_keys=True)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or load_settings()
    templates = Jinja2Templates(directory=str(templates_dir()))
    app = FastAPI(title="review-ui", docs_url=None, redoc_url=None)
    app.state.settings = resolved

    def health() -> JSONResponse:
        return JSONResponse({"status": "ok", "service": "review-ui"})

    # Compose and the image HEALTHCHECK probe /health (no auth).
    app.add_api_route("/health", health, methods=["GET"], include_in_schema=False)
    app.add_api_route("/healthz", health, methods=["GET"], include_in_schema=False)

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/reviews", status_code=302)

    @app.get("/reviews", response_class=HTMLResponse)
    def reviews_list(
        request: Request,
        _actor: str = Depends(_actor),
    ) -> Response:
        error: str | None = None
        items: list[dict[str, Any]] = []
        try:
            items = list_pending(resolved.database_url)
        except DatabaseUnavailable as exc:
            error = str(exc)
            LOGGER.error(
                json.dumps(
                    {"event": "review_list_failed", "error_class": type(exc).__name__}
                )
            )
        groups = list(iter_kinds(items)) if not error else []
        return templates.TemplateResponse(
            request,
            "list.html",
            {
                "error": error,
                "groups": groups,
                "notice": request.query_params.get("notice"),
            },
        )

    @app.get("/reviews/{review_id}", response_class=HTMLResponse)
    def reviews_detail(
        request: Request,
        review_id: UUID,
        _actor: str = Depends(_actor),
    ) -> Response:
        error: str | None = None
        item: dict[str, Any] | None = None
        try:
            item = get_item(resolved.database_url, review_id)
        except DatabaseUnavailable as exc:
            error = str(exc)
            LOGGER.error(
                json.dumps({"event": "review_detail_failed", "id": str(review_id)})
            )
        if error is None and item is None:
            return templates.TemplateResponse(
                request,
                "detail.html",
                {
                    "error": "Review item not found.",
                    "item": None,
                    "payload_json": "",
                    "notice": request.query_params.get("notice"),
                    "pending": False,
                },
                status_code=404,
            )
        payload_json = _pretty_json(item.get("payload")) if item else ""
        pending = bool(item and item.get("status") == "pending")
        return templates.TemplateResponse(
            request,
            "detail.html",
            {
                "error": error,
                "item": item,
                "payload_json": payload_json,
                "notice": request.query_params.get("notice"),
                "pending": pending,
            },
        )

    def _decide(
        review_id: UUID,
        status: str,
        actor: str,
        reason: str,
    ) -> RedirectResponse:
        reason_value = reason.strip() or None
        try:
            claimed = apply_decision(
                resolved.database_url,
                review_id=review_id,
                status=status,
                decided_by=actor,
                reason=reason_value,
            )
        except DatabaseUnavailable as exc:
            LOGGER.error(
                json.dumps(
                    {
                        "event": "review_decide_failed",
                        "id": str(review_id),
                        "error_class": type(exc).__name__,
                    }
                )
            )
            return RedirectResponse(
                url=f"/reviews/{review_id}?notice=db_error",
                status_code=303,
            )
        if claimed is None:
            return RedirectResponse(
                url=f"/reviews/{review_id}?notice=already_decided",
                status_code=303,
            )
        body = decision_body(
            review_id=review_id,
            status=status,
            decided_by=actor,
            reason=reason_value,
            project=claimed.get("project"),
            kind=claimed.get("kind"),
            subject_id=claimed.get("subject_id"),
            callback_workflow_id=claimed.get("callback_workflow_id"),
        )
        try:
            post_decision(
                url=resolved.review_receiver_url,
                secret=resolved.review_hmac_secret,
                payload=body,
            )
        except ReceiverError:
            notice = (
                "approved_receiver_failed"
                if status == "approved"
                else "rejected_receiver_failed"
            )
            return RedirectResponse(
                url=f"/reviews/{review_id}?notice={notice}",
                status_code=303,
            )
        notice = "approved" if status == "approved" else "rejected"
        return RedirectResponse(
            url=f"/reviews/{review_id}?notice={notice}", status_code=303
        )

    @app.post("/reviews/{review_id}/approve")
    def reviews_approve(
        review_id: UUID,
        actor: str = Depends(_actor),
        reason: str = Form(""),
    ) -> RedirectResponse:
        return _decide(review_id, "approved", actor, reason)

    @app.post("/reviews/{review_id}/reject")
    def reviews_reject(
        review_id: UUID,
        actor: str = Depends(_actor),
        reason: str = Form(""),
    ) -> RedirectResponse:
        return _decide(review_id, "rejected", actor, reason)

    return app


app = create_app()
