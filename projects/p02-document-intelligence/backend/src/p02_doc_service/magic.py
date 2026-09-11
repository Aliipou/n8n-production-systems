"""Detect PDF, PNG, and JPEG from magic bytes. Filename suffix must match."""

from __future__ import annotations

from pathlib import Path

MIME_PDF = "application/pdf"
MIME_PNG = "image/png"
MIME_JPEG = "image/jpeg"

PDF_MAGIC = b"%PDF"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"

_SUFFIX_TO_MIME = {
    ".pdf": MIME_PDF,
    ".png": MIME_PNG,
    ".jpg": MIME_JPEG,
    ".jpeg": MIME_JPEG,
}


def detect_mime(data: bytes) -> str | None:
    if data.startswith(PDF_MAGIC):
        return MIME_PDF
    if data.startswith(PNG_MAGIC):
        return MIME_PNG
    if data.startswith(JPEG_MAGIC):
        return MIME_JPEG
    return None


def filename_matches_mime(filename: str, mime: str) -> bool:
    suffix = Path(filename).name.lower()
    ext = Path(suffix).suffix
    expected = _SUFFIX_TO_MIME.get(ext)
    if expected is None:
        return True
    return expected == mime
