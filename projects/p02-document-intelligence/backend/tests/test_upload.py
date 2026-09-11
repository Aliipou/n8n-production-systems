"""Upload magic bytes, 10 MB cap, sha256 dedupe. Synthetic files only, not invoices."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from p02_doc_service.documents import MemoryDocuments, NewDocument
from p02_doc_service.magic import PNG_MAGIC, detect_mime, filename_matches_mime
from p02_doc_service.main import MAX_UPLOAD_BYTES, create_app
from p02_doc_service.storage import MemoryStorage

PDF_BYTES = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
PNG_BYTES = PNG_MAGIC + b"\x00\x00\x00\rIHDR" + b"\x00" * 16
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 20
TOKEN = "test-token"


class RecordingIntake:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def notify(self, document_id: str, sha256: str) -> None:
        self.calls.append((document_id, sha256))


@pytest.fixture
def intake() -> RecordingIntake:
    return RecordingIntake()


@pytest.fixture
def client(intake: RecordingIntake) -> Iterator[TestClient]:
    app = create_app(
        internal_api_token=TOKEN,
        storage=MemoryStorage(),
        documents=MemoryDocuments(),
        intake=intake,
    )
    with TestClient(app) as test_client:
        yield test_client


def _headers() -> dict[str, str]:
    return {"INTERNAL_API_TOKEN": TOKEN}


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_unauthorized(client: TestClient) -> None:
    response = client.post(
        "/v1/documents",
        files={"file": ("note.pdf", PDF_BYTES, "application/pdf")},
    )
    assert response.status_code == 401


def test_magic_bytes_pdf_ok(client: TestClient) -> None:
    response = client.post(
        "/v1/documents",
        files={"file": ("scan.pdf", PDF_BYTES, "application/octet-stream")},
        headers=_headers(),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["mime_type"] == "application/pdf"
    assert body["deduplicated"] is False
    assert body["sha256"] == hashlib.sha256(PDF_BYTES).hexdigest()


def test_magic_bytes_png_and_jpeg(client: TestClient) -> None:
    png = client.post(
        "/v1/documents",
        files={"file": ("page.png", PNG_BYTES, "image/png")},
        headers=_headers(),
    )
    jpeg = client.post(
        "/v1/documents",
        files={"file": ("page.jpg", JPEG_BYTES, "image/jpeg")},
        headers=_headers(),
    )
    assert png.status_code == 201
    assert jpeg.status_code == 201
    assert png.json()["mime_type"] == "image/png"
    assert jpeg.json()["mime_type"] == "image/jpeg"


def test_magic_bytes_pdf_extension_other_content(client: TestClient) -> None:
    response = client.post(
        "/v1/documents",
        files={"file": ("invoice.pdf", PNG_BYTES, "application/pdf")},
        headers=_headers(),
    )
    assert response.status_code == 415
    assert response.json()["detail"] == "magic_mismatch"


def test_magic_bytes_plain_text(client: TestClient) -> None:
    response = client.post(
        "/v1/documents",
        files={"file": ("note.pdf", b"not a pdf", "application/pdf")},
        headers=_headers(),
    )
    assert response.status_code == 415
    assert response.json()["detail"] == "unsupported_type"


def test_same_file_dedupe(client: TestClient, intake: RecordingIntake) -> None:
    first = client.post(
        "/v1/documents",
        files={"file": ("a.pdf", PDF_BYTES, "application/pdf")},
        headers=_headers(),
    )
    second = client.post(
        "/v1/documents",
        files={"file": ("b.pdf", PDF_BYTES, "application/pdf")},
        headers=_headers(),
    )
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["document_id"] == second.json()["document_id"]
    assert second.json()["deduplicated"] is True
    assert len(intake.calls) == 1


def test_empty_file(client: TestClient) -> None:
    response = client.post(
        "/v1/documents",
        files={"file": ("empty.pdf", b"", "application/pdf")},
        headers=_headers(),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "empty_file"


def test_file_too_large(client: TestClient) -> None:
    payload = b"%PDF" + b"\x00" * (MAX_UPLOAD_BYTES - 3)
    response = client.post(
        "/v1/documents",
        files={"file": ("big.pdf", payload, "application/pdf")},
        headers=_headers(),
    )
    assert response.status_code == 413
    assert response.json()["detail"] == "file_too_large"


def test_get_file_roundtrip(client: TestClient) -> None:
    uploaded = client.post(
        "/v1/documents",
        files={"file": ("scan.pdf", PDF_BYTES, "application/pdf")},
        headers=_headers(),
    )
    document_id = uploaded.json()["document_id"]
    fetched = client.get(f"/v1/documents/{document_id}/file", headers=_headers())
    assert fetched.status_code == 200
    assert fetched.content == PDF_BYTES
    assert fetched.headers["content-type"].startswith("application/pdf")


def test_get_file_missing(client: TestClient) -> None:
    response = client.get(
        "/v1/documents/00000000-0000-4000-8000-000000000000/file",
        headers=_headers(),
    )
    assert response.status_code == 404


def test_memory_documents_concurrent_same_hash() -> None:
    repo = MemoryDocuments()
    payload = NewDocument(
        sha256="a" * 64,
        original_filename="scan.pdf",
        mime_type="application/pdf",
        size_bytes=12,
        storage_path="aa/aa/" + "a" * 64,
    )

    def _put() -> UUID:
        return repo.put(payload).id

    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(lambda _: _put(), range(16)))
    assert len(set(ids)) == 1


def test_detect_mime_helpers() -> None:
    assert detect_mime(PDF_BYTES) == "application/pdf"
    assert detect_mime(PNG_BYTES) == "image/png"
    assert detect_mime(JPEG_BYTES) == "image/jpeg"
    assert detect_mime(b"hello") is None
    assert filename_matches_mime("scan.pdf", "application/pdf") is True
    assert filename_matches_mime("scan.pdf", "image/png") is False
    assert filename_matches_mime("noext", "application/pdf") is True
