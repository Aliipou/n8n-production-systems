#!/usr/bin/env python3
"""Sanitize n8n workflow JSON for version control (PLT-T07 / spec 00 section 7).

Removes pinData, staticData, meta.instanceId, and execution references.
Sorts keys, writes 2-space indent, and ends with a trailing newline.

Fails if any string matches secret patterns (gitleaks-like high-confidence
rules, plus sk-, xox, Bearer + long token, and private key headers).

CLI:
  python scripts/sanitize_workflows.py                 # stdin -> stdout
  python scripts/sanitize_workflows.py file.json ...   # rewrite files
  python scripts/sanitize_workflows.py --in-place DIR  # rewrite *.json under DIR
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Keys dropped at any depth. settings.executionOrder is kept (not in this set).
_DROP_KEYS = frozenset(
    {
        "pinData",
        "staticData",
        "executionId",
        "executionIds",
        "lastExecution",
        "lastExecutionStatus",
    }
)

# High-confidence secret patterns. Not a full gitleaks clone.
# Placeholders such as ${INTERNAL_API_TOKEN} do not match (no $ or { in token class).
_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "private-key-header",
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ),
    (
        "aws-access-key",
        re.compile(
            r"\b(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}\b"
        ),
    ),
    (
        "github-pat",
        re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36}\b"),
    ),
    (
        "github-fine-grained",
        re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    ),
    (
        "gitlab-pat",
        re.compile(r"\bglpat-[A-Za-z0-9_\-]{20,}\b"),
    ),
    (
        "stripe-key",
        re.compile(r"\b(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{16,}\b"),
    ),
    (
        "openai-sk",
        re.compile(r"\bsk-[A-Za-z0-9]{16,}\b"),
    ),
    (
        "slack-xox",
        re.compile(r"\bxox[baprs]-[\w-]{10,}\b", re.IGNORECASE),
    ),
    (
        "bearer-token",
        re.compile(r"\bBearer\s+[A-Za-z0-9._\-+=/]{24,}"),
    ),
]


class SanitizeError(Exception):
    """Workflow JSON failed sanitizer checks."""


def collect_strings(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, str):
        found.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            found.extend(collect_strings(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(collect_strings(item))
    return found


def find_secret_matches(value: Any) -> list[str]:
    """Return human-readable match descriptions. Never echoes the full secret."""
    hits: list[str] = []
    seen: set[str] = set()
    for text in collect_strings(value):
        for name, pattern in _SECRET_PATTERNS:
            if pattern.search(text):
                key = f"{name}:{text[:12]}"
                if key in seen:
                    continue
                seen.add(key)
                hits.append(f"{name} (string starts with {text[:12]!r}...)")
    return hits


def _strip(value: Any, path: str = "") -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            child_path = f"{path}.{key}" if path else key
            if key in _DROP_KEYS:
                continue
            if key == "instanceId" and (path == "meta" or path.endswith(".meta")):
                continue
            if key == "execution" and not isinstance(item, str):
                continue
            out[key] = _strip(item, child_path)
        return out
    if isinstance(value, list):
        return [_strip(item, path) for item in value]
    return value


def dumps_stable(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sanitize_document(value: Any) -> Any:
    matches = find_secret_matches(value)
    if matches:
        raise SanitizeError("secret pattern(s) matched: " + "; ".join(matches))
    return _strip(value)


def load_json_text(text: str) -> Any:
    return json.loads(text)


def process_text(text: str) -> str:
    return dumps_stable(sanitize_document(load_json_text(text)))


def iter_json_files(directory: Path) -> list[Path]:
    return sorted(path for path in directory.rglob("*.json") if path.is_file())


def process_file(path: Path) -> bool:
    """Rewrite path. Return True if the file content changed."""
    original = path.read_text(encoding="utf-8")
    updated = process_text(original)
    if updated != original:
        path.write_text(updated, encoding="utf-8", newline="\n")
        return True
    return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sanitize n8n workflow JSON")
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="Workflow JSON files to rewrite in place",
    )
    parser.add_argument(
        "--in-place",
        metavar="DIR",
        type=Path,
        help="Rewrite every *.json file under this directory",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    targets: list[Path] = list(args.files)
    if args.in_place is not None:
        directory = args.in_place
        if not directory.is_dir():
            print(f"error: not a directory: {directory}", file=sys.stderr)
            return 2
        targets.extend(iter_json_files(directory))

    if not targets:
        try:
            sys.stdout.write(process_text(sys.stdin.read()))
        except json.JSONDecodeError as exc:
            print(f"error: invalid JSON: {exc}", file=sys.stderr)
            return 2
        except SanitizeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        return 0

    failed = 0
    for path in targets:
        try:
            process_file(path)
        except json.JSONDecodeError as exc:
            print(f"error: {path}: invalid JSON: {exc}", file=sys.stderr)
            failed = 1
        except SanitizeError as exc:
            print(f"error: {path}: {exc}", file=sys.stderr)
            failed = 1
        except OSError as exc:
            print(f"error: {path}: {exc}", file=sys.stderr)
            failed = 1
    return failed


if __name__ == "__main__":
    raise SystemExit(main())
