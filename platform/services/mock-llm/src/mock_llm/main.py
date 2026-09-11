"""OpenAI-compatible mock LLM used by local stacks and CI."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

LOGGER = logging.getLogger("mock_llm")

AdminMode = Literal["invalid_json", "timeout", "429", "500", "normal"]

# TODO(verify): confirm Chat Completions structured-output field names against
# current OpenAI API docs. Implemented common shape:
# {type: json_schema, json_schema: {name, schema, strict}}.


def _log(event: str, **fields: object) -> None:
    payload = {"event": event, **fields}
    LOGGER.info("%s", json.dumps(payload, default=str, separators=(",", ":")))


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if raw == "":
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        msg = f"{name} must be a number, got {raw!r}"
        raise RuntimeError(msg) from exc
    if value < 0:
        msg = f"{name} must be >= 0"
        raise RuntimeError(msg)
    return value


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        msg = f"{name} must be an integer, got {raw!r}"
        raise RuntimeError(msg) from exc
    if value < 0:
        msg = f"{name} must be >= 0"
        raise RuntimeError(msg)
    return value


def _env_path(name: str) -> Path | None:
    raw = os.environ.get(name, "").strip()
    if raw == "":
        return None
    return Path(raw)


@dataclass
class ServiceState:
    mode: AdminMode = "normal"
    timeout_seconds: float = 60.0
    retry_after_s: int = 2
    fixtures_dir: Path | None = None


state = ServiceState()


def reset_app_state() -> None:
    """Reload settings from the environment and return to normal mode."""
    state.mode = "normal"
    state.timeout_seconds = _env_float("MOCK_LLM_TIMEOUT_SECONDS", 60.0)
    state.retry_after_s = _env_int("MOCK_LLM_RETRY_AFTER_S", 2)
    state.fixtures_dir = _env_path("MOCK_LLM_FIXTURES_DIR")


def request_hash(model: str, messages: Sequence[Mapping[str, Any]]) -> str:
    """Return sha256 of canonical JSON for (model, messages)."""
    normalized: list[dict[str, Any]] = []
    for message in messages:
        normalized.append(
            {
                "content": message.get("content"),
                "role": message.get("role"),
            }
        )
    blob = json.dumps(
        {"messages": normalized, "model": model},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def count_tokens(text: str) -> int:
    """Deterministic token estimate: 4 characters per token."""
    if text == "":
        return 0
    return max(1, (len(text) + 3) // 4)


def default_from_schema(schema: Mapping[str, Any] | None) -> Any:
    """Build a deterministic value that satisfies a JSON schema."""
    if not schema:
        return {"ok": True}

    if "const" in schema:
        return schema["const"]
    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and enum_values:
        return enum_values[0]
    if "default" in schema:
        return schema["default"]

    raw_type = schema.get("type")
    type_name: str | None
    if isinstance(raw_type, list):
        type_name = next((item for item in raw_type if item != "null"), None)
        if type_name is None and raw_type:
            type_name = str(raw_type[0])
    elif isinstance(raw_type, str):
        type_name = raw_type
    else:
        type_name = None

    if type_name == "object" or "properties" in schema:
        properties = schema.get("properties")
        props: dict[str, Any] = properties if isinstance(properties, dict) else {}
        required = schema.get("required")
        keys: list[str]
        if isinstance(required, list) and required:
            keys = [key for key in required if isinstance(key, str)]
        else:
            keys = [key for key in props if isinstance(key, str)]
        out: dict[str, Any] = {}
        for key in keys:
            child = props.get(key)
            out[key] = default_from_schema(child if isinstance(child, dict) else {})
        return out if out else {"ok": True}

    if type_name == "array":
        items = schema.get("items")
        min_items_raw = schema.get("minItems") or 0
        min_items = int(min_items_raw) if isinstance(min_items_raw, int | float) else 0
        if isinstance(items, dict) and min_items > 0:
            return [default_from_schema(items) for _ in range(min_items)]
        return []

    if type_name == "string":
        return "default"
    if type_name == "integer":
        minimum = schema.get("minimum")
        return int(minimum) if isinstance(minimum, int | float) else 0
    if type_name == "number":
        minimum = schema.get("minimum")
        return float(minimum) if isinstance(minimum, int | float) else 0.0
    if type_name == "boolean":
        return False
    if type_name == "null":
        return None

    for union_key in ("anyOf", "oneOf"):
        options = schema.get(union_key)
        if isinstance(options, list) and options:
            first = options[0]
            if isinstance(first, dict):
                return default_from_schema(first)

    return {"ok": True}


def _unwrap_fixture(data: Any) -> Any:
    if isinstance(data, dict):
        if "content" in data:
            return data["content"]
        if "response" in data:
            return data["response"]
    return data


def lookup_fixture(digest: str, fixtures_dir: Path | None) -> Any | None:
    """Load a fixture object for digest, or None if missing."""
    if fixtures_dir is None or not fixtures_dir.is_dir():
        return None

    hashed_path = fixtures_dir / f"{digest}.json"
    if hashed_path.is_file():
        loaded = json.loads(hashed_path.read_text(encoding="utf-8"))
        return _unwrap_fixture(loaded)

    for path in sorted(fixtures_dir.glob("*.json")):
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            continue
        if loaded.get("hash") == digest:
            return _unwrap_fixture(loaded)
        model = loaded.get("model")
        messages = loaded.get("messages")
        if isinstance(model, str) and isinstance(messages, list):
            typed_messages: list[Mapping[str, Any]] = [
                item for item in messages if isinstance(item, dict)
            ]
            if request_hash(model, typed_messages) == digest:
                return _unwrap_fixture(loaded)
    return None


def _message_text(content: str | list[Any] | None) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for item in content:
        if isinstance(item, dict):
            text = item.get("text")
            if isinstance(text, str):
                parts.append(text)
    return " ".join(parts)


def _assistant_content(payload: Any) -> str:
    if isinstance(payload, str):
        return payload
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


class JsonSchemaSpec(BaseModel):
    """OpenAI structured output `json_schema` object.

    TODO(verify): confirm field names against OpenAI Chat Completions
    structured outputs docs (name, schema, strict).
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    name: str = "response"
    schema_: dict[str, Any] = Field(default_factory=dict, alias="schema")
    strict: bool | None = None


