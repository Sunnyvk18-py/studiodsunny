"""Local filesystem storage for HQ file assets (S3 later)."""

from __future__ import annotations

import re
from pathlib import Path
from uuid import UUID, uuid4

from app.core.config import settings

SAFE_NAME = re.compile(r"[^A-Za-z0-9._\- ]+")
MAX_UPLOAD_BYTES = 25 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".zip",
    ".pptx",
}


def upload_root() -> Path:
    root = Path(settings.upload_dir)
    if not root.is_absolute():
        root = Path.cwd() / root
    root.mkdir(parents=True, exist_ok=True)
    return root


def sanitize_filename(name: str) -> str:
    cleaned = SAFE_NAME.sub("", (name or "file").strip()) or "file"
    return cleaned[:200]


def extension_allowed(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def build_storage_key(org_id: UUID, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return f"{org_id}/{uuid4().hex}{ext}"


def absolute_path(storage_key: str) -> Path:
    path = upload_root() / storage_key
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_bytes(storage_key: str, data: bytes) -> int:
    path = absolute_path(storage_key)
    path.write_bytes(data)
    return len(data)


def read_path(storage_key: str) -> Path:
    path = absolute_path(storage_key)
    if not path.exists():
        raise FileNotFoundError(storage_key)
    return path


def delete_file(storage_key: str) -> None:
    path = absolute_path(storage_key)
    if path.exists():
        path.unlink()
