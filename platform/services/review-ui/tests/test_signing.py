from __future__ import annotations

import pytest

from review_ui.config import Settings
from review_ui.signing import (
    constant_time_equals,
    encode_body,
    sign_body,
    signatures_match,
)


def test_sign_body_rfc_fox_vector() -> None:
    # Common HMAC-SHA256 test vector (key "key", body is the fox sentence).
    body = b"The quick brown fox jumps over the lazy dog"
    assert (
        sign_body("key", body)
        == "sha256=f7bc83f430538424b13298e6aa6fb143ef4d59a14946175997479dbc2d1a3cd8"
    )


def test_sign_body_changes_with_body() -> None:
    secret = "change-me"
    first = sign_body(secret, b'{"status":"approved"}')
    second = sign_body(secret, b'{"status":"rejected"}')
    assert first != second
    assert first.startswith("sha256=")
    assert second.startswith("sha256=")


def test_sign_body_accepts_bytes_secret() -> None:
    assert sign_body(b"key", b"abc") == sign_body("key", b"abc")


def test_constant_time_equals_uses_compare_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []

    def fake_compare(left: str, right: str) -> bool:
        calls.append((left, right))
        return left == right

    monkeypatch.setattr("review_ui.signing.hmac.compare_digest", fake_compare)
    assert constant_time_equals("same", "same") is True
    assert constant_time_equals("left", "right") is False
    assert calls == [("same", "same"), ("left", "right")]


def test_signatures_match_rejects_length_mismatch() -> None:
    expected = sign_body("secret", b"{}")
    assert signatures_match(expected, expected) is True
    assert signatures_match(expected, expected[:-1]) is False
    assert signatures_match(expected, "") is False
    assert signatures_match("", expected) is False


def test_encode_body_is_stable_and_signed() -> None:
    payload = {"status": "approved", "id": "abc"}
    body = encode_body(payload)
    assert body == b'{"id":"abc","status":"approved"}'
    signature = sign_body("change-me", body)
    assert signatures_match(signature, sign_body("change-me", body))
    assert signatures_match(signature, sign_body("other", body)) is False


def test_settings_placeholders() -> None:
    settings = Settings()
    settings.validate_local_auth()
    assert settings.review_ui_user == "reviewer"
    assert settings.review_receiver_url.endswith("/webhook/plt/review-decision")
