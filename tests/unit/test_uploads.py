"""
Unit tests for upload helper functions.
"""

import pytest

from backend import uploads

USER_ID = "123e4567-e89b-12d3-a456-426614174000"


def test_save_pdf_upload_returns_opaque_id_and_internal_path(tmp_path, monkeypatch):
    """PDF uploads should be addressable by opaque ID, not by public path."""
    monkeypatch.setattr(uploads, "UPLOAD_ROOT", tmp_path)

    upload_id, pdf_path = uploads.save_pdf_upload(USER_ID, b"%PDF-1.7\n")

    assert uploads.normalize_upload_id(upload_id) == upload_id
    assert pdf_path == tmp_path / USER_ID / f"{upload_id}.pdf"
    assert pdf_path.read_bytes() == b"%PDF-1.7\n"


def test_resolve_pdf_upload_is_user_scoped(tmp_path, monkeypatch):
    """Upload IDs should resolve only within the owning user's directory."""
    monkeypatch.setattr(uploads, "UPLOAD_ROOT", tmp_path)
    upload_id, pdf_path = uploads.save_pdf_upload(USER_ID, b"%PDF-1.7\n")

    assert uploads.resolve_pdf_upload(USER_ID, upload_id) == pdf_path
    assert uploads.resolve_pdf_upload("999e9999-e99b-99d9-a999-999999999999", upload_id) is None


def test_invalid_upload_id_rejected():
    """Upload IDs should not allow paths or arbitrary strings."""
    with pytest.raises(ValueError):
        uploads.get_pdf_upload_path(USER_ID, "../secret.pdf")


def test_invalid_user_id_rejected():
    """User-scoped paths should require UUID user IDs."""
    with pytest.raises(ValueError):
        uploads.get_user_upload_dir("../../etc")
