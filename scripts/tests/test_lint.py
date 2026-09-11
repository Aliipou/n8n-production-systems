from __future__ import annotations

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

from lint_workflows import (  # noqa: E402
    MAX_NODES,
    has_literal_http_url,
    lint_document,
    lint_workflow,
    main,
)
from sync_snippets import sync_workflow  # noqa: E402

GOOD = json.loads((FIXTURES / "good_workflow.json").read_text(encoding="utf-8"))
BAD = json.loads((FIXTURES / "bad_workflow.json").read_text(encoding="utf-8"))


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


def _messages(workflow: dict, **kwargs: object) -> str:
    issues = lint_workflow(workflow, path="wf.json", **kwargs)  # type: ignore[arg-type]
    return "\n".join(issue.message for issue in issues)


def test_good_fixture_passes() -> None:
    issues = lint_document(GOOD, path="good_workflow.json")
    assert issues == []


def test_good_fixture_cli() -> None:
    assert main([str(FIXTURES / "good_workflow.json")]) == 0


def test_bad_fixture_fails_on_required_rules() -> None:
    text = _messages(BAD)
    assert "pinData is present" in text
    assert "default node name" in text
    assert "HTTP Request1" in text
    assert "'Code'" in text
    assert "Set2" in text
    assert "'IF'" in text
    assert "missing settings.errorWorkflow" in text
    assert "HTTP Request missing parameters.options.timeout" in text
    assert "snippet 'missing_fixture_snippet' missing" in text
    assert "hardcoded http(s) URL" in text


def test_bad_fixture_cli() -> None:
    assert main([str(FIXTURES / "bad_workflow.json")]) == 1


def test_error_handler_may_omit_error_workflow() -> None:
    wf = {
        "name": "[PLT] Error Handler",
        "nodes": [
            {
                "name": "On workflow error",
                "type": "n8n-nodes-base.errorTrigger",
                "parameters": {},
            }
        ],
        "settings": {},
    }
    text = _messages(wf)
    assert "missing settings.errorWorkflow" not in text


def test_more_than_40_nodes_fails() -> None:
    wf = {
        "name": "[PLT] Huge",
        "settings": {"errorWorkflow": "eh"},
        "nodes": [
            {
                "name": f"Step {i}",
                "type": "n8n-nodes-base.noOp",
                "parameters": {},
            }
            for i in range(MAX_NODES + 1)
        ],
    }
    text = _messages(wf)
    assert f"more than {MAX_NODES} nodes" in text


def test_http_timeout_present_passes() -> None:
    wf = {
        "name": "[PLT] Timeout",
        "settings": {"errorWorkflow": "eh"},
        "nodes": [
            {
                "name": "Call flaky api",
                "type": "n8n-nodes-base.httpRequest",
                "parameters": {
                    "url": "={{ $json.base_url }}",
                    "options": {"timeout": 5000},
                },
            }
        ],
    }
    assert _messages(wf) == ""


def test_expression_url_allowed_literal_url_fails() -> None:
    assert not has_literal_http_url("={{ $json.base_url }}")
    assert not has_literal_http_url("{{ $('Lookup settings').item.json.url }}")
    assert has_literal_http_url("http://flaky-api:8091/items")
    assert has_literal_http_url("https://example.invalid/x")
    assert has_literal_http_url("{{ 'http://example.invalid' }}")


def test_settings_lookup_node_may_contain_url() -> None:
    wf = {
        "name": "[PLT] Settings",
        "settings": {"errorWorkflow": "eh"},
        "nodes": [
            {
                "name": "Lookup settings",
                "type": "n8n-nodes-base.postgres",
                "parameters": {
                    "query": "select value from ops.settings where key = 'base_url'",
                    "note": "http://mock-llm:8090 is the local mock, stored in settings",
                },
            }
        ],
    }
    text = _messages(wf)
    assert "hardcoded http(s) URL" not in text


def test_snippet_mismatch(workdir: Path) -> None:
    snippets = workdir / "snippets"
    snippets.mkdir()
    (snippets / "classify_error.js").write_text(
        "// snippet: classify_error\nmodule.exports = 1;\n",
        encoding="utf-8",
    )
    wf = {
        "name": "[PLT] Snippet",
        "settings": {"errorWorkflow": "eh"},
        "nodes": [
            {
                "name": "Classify error",
                "type": "n8n-nodes-base.code",
                "parameters": {
                    "jsCode": "// snippet: classify_error\nreturn items;\n"
                },
            }
        ],
    }
    text = _messages(wf, snippets_dir=snippets)
    assert "Code body differs from code-snippets/classify_error.js" in text


def test_snippet_match_passes(workdir: Path) -> None:
    snippets = workdir / "snippets"
    snippets.mkdir()
    body = "// snippet: classify_error\nreturn items;\n"
    (snippets / "classify_error.js").write_text(body, encoding="utf-8")
    wf = {
        "name": "[PLT] Snippet",
        "settings": {"errorWorkflow": "eh"},
        "nodes": [
            {
                "name": "Classify error",
                "type": "n8n-nodes-base.code",
                "parameters": {"jsCode": body},
            }
        ],
    }
    assert _messages(wf, snippets_dir=snippets) == ""


def test_sync_snippets_replaces_body(workdir: Path) -> None:
    snippets = workdir / "snippets"
    snippets.mkdir()
    replacement = "// snippet: classify_error\nconst out = items;\nreturn out;\n"
    (snippets / "classify_error.js").write_text(replacement, encoding="utf-8")
    wf = {
        "name": "[PLT] Snippet",
        "nodes": [
            {
                "name": "Classify error",
                "type": "n8n-nodes-base.code",
                "parameters": {
                    "jsCode": "// snippet: classify_error\nreturn items;\n"
                },
            }
        ],
    }
    changed = sync_workflow(wf, snippets_dir=snippets, path="wf.json")
    assert changed == 1
    assert wf["nodes"][0]["parameters"]["jsCode"] == replacement
