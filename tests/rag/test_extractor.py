from uuid import uuid4

import httpx
import pytest

from backend.rag.config import RagSettings
from backend.rag.errors import ExtractionError
from backend.rag.extraction.extractor import (
    SourceExtractor,
    clean_text,
    extract_text_from_html,
    extract_text_from_pdf,
)
from backend.rag.models import ExtractionStatus, SourceRecord

SETTINGS = RagSettings()

READABLE_PARAGRAPH = (
    "Statics is the branch of mechanics that studies bodies in equilibrium. "
    "A body is in equilibrium when the resultant force and the resultant "
    "moment acting on it are both zero, which lets engineers solve for "
    "unknown reactions at supports and connections."
)

PAGE_HTML = f"""
<html>
  <head><title>Statics Notes</title><style>body {{ color: red; }}</style></head>
  <body>
    <nav>Home | Courses | About</nav>
    <script>console.log("tracking");</script>
    <main><p>{READABLE_PARAGRAPH}</p></main>
    <footer>Copyright 2026</footer>
  </body>
</html>
"""


def _source(url: str = "https://ocw.mit.edu/statics", *, persisted: bool = True) -> SourceRecord:
    return SourceRecord(
        source_id=uuid4() if persisted else None,
        url=url,
        normalized_url=url,
        title="Statics Notes",
        source_type="web_search",
    )


def _extractor_with(
    handler,
    monkeypatch: pytest.MonkeyPatch,
    settings: RagSettings = SETTINGS,
) -> SourceExtractor:
    """Build a SourceExtractor whose httpx.Client uses a mock transport."""
    real_client = httpx.Client

    def factory(**kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(**kwargs)

    monkeypatch.setattr("backend.rag.extraction.extractor.httpx.Client", factory)
    return SourceExtractor(settings)


def _minimal_pdf(text: str) -> bytes:
    """Build a one-page PDF containing the given text, with a valid xref."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R"
        b" /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_start = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n" + str(xref_start).encode() + b"\n%%EOF"
    return bytes(out)


def test_clean_text_normalizes_whitespace() -> None:
    raw = "First   line\t here  \n\n\n\n   Second line   \n"
    assert clean_text(raw) == "First line here\n\nSecond line"


def test_extract_text_from_html_strips_boilerplate() -> None:
    text = extract_text_from_html(PAGE_HTML)
    assert "bodies in equilibrium" in text
    assert "console.log" not in text
    assert "Home | Courses" not in text
    assert "Copyright 2026" not in text
    assert "color: red" not in text


def test_extract_text_from_pdf_reads_page_text() -> None:
    text = extract_text_from_pdf(_minimal_pdf("Statics is about equilibrium."))
    assert "Statics is about equilibrium." in text


def test_html_source_extracts_successfully(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=PAGE_HTML, headers={"content-type": "text/html"})

    source = _source()
    document = _extractor_with(handler, monkeypatch).extract(source)
    assert document.extraction_status is ExtractionStatus.COMPLETED
    assert "bodies in equilibrium" in document.text
    assert document.url == source.url
    assert document.title == source.title
    assert document.extracted_at is not None
    assert document.metadata["text_length"] == len(document.text)


def test_pdf_content_type_routes_to_pdf_extraction(monkeypatch: pytest.MonkeyPatch) -> None:
    padding = " It applies to trusses, frames, and machines in engineering practice."
    pdf_text = ("Statics is about equilibrium." + padding * 4).strip()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=_minimal_pdf(pdf_text),
            headers={"content-type": "application/pdf"},
        )

    document = _extractor_with(handler, monkeypatch).extract(_source())
    assert document.extraction_status is ExtractionStatus.COMPLETED
    assert "Statics is about equilibrium." in document.text


def test_fetch_failure_returns_failed_record_not_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    document = _extractor_with(handler, monkeypatch).extract(_source())
    assert document.extraction_status is ExtractionStatus.FAILED
    assert document.text == ""
    assert "ConnectError" in document.extraction_error
    assert document.metadata["failure_reason"] == "fetch_or_parse_failed"
    assert document.metadata["error_type"] == "ConnectError"
    assert document.metadata["source_url"] == document.url


def test_http_error_status_returns_failed_record(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found")

    document = _extractor_with(handler, monkeypatch).extract(_source())
    assert document.extraction_status is ExtractionStatus.FAILED
    assert "404" in document.extraction_error


def test_page_with_no_usable_text_is_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html><body><p>Too short.</p></body></html>")

    document = _extractor_with(handler, monkeypatch).extract(_source())
    assert document.extraction_status is ExtractionStatus.FAILED
    assert "no usable text" in document.extraction_error
    assert document.metadata["failure_reason"] == "no_usable_text"
    assert document.metadata["error_type"] == "NoUsableText"
    assert document.metadata["text_length"] == len("Too short.")


def test_oversized_response_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=PAGE_HTML)

    extractor = _extractor_with(handler, monkeypatch, RagSettings(max_fetch_bytes=10))
    document = extractor.extract(_source())
    assert document.extraction_status is ExtractionStatus.FAILED
    assert "exceeds 10 bytes" in document.extraction_error


def test_same_content_produces_same_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=PAGE_HTML, headers={"content-type": "text/html"})

    extractor = _extractor_with(handler, monkeypatch)
    first = extractor.extract(_source())
    second = extractor.extract(_source())
    assert first.extracted_text_hash == second.extracted_text_hash


def test_unpersisted_source_raises() -> None:
    with pytest.raises(ExtractionError, match="persisted before extraction"):
        SourceExtractor(SETTINGS).extract(_source(persisted=False))
