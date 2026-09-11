#!/usr/bin/env python3
"""Lint n8n workflow JSON (PLT-T07 / spec 00 section 7).

Fails on:
- pinData present
- default node names (HTTP Request1, Code, Set2, IF, and similar)
- missing settings.errorWorkflow except workflow names containing "Error Handler"
- HTTP Request nodes without a timeout option
- Code nodes starting with // snippet: name that differ from code-snippets/name.js
- more than 40 nodes
- hardcoded http:// or https:// in node parameters other than credentials
  and settings lookups
- secret patterns (same rules as sanitize_workflows.py)

HTTP Request timeout (pinned n8n, verified 2026-09-11):
  The HTTP Request V3 option collection is parameters.options, and the
  timeout field name is timeout (milliseconds).
  Source: n8n packages/nodes-base/nodes/HttpRequest/V3/Description.ts
  (displayName Timeout, name timeout, parent name options).
  Runtime reads this.getNodeParameter('options') then options.timeout in
  HttpRequestV3.node.ts. Older V2 used the same options.timeout path.
  TODO(verify): exact parameter key on the n8n version pinned in
  platform/VERSIONS.md after PLT-T02. Until then this linter accepts
  parameters.options.timeout (preferred) or parameters.timeout.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from sanitize_workflows import find_secret_matches  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
SNIPPETS_DIR = REPO_ROOT / "code-snippets"
MAX_NODES = 40

# Default canvas names n8n assigns, with optional trailing digits (HTTP Request1).
DEFAULT_NODE_NAME_RE = re.compile(
    r"^(?:"
    r"HTTP Request|Code|Set|IF|If|Switch|Merge|Webhook|"
    r"Edit Fields|Filter|Wait|Split Out|Split In Batches|"
    r"Schedule Trigger|Manual Trigger|Error Trigger|"
    r"No Operation, do nothing|Sticky Note|Note|"
    r"Execute Workflow|Execute Sub-workflow"
    r")\d*$"
)

SNIPPET_FIRST_LINE_RE = re.compile(r"^// snippet:\s*([A-Za-z0-9_.-]+)\s*$")
LITERAL_HTTP_RE = re.compile(r"https?://", re.IGNORECASE)
EXPRESSION_ONLY_RE = re.compile(r"^=?\s*\{\{(.+)\}\}\s*$", re.DOTALL)
SETTINGS_LOOKUP_NAME_RE = re.compile(
    r"(lookup|load|get|read|fetch).{0,40}settings|settings.{0,40}(lookup|table|row)",
    re.IGNORECASE,
)
HTTP_REQUEST_TYPES = frozenset(
    {
        "n8n-nodes-base.httpRequest",
        "n8n-nodes-base.httpRequestTool",
    }
)
CODE_TYPES = frozenset({"n8n-nodes-base.code"})


@dataclass(frozen=True)
class Issue:
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def _iter_workflows(document: Any) -> Iterator[tuple[str, dict[str, Any]]]:
    if isinstance(document, dict):
        yield "", document
    elif isinstance(document, list):
        for index, item in enumerate(document):
            if isinstance(item, dict):
                yield f"[{index}]", item


def _code_body(node: dict[str, Any]) -> str:
    params = node.get("parameters") or {}
    for key in ("jsCode", "pythonCode", "functionCode", "code"):
        value = params.get(key)
        if isinstance(value, str):
            return value
    return ""


def _http_timeout(node: dict[str, Any]) -> Any:
    params = node.get("parameters") or {}
    options = params.get("options")
    if isinstance(options, dict) and options.get("timeout") not in (None, ""):
        return options.get("timeout")
    if params.get("timeout") not in (None, ""):
        return params.get("timeout")
    return None


def _timeout_is_set(node: dict[str, Any]) -> bool:
    timeout = _http_timeout(node)
    if timeout is None:
        return False
    if isinstance(timeout, bool):
        return False
    if isinstance(timeout, (int, float)):
        return timeout > 0
    if isinstance(timeout, str):
        stripped = timeout.strip()
        if not stripped:
            return False
        if stripped.startswith(("={{", "{{")):
            return True
        try:
            return float(stripped) > 0
        except ValueError:
            return True
    return True


def _is_settings_lookup_node(node: dict[str, Any]) -> bool:
    name = str(node.get("name") or "")
    if SETTINGS_LOOKUP_NAME_RE.search(name):
        return True
    node_type = str(node.get("type") or "")
    if node_type.endswith(".postgres"):
        params = node.get("parameters") or {}
        query = params.get("query") or params.get("sql") or ""
        if isinstance(query, str) and re.search(r"\bsettings\b", query, re.IGNORECASE):
            return True
    return False


def has_literal_http_url(text: str) -> bool:
    """True when the string contains a literal http(s) URL.

    A parameter that is only an n8n expression ({{ ... }} or ={{ ... }})
    is allowed unless the expression itself contains http:// or https://.
    """
    if not LITERAL_HTTP_RE.search(text):
        return False
    match = EXPRESSION_ONLY_RE.fullmatch(text.strip())
    if match and not LITERAL_HTTP_RE.search(match.group(1)):
        return False
    return True


def _scan_hardcoded_urls(
    value: Any, node_label: str, path: str, issues: list[Issue]
) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _scan_hardcoded_urls(item, node_label, f"{path}.{key}", issues)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _scan_hardcoded_urls(item, node_label, f"{path}[{index}]", issues)
    elif isinstance(value, str) and has_literal_http_url(value):
        issues.append(
            Issue(path, f"node {node_label}: hardcoded http(s) URL in parameters")
        )


def _snippet_issues(node: dict[str, Any], path: str, snippets_dir: Path) -> list[Issue]:
    body = _code_body(node)
    first_line = body.splitlines()[0] if body else ""
    match = SNIPPET_FIRST_LINE_RE.match(first_line)
    if not match:
        return []
    name = match.group(1)
    snippet_path = snippets_dir / f"{name}.js"
    node_label = repr(node.get("name") or node.get("id") or "?")
    if ".." in name or "/" in name or "\\" in name:
        return [Issue(path, f"node {node_label}: invalid snippet name {name!r}")]
    if not snippet_path.is_file():
        return [
            Issue(
                path,
                f"node {node_label}: snippet {name!r} missing at {snippet_path}",
            )
        ]
    expected = snippet_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    actual = body.replace("\r\n", "\n")
    if actual != expected:
        return [
            Issue(
                path,
                f"node {node_label}: Code body differs from code-snippets/{name}.js",
            )
        ]
    return []


def lint_workflow(
    workflow: dict[str, Any],
    *,
    path: str = "<workflow>",
    snippets_dir: Path | None = None,
) -> list[Issue]:
    issues: list[Issue] = []
    snippets_dir = snippets_dir if snippets_dir is not None else SNIPPETS_DIR
    name = str(workflow.get("name") or "")

    if "pinData" in workflow:
        issues.append(Issue(path, "pinData is present"))

    settings = workflow.get("settings")
    if not isinstance(settings, dict):
        settings = {}
    error_workflow = settings.get("errorWorkflow")
    missing_error = error_workflow in (None, "", {}, [])
    if missing_error and "Error Handler" not in name:
        issues.append(Issue(path, "missing settings.errorWorkflow"))

    nodes = workflow.get("nodes")
    if not isinstance(nodes, list):
        nodes = []
    if len(nodes) > MAX_NODES:
        issues.append(Issue(path, f"more than {MAX_NODES} nodes ({len(nodes)} found)"))

    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        node_path = f"{path}.nodes[{index}]"
        node_name = str(node.get("name") or "")
        node_label = repr(node_name or node.get("id") or index)
        if "pinData" in node:
            issues.append(Issue(node_path, f"node {node_label}: pinData is present"))
        if DEFAULT_NODE_NAME_RE.fullmatch(node_name):
            issues.append(Issue(node_path, f"node {node_label}: default node name"))

        node_type = str(node.get("type") or "")
        if node_type in HTTP_REQUEST_TYPES and not _timeout_is_set(node):
            issues.append(
                Issue(
                    node_path,
                    f"node {node_label}: HTTP Request missing parameters.options.timeout",
                )
            )
        if node_type in CODE_TYPES:
            issues.extend(_snippet_issues(node, node_path, snippets_dir))

        if not _is_settings_lookup_node(node):
            params = node.get("parameters")
            if params is not None:
                _scan_hardcoded_urls(
                    params, node_label, f"{node_path}.parameters", issues
                )

    for match in find_secret_matches(workflow):
        issues.append(Issue(path, f"secret pattern matched: {match}"))

    return issues


def lint_document(
    document: Any,
    *,
    path: str = "<stdin>",
    snippets_dir: Path | None = None,
) -> list[Issue]:
    issues: list[Issue] = []
    found = False
    for suffix, workflow in _iter_workflows(document):
        found = True
        label = path if not suffix else f"{path}{suffix}"
        issues.extend(lint_workflow(workflow, path=label, snippets_dir=snippets_dir))
    if not found:
        issues.append(Issue(path, "expected a workflow object or a list of workflows"))
    return issues


def default_workflow_files(root: Path) -> list[Path]:
    files: list[Path] = []
    files.extend(sorted((root / "platform" / "workflows").glob("*.json")))
    files.extend(sorted(root.glob("projects/*/workflows/*.json")))
    return files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lint n8n workflow JSON")
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="Workflow JSON files (default: platform and project workflow dirs)",
    )
    parser.add_argument(
        "--dir",
        metavar="DIR",
        type=Path,
        help="Lint every *.json file under this directory",
    )
    parser.add_argument(
        "--snippets-dir",
        type=Path,
        default=SNIPPETS_DIR,
        help="Directory of code-snippets/<name>.js files",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    targets: list[Path] = list(args.files)
    if args.dir is not None:
        if not args.dir.is_dir():
            print(f"error: not a directory: {args.dir}", file=sys.stderr)
            return 2
        targets.extend(sorted(args.dir.rglob("*.json")))
    if not targets:
        targets = default_workflow_files(REPO_ROOT)

    if not targets:
        print("error: no workflow JSON files to lint", file=sys.stderr)
        return 2

    failed = 0
    for path in targets:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"{path}: cannot read JSON: {exc}", file=sys.stderr)
            failed = 1
            continue
        issues = lint_document(document, path=str(path), snippets_dir=args.snippets_dir)
        for issue in issues:
            print(issue, file=sys.stderr)
            failed = 1
    return failed


if __name__ == "__main__":
    raise SystemExit(main())
