"""Helpers for user-scoped temporary file uploads."""

import os
import uuid
from pathlib import Path

UPLOAD_ROOT = Path("/tmp/scholar_uploads")


def normalize_upload_id(upload_id: str) -> str:
    """Return a canonical UUID string for an upload identifier."""
    return str(uuid.UUID(upload_id))


def get_user_upload_dir(user_id: str) -> Path:
    """Return the upload directory for a Supabase user UUID."""
    safe_user_id = str(uuid.UUID(user_id))
    return UPLOAD_ROOT / safe_user_id


def get_pdf_upload_path(user_id: str, upload_id: str) -> Path:
    """Resolve a user-owned PDF upload ID to its internal temp-file path."""
    safe_upload_id = normalize_upload_id(upload_id)
    return get_user_upload_dir(user_id) / f"{safe_upload_id}.pdf"


def save_pdf_upload(user_id: str, contents: bytes) -> tuple[str, Path]:
    """Save PDF bytes and return the opaque upload ID plus internal path."""
    upload_id = str(uuid.uuid4())
    pdf_path = get_pdf_upload_path(user_id, upload_id)
    os.makedirs(pdf_path.parent, exist_ok=True)
    pdf_path.write_bytes(contents)
    return upload_id, pdf_path


def resolve_pdf_upload(user_id: str, upload_id: str) -> Path | None:
    """Return the internal PDF path if the upload exists for this user."""
    pdf_path = get_pdf_upload_path(user_id, upload_id)
    if not pdf_path.exists() or not pdf_path.is_file():
        return None
    return pdf_path
