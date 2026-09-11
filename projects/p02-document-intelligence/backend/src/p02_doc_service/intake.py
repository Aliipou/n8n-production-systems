"""Optional n8n intake webhook. Files never go in the payload, only document_id."""

from __future__ import annotations

import logging
from typing import Protocol

import httpx

log = logging.getLogger("p02_doc_service")


class IntakeNotifier(Protocol):
    def notify(self, document_id: str, sha256: str) -> None: ...


class NullIntake:
    def notify(self, document_id: str, sha256: str) -> None:
        del document_id, sha256


class HttpIntake:
    def __init__(self, url: str, token: str, *, timeout_s: float = 5.0) -> None:
        self._url = url
        self._token = token
        self._timeout_s = timeout_s

    def notify(self, document_id: str, sha256: str) -> None:
        try:
            response = httpx.post(
                self._url,
                json={"document_id": document_id, "sha256": sha256},
                headers={"INTERNAL_API_TOKEN": self._token},
                timeout=self._timeout_s,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            log.info(
                "intake_webhook_failed document_id=%s error_class=%s",
                document_id,
                type(exc).__name__,
            )
