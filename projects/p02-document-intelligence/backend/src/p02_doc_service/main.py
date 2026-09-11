"""HTTP API: health, document upload, validator endpoint."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from p02_doc_service.config import (
    DecisionConfig,
    VatRatesConfig,
    default_config_dir,
    load_decision,
    load_vat_rates,
)
from p02_doc_service.documents import DocumentRepository, NewDocument, PostgresDocuments
from p02_doc_service.intake import HttpIntake, IntakeNotifier, NullIntake
from p02_doc_service.magic import detect_mime, filename_matches_mime
from p02_doc_service.storage import FilesystemStorage, Storage
from p02_doc_service.validators import (
    RuleResult,
    VatLine,
    business_id_checksum,
    dates,
    iban_checksum,
    reference_number,
    vat_math,
    vat_rates,
)
from p02_doc_service.validators.dates import today_helsinki

log = logging.getLogger("p02_doc_service")

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
READ_CHUNK = 64 * 1024


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


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is missing or empty")
    return value


def _config_path(env_name: str, filename: str) -> Path:
    raw = os.environ.get(env_name, "").strip()
    if raw:
        return Path(raw)
    return default_config_dir() / filename


class VatLineIn(BaseModel):
    rate: Decimal
    base: Decimal
    vat: Decimal


class ValidateIn(BaseModel):
    supplier_business_id: str | None = None
    iban: str | None = None
    reference_number: str | None = None
    invoice_date: str | None = None
    due_date: str | None = None
    net_total: Decimal | None = None
    vat_total: Decimal | None = None
    gross_total: Decimal | None = None
    vat_breakdown: list[VatLineIn] = Field(default_factory=list)


class ValidateOut(BaseModel):
    results: list[RuleResult]


def create_app(
    *,
    internal_api_token: str | None = None,
    storage: Storage | None = None,
    documents: DocumentRepository | None = None,
    intake: IntakeNotifier | None = None,
    vat_config: VatRatesConfig | None = None,
    decision_config: DecisionConfig | None = None,
    load_env: bool = False,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        _configure_logging()
        token = internal_api_token
        if token is None:
            token = _required_env("INTERNAL_API_TOKEN")
        app.state.internal_api_token = token
        app.state.storage = storage
        app.state.documents = documents
        app.state.intake = intake if intake is not None else NullIntake()
        app.state.vat_config = vat_config
        app.state.decision_config = decision_config
        if load_env:
            if app.state.storage is None:
                storage_dir = Path(os.environ.get("P02_STORAGE_DIR", "/data/documents"))
                app.state.storage = FilesystemStorage(storage_dir)
            if app.state.documents is None:
                app.state.documents = PostgresDocuments(_required_env("DATABASE_URL"))
            webhook = os.environ.get("P02_INTAKE_WEBHOOK_URL", "").strip()
            if webhook and intake is None:
                app.state.intake = HttpIntake(webhook, token)
            if app.state.vat_config is None:
                vat_path = _config_path("P02_VAT_RATES", "vat_rates.yaml")
                app.state.vat_config = load_vat_rates(vat_path)
            if app.state.decision_config is None:
                app.state.decision_config = load_decision(
                    _config_path("P02_DECISION", "decision.yaml")
                )
        if app.state.storage is None or app.state.documents is None:
            raise RuntimeError("storage and documents repository must be configured")
        if app.state.vat_config is None:
            app.state.vat_config = load_vat_rates(default_config_dir() / "vat_rates.yaml")
        if app.state.decision_config is None:
            app.state.decision_config = load_decision(default_config_dir() / "decision.yaml")
        log.info("p02-doc-service started")
        yield

    application = FastAPI(title="p02-doc-service", lifespan=lifespan)
    _register_routes(application)

    @application.exception_handler(Exception)
    async def unhandled_error(_request: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, HTTPException):
            raise exc
        log.info("unhandled_error type=%s", type(exc).__name__)
        return JSONResponse(status_code=500, content={"detail": "internal_error"})

    return application


def _register_routes(app: FastAPI) -> None:
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

    @app.post("/v1/documents")
    async def upload_document(
        request: Request,
        file: Annotated[UploadFile | None, File()] = None,
        _: None = Depends(require_internal_token),
    ) -> JSONResponse:
        if file is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="file_required")
        payload = await _read_limited(file)
        if not payload:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty_file")
        mime = detect_mime(payload)
        filename = Path(file.filename or "upload").name
        if mime is None:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="unsupported_type",
            )
        if not filename_matches_mime(filename, mime):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="magic_mismatch",
            )
        digest = hashlib.sha256(payload).hexdigest()
        documents: DocumentRepository = request.app.state.documents
        file_storage: Storage = request.app.state.storage
        storage_path = file_storage.put(digest, payload)
        stored = documents.put(
            NewDocument(
                sha256=digest,
                original_filename=filename,
                mime_type=mime,
                size_bytes=len(payload),
                storage_path=storage_path,
            )
        )
        if not stored.deduplicated:
            notifier: IntakeNotifier = request.app.state.intake
            notifier.notify(str(stored.id), stored.sha256)
        status_code = status.HTTP_200_OK if stored.deduplicated else status.HTTP_201_CREATED
        return JSONResponse(
            status_code=status_code,
            content={
                "document_id": str(stored.id),
                "sha256": stored.sha256,
                "deduplicated": stored.deduplicated,
                "mime_type": stored.mime_type,
                "size_bytes": stored.size_bytes,
            },
        )

    @app.get("/v1/documents/{document_id}/file")
    def get_file(
        document_id: UUID,
        request: Request,
        _: None = Depends(require_internal_token),
    ) -> Response:
        documents: DocumentRepository = request.app.state.documents
        stored = documents.get(document_id)
        if stored is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
        file_storage: Storage = request.app.state.storage
        try:
            data = file_storage.get(stored.storage_path)
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="file_missing",
            ) from exc
        return Response(content=data, media_type=stored.mime_type)

    @app.post("/v1/extractions/validate")
    def validate_extraction(
        body: ValidateIn,
        request: Request,
        _: None = Depends(require_internal_token),
    ) -> ValidateOut:
        vat_config: VatRatesConfig = request.app.state.vat_config
        decision: DecisionConfig = request.app.state.decision_config
        lines = [
            VatLine(rate=item.rate, base=item.base, vat=item.vat) for item in body.vat_breakdown
        ]
        results = [
            business_id_checksum(body.supplier_business_id),
            iban_checksum(body.iban),
            reference_number(body.reference_number),
            dates(body.invoice_date, body.due_date, today=today_helsinki()),
            vat_math(
                body.net_total,
                body.vat_total,
                body.gross_total,
                lines,
                tolerance=decision.money_tolerance,
                rate_unit=vat_config.rate_unit,
            ),
            vat_rates(lines, vat_config, invoice_date=body.invoice_date),
        ]
        return ValidateOut(results=results)


async def _read_limited(upload: UploadFile) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(READ_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="file_too_large",
            )
        chunks.append(chunk)
    return b"".join(chunks)


app = create_app(load_env=True)


def main() -> None:
    import uvicorn

    uvicorn.run(
        "p02_doc_service.main:app",
        host="0.0.0.0",
        port=8000,
        factory=False,
    )


if __name__ == "__main__":
    main()
