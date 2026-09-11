"""Error taxonomy (spec 00 section 4).

Classes: transient, rate_limited, invalid_data, auth, permanent, unknown.
HTTP 409 on an idempotent create is class ``success`` with
``idempotent_success`` true (not an error).

Backoff: full jitter, ``delay_s = jitter_fn() * min(cap, base * 2**attempt)``.
``attempt`` is 0-based (0 is the delay after the first failure). Defaults:
base 2 s, cap 300 s, max 6 attempts. ``jitter_fn`` returns a float in [0, 1).
"""

from __future__ import annotations

import random
import re
from collections.abc import Callable, Mapping
from typing import Any

MAX_ATTEMPTS = 6
BASE_DELAY_S = 2.0
CAP_DELAY_S = 300.0

TRANSIENT_STATUS = frozenset({500, 502, 503, 504})
RATE_LIMIT_STATUS = frozenset({429})
INVALID_STATUS = frozenset({400, 422})
AUTH_STATUS = frozenset({401, 403})
PERMANENT_STATUS = frozenset({404, 410, 501, 409})

TRANSIENT_CODES = frozenset(
    {
        "etimedout",
        "esockettimedout",
        "econnreset",
        "econnrefused",
        "econnaborted",
        "epipe",
        "eai_again",
        "enotfound",
        "eai_noname",
        "und_err_connect_timeout",
        "und_err_headers_timeout",
        "und_err_body_timeout",
        "timeout",
        "timeouterror",
    }
)

TRANSIENT_MARKERS = (
    "timed out",
    "timeout",
    "deadline exceeded",
    "connection reset",
    "connection refused",
    "socket hang up",
    "econnreset",
    "econnrefused",
    "eai_again",
    "enotfound",
    "temporary failure in name resolution",
    "getaddrinfo",
)

RATE_LIMIT_MARKERS = (
    "rate_limit",
    "ratelimit",
    "too many requests",
    "too_many_requests",
    "throttl",
    "resource_exhausted",
)

INVALID_MARKERS = (
    "schema validation",
    "validation error",
    "validation failed",
    "json schema",
    "schema_validation",
    "validation_error",
    "pydantic",
)

_STATUS_KEYS = ("status", "statusCode", "httpCode", "status_code", "http_code")
_CODE_KEYS = ("code", "errno", "errorCode", "error_code")
_MESSAGE_KEYS = ("message", "description")
_STATUS_IN_MESSAGE = re.compile(r"status code (\d{3})", re.I)
_HTTP_IN_MESSAGE = re.compile(r"\bHTTP[ /](\d{3})\b", re.I)


def classify_error(input_value: Mapping[str, Any] | None = None) -> dict[str, Any]:
    parsed = _parse(input_value)
    if parsed["status"] == 409 and parsed["idempotent_create"]:
        return _result("success", retry=False, idempotent_success=True)
    if parsed["status"] in TRANSIENT_STATUS:
        return _result("transient", retry=True, idempotent_success=False)
    if parsed["status"] in RATE_LIMIT_STATUS:
        return _result("rate_limited", retry=True, idempotent_success=False)
    if parsed["status"] in INVALID_STATUS:
        return _result("invalid_data", retry=False, idempotent_success=False)
    if parsed["status"] in AUTH_STATUS:
        return _result("auth", retry=False, idempotent_success=False)
    if parsed["status"] in PERMANENT_STATUS:
        return _result("permanent", retry=False, idempotent_success=False)
    if _is_transient(parsed["code"], parsed["blob"]):
        return _result("transient", retry=True, idempotent_success=False)
    if _has_marker(parsed["blob"], RATE_LIMIT_MARKERS):
        return _result("rate_limited", retry=True, idempotent_success=False)
    if _has_marker(parsed["blob"], INVALID_MARKERS):
        return _result("invalid_data", retry=False, idempotent_success=False)
    return _result("unknown", retry=False, idempotent_success=False)


def compute_next_delay(
    attempt: int,
    base: float = BASE_DELAY_S,
    cap: float = CAP_DELAY_S,
    jitter_fn: Callable[[], float] | None = None,
) -> float:
    exp = 0 if attempt is None or attempt < 0 else int(attempt)
    if jitter_fn is None:
        jitter_fn = random.random
    return jitter_fn() * min(cap, base * (2**exp))


def _result(cls: str, retry: bool, idempotent_success: bool) -> dict[str, Any]:
    return {"class": cls, "retry": retry, "idempotent_success": idempotent_success}


def _parse(input_value: Mapping[str, Any] | None) -> dict[str, Any]:
    src = input_value if isinstance(input_value, Mapping) else {}
    error_field = src.get("error")
    nested: Mapping[str, Any] = error_field if isinstance(error_field, Mapping) else {}
    status = _first_status(src, nested)
    code = _norm_code(_first_text(src, nested, _CODE_KEYS))
    message = _first_text(src, nested, _MESSAGE_KEYS).lower()
    error_text = error_field.lower() if isinstance(error_field, str) else ""
    blob = f"{code} {message} {error_text}".replace("-", "_")
    idempotent_create = any(
        src.get(key) is True or nested.get(key) is True
        for key in ("idempotent_create", "idempotentCreate")
    )
    return {
        "status": status,
        "code": code,
        "blob": blob,
        "idempotent_create": idempotent_create,
    }


def _first_status(src: Mapping[str, Any], nested: Mapping[str, Any]) -> int | None:
    for key in _STATUS_KEYS:
        for block in (src, nested):
            parsed = _to_status(block.get(key))
            if parsed is not None:
                return parsed
    msg = str(src.get("message") or nested.get("message") or src.get("error") or "")
    match = _STATUS_IN_MESSAGE.search(msg) or _HTTP_IN_MESSAGE.search(msg)
    return _to_status(match.group(1)) if match else None


def _first_text(
    src: Mapping[str, Any], nested: Mapping[str, Any], keys: tuple[str, ...]
) -> str:
    for key in keys:
        for block in (src, nested):
            value = block.get(key)
            if isinstance(value, str) and value:
                return value
    return ""


def _to_status(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if 100 <= value <= 599 else None
    if isinstance(value, float) and value.is_integer():
        number = int(value)
        return number if 100 <= number <= 599 else None
    if isinstance(value, str) and value.strip().isdigit():
        number = int(value.strip())
        return number if 100 <= number <= 599 else None
    return None


def _norm_code(value: str) -> str:
    return value.lower().replace("-", "_")


def _is_transient(code: str, blob: str) -> bool:
    return code in TRANSIENT_CODES or _has_marker(blob, TRANSIENT_MARKERS)


def _has_marker(blob: str, markers: tuple[str, ...]) -> bool:
    return any(marker in blob for marker in markers)
