"""Tests for authenticated uploaded-PDF normalization."""

from __future__ import annotations

import io
from pathlib import Path
from uuid import uuid4

import pytest
from pypdf import PdfWriter

from backend.models import CourseInputRequest
from backend.rag.config import DEFAULT_SETTINGS, RagSettings
from backend.rag.errors import UploadedPdfNormalizationError
from backend.rag.input_adapters import AdapterDispatcher, UploadedPdfAdapter
from backend.rag.input_adapters.uploaded_pdf import UPLOAD_CONTEXT_WARNING
from backend.rag.input_adapters.url_page import LearningOutline
from backend.rag.models import LearningInputKind, NormalizedLearningField, ProvenanceOrigin


class StubOutlineDeriver:
    def __init__(self) -> None:
        self.text = ""
        self.source_url = ""

    def derive(self, *, text: str, source_url: str, media_type: str) -> LearningOutline:
        self.text = text
        self.source_url = source_url
        assert media_type == "pdf"
        return LearningOutline(
            title="Engineering Mechanics",
            author="Ada Author",
            subject="Statics",
            topics=["Equilibrium", "Free-body diagrams"],
            chapters=["Forces"],
            sections=["Moments"],
            confidence=0.9,
        )


def _minimal_pdf(text: str) -> bytes:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
        ),
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(output)


def _owned_request(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, contents: bytes) -> CourseInputRequest:
    upload_id = str(uuid4())
    user_id = str(uuid4())
    pdf_path = tmp_path / user_id / f"{upload_id}.pdf"
    pdf_path.parent.mkdir()
    pdf_path.write_bytes(contents)
    monkeypatch.setattr("backend.rag.input_adapters.uploaded_pdf.UPLOAD_ROOT", tmp_path)
    return CourseInputRequest(book_upload_id=upload_id, book_pdf_path=str(pdf_path))


def test_uploaded_pdf_adapter_preserves_page_and_upload_provenance(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    request = _owned_request(monkeypatch, tmp_path, _minimal_pdf("Statics studies equilibrium and moments."))
    deriver = StubOutlineDeriver()
    adapter = UploadedPdfAdapter(settings=DEFAULT_SETTINGS, outline_deriver=deriver)

    result = adapter.normalize(request)

    assert result.input_kind is LearningInputKind.UPLOADED_PDF
    assert result.canonical_identifier == f"upload:{request.book_upload_id}"
    assert "[Page 1]" in deriver.text
    assert deriver.source_url == f"upload:{request.book_upload_id}#pages=1"
    assert result.field_provenance[NormalizedLearningField.TOPICS].source_reference.endswith("#pages=1")
    assert result.field_provenance[NormalizedLearningField.TOPICS].origin is ProvenanceOrigin.EXTRACTED_CONTENT
    assert result.warnings == [UPLOAD_CONTEXT_WARNING]


def test_uploaded_pdf_adapter_preserves_explicit_context_and_dispatches(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    request = _owned_request(monkeypatch, tmp_path, _minimal_pdf("Algorithms and data structures."))
    request.book_title = "User title"
    request.chapter = "Chapter 2"
    adapter = UploadedPdfAdapter(settings=DEFAULT_SETTINGS, outline_deriver=StubOutlineDeriver())

    result = AdapterDispatcher({LearningInputKind.UPLOADED_PDF: adapter}).dispatch(request)

    assert result.title == "User title"
    assert result.chapters == ["Chapter 2", "Forces"]
    assert result.field_provenance[NormalizedLearningField.TITLE].origin is ProvenanceOrigin.USER_INPUT


@pytest.mark.parametrize(
    ("contents", "expected_code"),
    [
        (b"not a pdf", "invalid_file_type"),
        (b"%PDF-corrupt", "corrupt_pdf"),
    ],
)
def test_uploaded_pdf_adapter_rejects_invalid_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    contents: bytes,
    expected_code: str,
) -> None:
    request = _owned_request(monkeypatch, tmp_path, contents)
    adapter = UploadedPdfAdapter(settings=DEFAULT_SETTINGS, outline_deriver=StubOutlineDeriver())

    with pytest.raises(UploadedPdfNormalizationError) as error:
        adapter.normalize(request)

    assert error.value.code == expected_code


def test_uploaded_pdf_adapter_rejects_encrypted_pdf(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.encrypt("secret")
    output = io.BytesIO()
    writer.write(output)
    request = _owned_request(monkeypatch, tmp_path, output.getvalue())

    with pytest.raises(UploadedPdfNormalizationError) as error:
        UploadedPdfAdapter(settings=DEFAULT_SETTINGS, outline_deriver=StubOutlineDeriver()).normalize(request)

    assert error.value.code == "encrypted_pdf"


def test_uploaded_pdf_adapter_reports_ocr_requirement_for_image_only_pdf(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    output = io.BytesIO()
    writer.write(output)
    request = _owned_request(monkeypatch, tmp_path, output.getvalue())

    with pytest.raises(UploadedPdfNormalizationError) as error:
        UploadedPdfAdapter(settings=DEFAULT_SETTINGS, outline_deriver=StubOutlineDeriver()).normalize(request)

    assert error.value.code == "ocr_required"
    assert "OCR is not configured" in str(error.value)


def test_uploaded_pdf_adapter_rejects_path_that_does_not_match_owned_upload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    request = _owned_request(monkeypatch, tmp_path, _minimal_pdf("Readable text"))
    request.book_upload_id = str(uuid4())

    with pytest.raises(UploadedPdfNormalizationError) as error:
        UploadedPdfAdapter(settings=DEFAULT_SETTINGS, outline_deriver=StubOutlineDeriver()).normalize(request)

    assert error.value.code == "upload_ownership_invalid"


def test_uploaded_pdf_adapter_enforces_configured_size_limit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    request = _owned_request(monkeypatch, tmp_path, _minimal_pdf("Readable text"))
    settings = RagSettings(max_upload_pdf_bytes=10)

    with pytest.raises(UploadedPdfNormalizationError) as error:
        UploadedPdfAdapter(settings=settings, outline_deriver=StubOutlineDeriver()).normalize(request)

    assert error.value.code == "file_too_large"
