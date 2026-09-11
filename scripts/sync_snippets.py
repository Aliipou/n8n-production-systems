#!/usr/bin/env python3
"""Copy code-snippets/<name>.js into Code nodes marked // snippet: <name>.

PLT-T07 / spec 00 section 7. Replaces the entire Code node body with the
file contents. The snippet file should itself start with // snippet: <name>
so lint_workflows.py continues to treat the node as snippet-backed.

CLI:
  python scripts/sync_snippets.py                 # default workflow dirs
  python scripts/sync_snippets.py file.json ...
  python scripts/sync_snippets.py --in-place DIR
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from sanitize_workflows import dumps_stable  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
SNIPPETS_DIR = REPO_ROOT / "code-snippets"
SNIPPET_FIRST_LINE_RE = re.compile(r"^// snippet:\s*([A-Za-z0-9_.-]+)\s*$")
CODE_BODY_KEYS = ("jsCode", "pythonCode", "functionCode", "code")
CODE_TYPES = frozenset({"n8n-nodes-base.code"})


class SyncError(Exception):
    """A Code node snippet could not be synchronized."""


def _code_key(parameters: dict[str, Any]) -> str | None:
    for key in CODE_BODY_KEYS:
        if isinstance(parameters.get(key), str):
            return key
    return None


def sync_workflow(
    workflow: dict[str, Any],
    *,
    snippets_dir: Path,
    path: str = "<workflow>",
) -> int:
    """Replace snippet-backed Code bodies. Returns the number of nodes updated."""
    nodes = workflow.get("nodes")
    if not isinstance(nodes, list):
        return 0
    updated = 0
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        if str(node.get("type") or "") not in CODE_TYPES:
            continue
        parameters = node.get("parameters")
        if not isinstance(parameters, dict):
            continue
        key = _code_key(parameters)
        if key is None:
            continue
        body = parameters[key]
        first_line = body.splitlines()[0] if body else ""
        match = SNIPPET_FIRST_LINE_RE.match(first_line)
        if not match:
            continue
        name = match.group(1)
        node_label = node.get("name") or node.get("id") or index
        if ".." in name or "/" in name or "\\" in name:
            raise SyncError(
                f"{path} node {node_label!r}: invalid snippet name {name!r}"
            )
        snippet_path = snippets_dir / f"{name}.js"
        if not snippet_path.is_file():
            raise SyncError(
                f"{path} node {node_label!r}: snippet file missing: {snippet_path}"
            )
        replacement = snippet_path.read_text(encoding="utf-8").replace("\r\n", "\n")
        if not replacement.endswith("\n") and replacement:
            replacement += "\n"
        current = body.replace("\r\n", "\n")
        if current != replacement:
            parameters[key] = replacement
            updated += 1
    return updated


def sync_document(
    document: Any,
    *,
    snippets_dir: Path,
    path: str = "<stdin>",
) -> tuple[Any, int]:
    updated = 0
    if isinstance(document, dict):
        updated += sync_workflow(document, snippets_dir=snippets_dir, path=path)
        return document, updated
    if isinstance(document, list):
        for index, item in enumerate(document):
            if isinstance(item, dict):
                updated += sync_workflow(
                    item, snippets_dir=snippets_dir, path=f"{path}[{index}]"
                )
        return document, updated
    raise SyncError(f"{path}: expected a workflow object or a list of workflows")


def default_workflow_files(root: Path) -> list[Path]:
    files: list[Path] = []
    files.extend(sorted((root / "platform" / "workflows").glob("*.json")))
    files.extend(sorted(root.glob("projects/*/workflows/*.json")))
    return files


def process_file(path: Path, snippets_dir: Path) -> int:
    document = json.loads(path.read_text(encoding="utf-8"))
    document, updated = sync_document(
        document, snippets_dir=snippets_dir, path=str(path)
    )
    path.write_text(dumps_stable(document), encoding="utf-8", newline="\n")
    return updated


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Copy code-snippets into n8n Code nodes"
    )
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument("--in-place", metavar="DIR", type=Path)
    parser.add_argument("--snippets-dir", type=Path, default=SNIPPETS_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    targets: list[Path] = list(args.files)
    if args.in_place is not None:
        if not args.in_place.is_dir():
            print(f"error: not a directory: {args.in_place}", file=sys.stderr)
            return 2
        targets.extend(sorted(args.in_place.rglob("*.json")))
    if not targets:
        targets = default_workflow_files(REPO_ROOT)

    if not targets:
        print("error: no workflow JSON files to sync", file=sys.stderr)
        return 2

    failed = 0
    total = 0
    for path in targets:
        try:
            total += process_file(path, args.snippets_dir)
        except (OSError, json.JSONDecodeError, SyncError) as exc:
            print(f"error: {path}: {exc}", file=sys.stderr)
            failed = 1
    if failed:
        return 1
    print(f"updated {total} Code node(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
