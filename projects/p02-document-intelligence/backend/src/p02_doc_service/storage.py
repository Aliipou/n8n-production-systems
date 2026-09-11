"""Content-addressed file storage. Paths are relative to the volume root."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class Storage(Protocol):
    def put(self, digest: str, data: bytes) -> str: ...

    def get(self, storage_path: str) -> bytes: ...

    def exists(self, digest: str) -> bool: ...


class FilesystemStorage:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _abs(self, digest: str) -> Path:
        return self.root / digest[:2] / digest[2:4] / digest

    def put(self, digest: str, data: bytes) -> str:
        dest = self._abs(digest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            dest.write_bytes(data)
        return dest.relative_to(self.root).as_posix()

    def get(self, storage_path: str) -> bytes:
        root = self.root.resolve()
        path = (self.root / storage_path).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise FileNotFoundError(storage_path) from exc
        return path.read_bytes()

    def exists(self, digest: str) -> bool:
        return self._abs(digest).is_file()


class MemoryStorage:
    def __init__(self) -> None:
        self._files: dict[str, bytes] = {}

    def put(self, digest: str, data: bytes) -> str:
        self._files.setdefault(digest, data)
        return digest

    def get(self, storage_path: str) -> bytes:
        data = self._files.get(storage_path)
        if data is None:
            raise FileNotFoundError(storage_path)
        return data

    def exists(self, digest: str) -> bool:
        return digest in self._files
