from __future__ import annotations

import shutil
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture
def workdir() -> Iterator[Path]:
    """Local scratch dir. pytest tmp_path hits WinError 5 on this machine."""
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
