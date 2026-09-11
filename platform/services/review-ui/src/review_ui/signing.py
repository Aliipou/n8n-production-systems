from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping
from typing import Any

# TODO(verify): header name on the pinned n8n receiver (PLT-T10 workflow).
# Spec allows HMAC over the raw body, or Header Auth plus a signature node.
# GitHub uses X-Hub-Signature-256 with the same sha256=<hex> form.
SIGNATURE_HEADER = "X-Signature-256"
SIGNATURE_PREFIX = "sha256="


def encode_body(payload: Mapping[str, Any]) -> bytes:
    """Stable JSON bytes for HMAC and the webhook POST."""
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def sign_body(secret: str | bytes, body: bytes) -> str:
    """HMAC-SHA256 of raw body. Return value is sha256=<hex>."""
    key = secret.encode("utf-8") if isinstance(secret, str) else secret
    digest = hmac.new(key, body, hashlib.sha256).hexdigest()
    return f"{SIGNATURE_PREFIX}{digest}"


def constant_time_equals(left: str, right: str) -> bool:
    """Compare two strings with hmac.compare_digest."""
    return hmac.compare_digest(left, right)


def signatures_match(expected: str, provided: str) -> bool:
    if not expected or not provided:
        return False
    if len(expected) != len(provided):
        return False
    return constant_time_equals(expected, provided)
