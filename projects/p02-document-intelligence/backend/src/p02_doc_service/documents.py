"""Document metadata store. Insert on sha256 conflict returns the existing row."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Protocol
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row


@dataclass(frozen=True)
class NewDocument:
    sha256: str
    original_filename: str
    mime_type: str
    size_bytes: int
    storage_path: str
    source: str = "upload"


@dataclass(frozen=True)
class StoredDocument:
    id: UUID
    sha256: str
    original_filename: str
    mime_type: str
    size_bytes: int
    storage_path: str
    source: str
    status: str
    deduplicated: bool


class DocumentRepository(Protocol):
    def put(self, document: NewDocument) -> StoredDocument: ...

    def get(self, document_id: UUID) -> StoredDocument | None: ...


class MemoryDocuments:
    def __init__(self) -> None:
        self._by_id: dict[UUID, StoredDocument] = {}
        self._by_hash: dict[str, UUID] = {}
        self._lock = Lock()

    def put(self, document: NewDocument) -> StoredDocument:
        with self._lock:
            existing_id = self._by_hash.get(document.sha256)
            if existing_id is not None:
                current = self._by_id[existing_id]
                return StoredDocument(
                    id=current.id,
                    sha256=current.sha256,
                    original_filename=current.original_filename,
                    mime_type=current.mime_type,
                    size_bytes=current.size_bytes,
                    storage_path=current.storage_path,
                    source=current.source,
                    status=current.status,
                    deduplicated=True,
                )
            stored = StoredDocument(
                id=uuid4(),
                sha256=document.sha256,
                original_filename=document.original_filename,
                mime_type=document.mime_type,
                size_bytes=document.size_bytes,
                storage_path=document.storage_path,
                source=document.source,
                status="received",
                deduplicated=False,
            )
            self._by_id[stored.id] = stored
            self._by_hash[stored.sha256] = stored.id
            return stored

    def get(self, document_id: UUID) -> StoredDocument | None:
        return self._by_id.get(document_id)


_RETURNING = """
id, sha256, original_filename, mime_type, size_bytes, storage_path, source, status
"""


class PostgresDocuments:
    def __init__(self, database_url: str) -> None:
        self._url = database_url

    def put(self, document: NewDocument) -> StoredDocument:
        with psycopg.connect(self._url) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    f"""
                    INSERT INTO p02.documents (
                        sha256, original_filename, mime_type, size_bytes,
                        storage_path, source, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, 'received')
                    ON CONFLICT (sha256) DO NOTHING
                    RETURNING {_RETURNING}
                    """,
                    (
                        document.sha256,
                        document.original_filename,
                        document.mime_type,
                        document.size_bytes,
                        document.storage_path,
                        document.source,
                    ),
                )
                row = cur.fetchone()
                deduplicated = row is None
                if row is None:
                    cur.execute(
                        f"SELECT {_RETURNING} FROM p02.documents WHERE sha256 = %s",
                        (document.sha256,),
                    )
                    row = cur.fetchone()
                if row is None:
                    msg = "document insert conflicted but no row for sha256"
                    raise RuntimeError(msg)
                conn.commit()
                return _from_row(row, deduplicated=deduplicated)

    def get(self, document_id: UUID) -> StoredDocument | None:
        with psycopg.connect(self._url) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    f"SELECT {_RETURNING} FROM p02.documents WHERE id = %s",
                    (document_id,),
                )
                row = cur.fetchone()
        if row is None:
            return None
        return _from_row(row, deduplicated=False)


def _from_row(row: dict[str, object], *, deduplicated: bool) -> StoredDocument:
    raw_size = row["size_bytes"]
    if isinstance(raw_size, bool) or not isinstance(raw_size, int):
        size_bytes = int(str(raw_size))
    else:
        size_bytes = raw_size
    return StoredDocument(
        id=row["id"] if isinstance(row["id"], UUID) else UUID(str(row["id"])),
        sha256=str(row["sha256"]),
        original_filename=str(row["original_filename"]),
        mime_type=str(row["mime_type"]),
        size_bytes=size_bytes,
        storage_path=str(row["storage_path"]),
        source=str(row["source"]),
        status=str(row["status"]),
        deduplicated=deduplicated,
    )
