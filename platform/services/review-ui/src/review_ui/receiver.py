from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Any

import httpx

from review_ui.signing import SIGNATURE_HEADER, encode_body, sign_body

LOGGER = logging.getLogger("review_ui")

WEBHOOK_TIMEOUT_S = 10.0


class ReceiverError(Exception):
    """HMAC-signed POST to the review decision webhook failed."""


def post_decision(
    *,
    url: str,
    secret: str,
    payload: Mapping[str, Any],
) -> None:
    body = encode_body(payload)
    signature = sign_body(secret, body)
    headers = {
        "Content-Type": "application/json",
        SIGNATURE_HEADER: signature,
    }
    try:
        response = httpx.post(
            url,
            content=body,
            headers=headers,
            timeout=WEBHOOK_TIMEOUT_S,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        LOGGER.error(
            json.dumps(
                {
                    "event": "review_receiver_failed",
                    "id": payload.get("id"),
                    "error_class": type(exc).__name__,
                }
            )
        )
        raise ReceiverError(str(exc)) from exc
    LOGGER.info(
        json.dumps(
            {
                "event": "review_receiver_posted",
                "id": payload.get("id"),
                "status_code": response.status_code,
            }
        )
    )
