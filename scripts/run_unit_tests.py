#!/usr/bin/env python3
"""Run Python, Go, and snippet unit tests. Used by `make test` / `make check`."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PYTEST_DIRS = (
    ROOT / "scripts" / "tests",
    ROOT / "platform" / "libs" / "python",
    ROOT / "platform" / "db" / "tests",
    ROOT / "platform" / "services" / "mock-llm",
    ROOT / "platform" / "services" / "review-ui",
    ROOT / "projects" / "p01-lead-qualification" / "backend",
    ROOT / "projects" / "p02-document-intelligence" / "backend",
)

GO_DIRS = (
    ROOT / "platform" / "services" / "flaky-api",
    ROOT / "projects" / "p03-webhook-gateway",
)


def _run(cmd: list[str], cwd: Path) -> int:
    print(f"+ {' '.join(cmd)}  (cwd={cwd})", flush=True)
    proc = subprocess.run(cmd, cwd=cwd, check=False)
    return int(proc.returncode)


def _go_bin() -> str | None:
    found = shutil.which("go")
    if found:
        return found
    win = Path(r"C:\Program Files\Go\bin\go.exe")
    if win.is_file():
        return str(win)
    return None


def main() -> int:
    python = sys.executable
    status = 0

    for path in PYTEST_DIRS:
        if not path.is_dir():
            print(f"skip missing {path}", flush=True)
            continue
        tests = list(path.glob("test_*.py")) + list(path.glob("**/test_*.py"))
        if path.name == "tests" and not any(tests):
            continue
        code = _run([python, "-m", "pytest", "-q"], cwd=path)
        if code != 0:
            status = code

    go = _go_bin()
    if go is None:
        print("skip Go tests: go not on PATH", flush=True)
    else:
        env = os.environ.copy()
        gobin = str(Path(go).parent)
        env["PATH"] = gobin + os.pathsep + env.get("PATH", "")
        for path in GO_DIRS:
            if not (path / "go.mod").is_file():
                continue
            print(f"+ {go} test -race ./...  (cwd={path})", flush=True)
            proc = subprocess.run([go, "test", "-race", "./..."], cwd=path, check=False, env=env)
            if proc.returncode != 0:
                status = int(proc.returncode)

    snippets = ROOT / "code-snippets"
    if (snippets / "package.json").is_file():
        npm = shutil.which("npm")
        if npm is None:
            print("skip snippet tests: npm not on PATH", flush=True)
        else:
            if not (snippets / "node_modules").is_dir():
                install = _run([npm, "ci"], cwd=snippets)
                if install != 0:
                    status = install
            code = _run([npm, "test"], cwd=snippets)
            if code != 0:
                status = code

    return status


if __name__ == "__main__":
    raise SystemExit(main())