class ResponseFormat(BaseModel):
    """TODO(verify): confirm `response_format` envelope against OpenAI docs."""

    model_config = ConfigDict(extra="ignore")

    type: Literal["json_schema", "json_object", "text"] = "json_schema"
    json_schema: JsonSchemaSpec | None = None


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: str
    content: str | list[Any] | None = None


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    model: str
    messages: list[ChatMessage] = Field(min_length=1)
    response_format: ResponseFormat | None = None


class AdminModeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: AdminMode


reset_app_state()
app = FastAPI(title="mock-llm", version="0.1.0")


@app.get("/health")
@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/admin/mode")
def set_mode(body: AdminModeRequest) -> dict[str, str]:
    state.mode = body.mode
    _log("admin.mode", mode=state.mode)
    return {"mode": state.mode}


def _openai_error(
    status_code: int,
    message: str,
    error_type: str,
    code: str,
) -> JSONResponse:
    headers: dict[str, str] = {}
    if status_code == 429:
        headers["Retry-After"] = str(state.retry_after_s)
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "message": message,
                "type": error_type,
                "param": None,
                "code": code,
            }
        },
        headers=headers,
    )


def _completion_response(
    *,
    model: str,
    digest: str,
    content: str,
    prompt_text: str,
) -> dict[str, Any]:
    prompt_tokens = count_tokens(prompt_text)
    completion_tokens = count_tokens(content)
    return {
        "id": f"chatcmpl-{digest[:24]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


@app.post("/v1/chat/completions")
async def chat_completions(body: ChatCompletionRequest) -> JSONResponse:
    raw_messages = [message.model_dump() for message in body.messages]
    digest = request_hash(body.model, raw_messages)
    prompt_text = " ".join(_message_text(message.content) for message in body.messages)
    _log("chat.completions", hash=digest, model=body.model, mode=state.mode)

    if state.mode == "500":
        return _openai_error(
            500,
            "Internal server error",
            "server_error",
            "internal_error",
        )
    if state.mode == "429":
        return _openai_error(
            429,
            "Rate limit exceeded",
            "rate_limit_error",
            "rate_limit_exceeded",
        )
    if state.mode == "timeout":
        await asyncio.sleep(state.timeout_seconds)

    if state.mode == "invalid_json":
        return JSONResponse(
            _completion_response(
                model=body.model,
                digest=digest,
                content="not-json{",
                prompt_text=prompt_text,
            )
        )

    fixture = lookup_fixture(digest, state.fixtures_dir)
    if fixture is not None:
        content = _assistant_content(fixture)
    else:
        schema: dict[str, Any] | None = None
        fmt = body.response_format
        if fmt is not None and fmt.json_schema is not None:
            schema = fmt.json_schema.schema_
        content = _assistant_content(default_from_schema(schema))

    return JSONResponse(
        _completion_response(
            model=body.model,
            digest=digest,
            content=content,
            prompt_text=prompt_text,
        )
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("mock_llm.main:app", host="127.0.0.1", port=8090)
