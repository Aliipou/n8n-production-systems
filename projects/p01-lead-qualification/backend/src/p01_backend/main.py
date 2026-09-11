"""HTTP API: health plus authenticated normalize and score endpoints."""

from __future__ import annotations

import hmac
import json
import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from pydantic import ValidationError

from p01_backend.config import Settings
from p01_backend.normalize import NormalizeInput, NormalizeResult, normalize_lead
from p01_backend.score import ScoreInput, ScoreResult, ScoringConfig, load_config, score_lead

log = logging.getLogger("p01_backend")


def _configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
        }
        return json.dumps(payload, ensure_ascii=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    _configure_logging()
    try:
        settings = Settings()
    except ValidationError as exc:
        raise RuntimeError("INTERNAL_API_TOKEN is missing or empty") from exc
    config_path = settings.scoring_path()
    if not config_path.is_file():
        raise RuntimeError(f"scoring config not found: {config_path}")
    app.state.internal_api_token = settings.internal_api_token
    app.state.scoring_config = load_config(config_path)
    app.state.mx_check = settings.mx_check
    log.info("p01-backend started")
    yield


app = FastAPI(title="p01-backend", lifespan=lifespan)


def require_internal_token(
    request: Request,
    internal_api_token: Annotated[
        str | None,
        Header(alias="INTERNAL_API_TOKEN", convert_underscores=False),
    ] = None,
) -> None:
    expected: str = request.app.state.internal_api_token
    provided = internal_api_token or ""
    if not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/leads/normalize")
def post_normalize(
    body: NormalizeInput,
    request: Request,
    _: None = Depends(require_internal_token),
) -> NormalizeResult:
    mx_check = bool(request.app.state.mx_check)
    return normalize_lead(body, mx_check=mx_check)


@app.post("/v1/score")
def post_score(
    body: ScoreInput,
    request: Request,
    _: None = Depends(require_internal_token),
) -> ScoreResult:
    config: ScoringConfig = request.app.state.scoring_config
    return score_lead(body, config)


def main() -> None:
    import uvicorn

    uvicorn.run(
        "p01_backend.main:app",
        host="0.0.0.0",
        port=8000,
        factory=False,
    )


if __name__ == "__main__":
    main()
