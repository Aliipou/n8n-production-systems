from __future__ import annotations

import json
import shutil
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from sanitize_workflows import dumps_stable  # noqa: E402
from sync_snippets import main, sync_workflow  # noqa: E402


@pytest.fixture
def scratch_dir() -> Iterator[Path]:
    root = Path(__file__).resolve().parent / "_scratch"
    root.mkdir(exist_ok=True)
    path = root / f"sync-{time.time_ns()}"
    path.mkdir()
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_sync_snippets_replaces_body(scratch_dir: Path) -> None:
    snippets = scratch_dir / "snippets"
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


def test_sync_snippets_cli_rewrites_file(scratch_dir: Path) -> None:
    snippets = scratch_dir / "snippets"
    snippets.mkdir()
    replacement = "// snippet: classify_error\nreturn items.map((i) => i);\n"
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
    path = scratch_dir / "wf.json"
    path.write_text(dumps_stable(wf), encoding="utf-8")
    assert main([str(path), "--snippets-dir", str(snippets)]) == 0
    updated = json.loads(path.read_text(encoding="utf-8"))
    assert updated["nodes"][0]["parameters"]["jsCode"] == replacement
