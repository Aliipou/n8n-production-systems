"""Tests for mock-llm chat completions and admin modes."""

from __future__ import annotations

import json
import shutil
import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient

from mock_llm.main import app, request_hash, reset_app_state, state

SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": ["demo_request", "pricing", "other"],
        },
        "ok": {"type": "boolean"},
    },
    "required": ["intent", "ok"],
    "additionalProperties": False,
}


def _completion_payload(
    *,
    model: str = "gpt-4o-mini",
    content: str = "qualify this lead",
) -> dict[str, object]:
    return {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "lead_class",
                "strict": True,
                "schema": SCHEMA,
            },
        },
    }


@pytest.fixture(autouse=True)
def _reset_state() -> Iterator[None]:
    reset_app_state()
    yield
    reset_app_state()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def fixtures_dir() -> Iterator[Path]:
    root = Path(__file__).resolve().parent / "_scratch"
    root.mkdir(exist_ok=True)
    path = root / f"fix-{time.time_ns()}"
    path.mkdir()
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_healthz(client: TestClient) -> None:
    health = client.get("/health")
    healthz = client.get("/healthz")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert healthz.status_code == 200
    assert healthz.json() == {"status": "ok"}


def test_happy_path_json(client: TestClient) -> None:
    response = client.post("/v1/chat/completions", json=_completion_payload())
    assert response.status_code == 200
    body = response.json()
    content = json.loads(body["choices"][0]["message"]["content"])
    assert content["intent"] == "demo_request"
    assert content["ok"] is False
    usage = body["usage"]
    assert usage["prompt_tokens"] >= 1
    assert usage["completion_tokens"] >= 1
    assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["message"]["role"] == "assistant"


def test_fixture_hash_stability(fixtures_dir: Path, client: TestClient) -> None:
    model = "gpt-4o-mini"
    messages = [{"role": "user", "content": "stable hash please"}]
    digest_a = request_hash(model, messages)
    digest_b = request_hash(model, messages)
    digest_c = request_hash(
        model,
        [{"content": "stable hash please", "role": "user"}],
    )
    assert digest_a == digest_b == digest_c
    assert len(digest_a) == 64

    fixture_body = {"intent": "pricing", "ok": True}
    (fixtures_dir / f"{digest_a}.json").write_text(
        json.dumps(fixture_body),
        encoding="utf-8",
    )
    state.fixtures_dir = fixtures_dir

    response = client.post(
        "/v1/chat/completions",
        json=_completion_payload(model=model, content="stable hash please"),
    )
    assert response.status_code == 200
    content = json.loads(response.json()["choices"][0]["message"]["content"])
    assert content == fixture_body


def test_fixture_hash_field_lookup(fixtures_dir: Path, client: TestClient) -> None:
    model = "gpt-4o-mini"
    messages = [{"role": "user", "content": "named fixture"}]
    digest = request_hash(model, messages)
    payload = {"intent": "other", "ok": True}
    (fixtures_dir / "named.json").write_text(
        json.dumps({"hash": digest, "content": payload}),
        encoding="utf-8",
    )
    state.fixtures_dir = fixtures_dir

    response = client.post(
        "/v1/chat/completions",
        json=_completion_payload(model=model, content="named fixture"),
    )
    assert response.status_code == 200
    content = json.loads(response.json()["choices"][0]["message"]["content"])
    assert content == payload


def test_admin_500(client: TestClient) -> None:
    mode = client.post("/admin/mode", json={"mode": "500"})
    assert mode.status_code == 200
    assert mode.json() == {"mode": "500"}
    response = client.post("/v1/chat/completions", json=_completion_payload())
    assert response.status_code == 500
    assert response.json()["error"]["type"] == "server_error"


def test_admin_429_retry_after(client: TestClient) -> None:
    mode = client.post("/admin/mode", json={"mode": "429"})
    assert mode.status_code == 200
    response = client.post("/v1/chat/completions", json=_completion_payload())
    assert response.status_code == 429
    assert response.headers["retry-after"] == "2"
    assert response.json()["error"]["type"] == "rate_limit_error"


def test_admin_invalid_json(client: TestClient) -> None:
    mode = client.post("/admin/mode", json={"mode": "invalid_json"})
    assert mode.status_code == 200
    assert mode.json() == {"mode": "invalid_json"}
    response = client.post("/v1/chat/completions", json=_completion_payload())
    assert response.status_code == 200
    raw = response.json()["choices"][0]["message"]["content"]
    with pytest.raises(json.JSONDecodeError):
        json.loads(raw)


def test_admin_normal_resets(client: TestClient) -> None:
    client.post("/admin/mode", json={"mode": "500"})
    reset = client.post("/admin/mode", json={"mode": "normal"})
    assert reset.json() == {"mode": "normal"}
    response = client.post("/v1/chat/completions", json=_completion_payload())
    assert response.status_code == 200
    json.loads(response.json()["choices"][0]["message"]["content"])


def test_admin_rejects_unknown_mode(client: TestClient) -> None:
    response = client.post("/admin/mode", json={"mode": "nope"})
    assert response.status_code == 422


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_healthy(port: int) -> None:
    deadline = time.monotonic() + 5.0
    url = f"http://127.0.0.1:{port}/healthz"
    while time.monotonic() < deadline:
        try:
            response = httpx.get(url, timeout=0.2)
        except httpx.HTTPError:
            time.sleep(0.05)
            continue
        if response.status_code == 200:
            return
        time.sleep(0.05)
    raise AssertionError("mock-llm test server did not become healthy")


def test_timeout_mode() -> None:
    state.mode = "timeout"
    state.timeout_seconds = 2.0
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        _wait_healthy(port)
        with pytest.raises(httpx.TimeoutException):
            httpx.post(
                f"http://127.0.0.1:{port}/v1/chat/completions",
                json=_completion_payload(),
                timeout=0.2,
            )
    finally:
        server.should_exit = True
