from __future__ import annotations

import io
import json
import shutil
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from sanitize_workflows import (  # noqa: E402
    SanitizeError,
    dumps_stable,
    find_secret_matches,
    main,
    process_text,
    sanitize_document,
)

GOOD = json.loads((FIXTURES / "good_workflow.json").read_text(encoding="utf-8"))


@pytest.fixture
def workdir() -> Iterator[Path]:
    path = Path(__file__).resolve().parent / "_work" / uuid.uuid4().hex
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
        try:
            path.parent.rmdir()
        except OSError:
            pass


def test_good_fixture_has_no_runtime_fields() -> None:
    assert "pinData" not in GOOD
    assert "staticData" not in GOOD
    assert "executionId" not in GOOD
    assert "instanceId" not in (GOOD.get("meta") or {})


def test_strips_pindata_staticdata_instanceid_and_execution_refs() -> None:
    dirty = {
        "name": "[PLT] Dirty",
        "id": "dirty",
        "pinData": {"Manual start": [{"json": {"n": 1}}]},
        "staticData": {"node": {"count": 1}},
        "meta": {"instanceId": "abc123instanceid", "keepMe": True},
        "executionId": "exec-1",
        "executionIds": ["exec-1"],
        "lastExecution": {"status": "success"},
        "settings": {"executionOrder": "v1", "errorWorkflow": "eh"},
        "nodes": [
            {
                "name": "Pass through",
                "type": "n8n-nodes-base.code",
                "executionId": "nested-exec",
                "parameters": {"jsCode": "return items;"},
            }
        ],
    }
    clean = sanitize_document(dirty)
    assert "pinData" not in clean
    assert "staticData" not in clean
    assert "executionId" not in clean
    assert "executionIds" not in clean
    assert "lastExecution" not in clean
    assert clean["meta"] == {"keepMe": True}
    assert clean["settings"]["executionOrder"] == "v1"
    assert "executionId" not in clean["nodes"][0]


def test_sorted_keys_two_space_indent_trailing_newline() -> None:
    text = process_text('{"b": 1, "a": {"d": 2, "c": 3}}')
    assert text.endswith("\n")
    assert text == dumps_stable({"a": {"c": 3, "d": 2}, "b": 1})
    assert '{\n  "a"' in text


def test_stdin_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    stdin = io.StringIO('{"b":1,"a":2}\n')
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(sys, "stdout", stdout)
    assert main([]) == 0
    assert stdout.getvalue() == dumps_stable({"a": 2, "b": 1})


def test_in_place_dir(workdir: Path) -> None:
    path = workdir / "wf.json"
    path.write_text('{"z": 1, "a": 2}\n', encoding="utf-8")
    assert main(["--in-place", str(workdir)]) == 0
    assert path.read_text(encoding="utf-8") == dumps_stable({"a": 2, "z": 1})


def test_file_args_rewrite(workdir: Path) -> None:
    path = workdir / "wf.json"
    path.write_text(
        '{"name": "[PLT] X", "pinData": {}, "a": 1}\n', encoding="utf-8"
    )
    assert main([str(path)]) == 0
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "pinData" not in data
    assert data["a"] == 1


def test_good_fixture_round_trip() -> None:
    raw = (FIXTURES / "good_workflow.json").read_text(encoding="utf-8")
    out = process_text(raw)
    assert json.loads(out)["name"] == "[PLT] Test Good Workflow"
    assert out.endswith("\n")


@pytest.mark.parametrize(
    "builder",
    [
        lambda: "sk" + "-" + ("a" * 20),
        lambda: "xox" + "b-" + "1234567890-abcdefghij",
        lambda: "Bearer " + ("T" * 32),
        lambda: "-----BEGIN " + "RSA PRIVATE KEY-----",
        lambda: "AKIA" + ("A" * 16),
        lambda: "ghp_" + ("a" * 36),
    ],
)
def test_secret_patterns_fail(builder: object) -> None:
    secret = builder()  # type: ignore[operator]
    doc = {"name": "x", "nodes": [{"parameters": {"token": secret}}]}
    matches = find_secret_matches(doc)
    assert matches, f"expected a match for constructed secret starting {secret[:8]!r}"
    with pytest.raises(SanitizeError):
        sanitize_document(doc)


def test_placeholders_are_not_secrets() -> None:
    doc = {
        "name": "x",
        "nodes": [
            {
                "parameters": {
                    "value": "${INTERNAL_API_TOKEN}",
                    "header": "Bearer ${INTERNAL_API_TOKEN}",
                    "url": "={{ $json.base_url }}",
                }
            }
        ],
    }
    assert find_secret_matches(doc) == []
    sanitize_document(doc)


def test_secret_in_file_exits_nonzero(workdir: Path) -> None:
    path = workdir / "secret.json"
    token = "sk" + "-" + ("b" * 24)
    path.write_text(
        json.dumps({"nodes": [{"parameters": {"k": token}}]}), encoding="utf-8"
    )
    assert main([str(path)]) == 1
    assert token in path.read_text(encoding="utf-8")
