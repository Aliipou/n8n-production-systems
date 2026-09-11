from __future__ import annotations

from typing import Any

import httpx
import pytest

from review_ui.receiver import ReceiverError, post_decision
from review_ui.signing import SIGNATURE_HEADER, encode_body, sign_body


def test_post_decision_sends_hmac_of_raw_body(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"id": "abc", "status": "approved"}
    captured: dict[str, Any] = {}

    def fake_post(
        url: str,
        *,
        content: bytes,
        headers: dict[str, str],
        timeout: float,
    ) -> httpx.Response:
        captured["url"] = url
        captured["content"] = content
        captured["headers"] = headers
        captured["timeout"] = timeout
        request = httpx.Request("POST", url, content=content, headers=headers)
        return httpx.Response(200, request=request, json={"ok": True})

    monkeypatch.setattr("review_ui.receiver.httpx.post", fake_post)
    post_decision(
        url="http://n8n-main:5678/webhook/plt/review-decision",
        secret="change-me",
        payload=payload,
    )
    body = encode_body(payload)
    assert captured["content"] == body
    assert captured["headers"][SIGNATURE_HEADER] == sign_body("change-me", body)
    assert captured["headers"]["Content-Type"] == "application/json"


def test_post_decision_raises_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(
        url: str,
        *,
        content: bytes,
        headers: dict[str, str],
        timeout: float,
    ) -> httpx.Response:
        request = httpx.Request("POST", url, content=content, headers=headers)
        return httpx.Response(500, request=request, text="no")

    monkeypatch.setattr("review_ui.receiver.httpx.post", fake_post)
    with pytest.raises(ReceiverError):
        post_decision(
            url="http://n8n-main:5678/webhook/plt/review-decision",
            secret="change-me",
            payload={"id": "abc", "status": "rejected"},
        )
