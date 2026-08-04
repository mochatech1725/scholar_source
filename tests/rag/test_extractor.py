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
from backend.rag.url_safety import UnsafeUrlError

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


def _public_resolver(host: str, port: int) -> list[str]:
    """Resolve every test host to one public address, keeping tests off DNS."""
    return ["93.184.216.34"]


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
    return SourceExtractor(settings, resolver=_public_resolver)


class _ChunkedStream(httpx.SyncByteStream):
    """Serve a response body lazily so tests can count what was actually pulled."""

    def __init__(self, chunks) -> None:
        self._chunks = chunks

    def __iter__(self):
        return iter(self._chunks)


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


def test_extract_url_returns_detected_html_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=PAGE_HTML, headers={"content-type": "text/html"})

    content = _extractor_with(handler, monkeypatch).extract_url("https://ocw.mit.edu/statics")

    assert content.media_type == "html"
    assert content.title == "Statics Notes"
    assert content.final_url == "https://ocw.mit.edu/statics"
    assert "bodies in equilibrium" in content.text


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


def test_extract_url_detects_pdf_from_content_type(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=_minimal_pdf("Statics is about equilibrium."),
            headers={"content-type": "application/pdf"},
        )

    content = _extractor_with(handler, monkeypatch).extract_url("https://example.edu/download?id=1")

    assert content.media_type == "pdf"
    assert content.title is None
    assert "Statics is about equilibrium." in content.text


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


def test_oversized_body_stops_streaming_before_it_is_buffered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Plan step 0.6.3: the budget is enforced mid-stream, not after buffering."""
    yielded_chunks = 0

    def body_chunks():
        nonlocal yielded_chunks
        for _ in range(1000):
            yielded_chunks += 1
            yield b"x" * 1000

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=_ChunkedStream(body_chunks()))

    extractor = _extractor_with(handler, monkeypatch, RagSettings(max_fetch_bytes=2500))
    document = extractor.extract(_source())

    assert document.extraction_status is ExtractionStatus.FAILED
    assert "exceeds 2500 bytes" in document.extraction_error
    # Three 1000-byte chunks are enough to pass a 2500-byte budget; the rest of
    # the transfer must never be pulled.
    assert yielded_chunks == 3


def test_oversized_content_length_is_rejected_before_the_body_is_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    read_chunks = 0

    def body_chunks():
        nonlocal read_chunks
        read_chunks += 1
        yield b"x" * 50

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-length": "9999999"},
            stream=_ChunkedStream(body_chunks()),
        )

    extractor = _extractor_with(handler, monkeypatch, RagSettings(max_fetch_bytes=10))
    document = extractor.extract(_source())

    assert document.extraction_status is ExtractionStatus.FAILED
    assert "exceeds 10 bytes" in document.extraction_error
    assert read_chunks == 0


def test_same_content_produces_same_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=PAGE_HTML, headers={"content-type": "text/html"})

    extractor = _extractor_with(handler, monkeypatch)
    first = extractor.extract(_source())
    second = extractor.extract(_source())
    assert first.extracted_text_hash == second.extracted_text_hash


def test_cached_source_returns_same_extracted_content(monkeypatch: pytest.MonkeyPatch) -> None:
    cached_documents = {}
    fetch_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal fetch_count
        fetch_count += 1
        changed_html = PAGE_HTML.replace("bodies in equilibrium", "changed page content")
        html = PAGE_HTML if fetch_count == 1 else changed_html
        return httpx.Response(200, text=html, headers={"content-type": "text/html"})

    extractor = _extractor_with(handler, monkeypatch)
    source = _source()

    def cached_extract(source: SourceRecord):
        cached_document = cached_documents.get(source.normalized_url)
        if cached_document is not None:
            return cached_document.model_copy(deep=True)
        document = extractor.extract(source)
        cached_documents[source.normalized_url] = document
        return document

    first = cached_extract(source)
    second = cached_extract(source)

    assert fetch_count == 1
    assert second.extraction_status is ExtractionStatus.COMPLETED
    assert second.text == first.text
    assert second.extracted_text_hash == first.extracted_text_hash
    assert "changed page content" not in second.text


def test_unpersisted_source_raises() -> None:
    with pytest.raises(ExtractionError, match="persisted before extraction"):
        SourceExtractor(SETTINGS).extract(_source(persisted=False))


def test_internal_address_is_refused_before_any_request(monkeypatch: pytest.MonkeyPatch) -> None:
    """Plan step 0.6.1: an unsafe host must not reach the HTTP client at all."""
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(200, text=PAGE_HTML)

    extractor = _extractor_with(handler, monkeypatch)
    monkeypatch.setattr(extractor, "_resolver", lambda host, port: ["169.254.169.254"])

    with pytest.raises(UnsafeUrlError, match="non-public address"):
        extractor.extract_url("http://metadata.internal/latest/meta-data/")
    assert requested == []


def test_unsafe_url_is_isolated_as_a_failed_document(monkeypatch: pytest.MonkeyPatch) -> None:
    """A blocked source must not crash the run (plan step 1.3.4)."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=PAGE_HTML)

    extractor = _extractor_with(handler, monkeypatch)
    monkeypatch.setattr(extractor, "_resolver", lambda host, port: ["127.0.0.1"])

    document = extractor.extract(_source(url="http://localhost/admin"))

    assert document.extraction_status is ExtractionStatus.FAILED
    assert document.metadata["failure_reason"] == "unsafe_url"


def _resolver_for(hosts: dict[str, str]):
    """Resolve named hosts to fixed addresses, defaulting to a public one."""

    def resolver(host: str, port: int) -> list[str]:
        return [hosts.get(host, "93.184.216.34")]

    return resolver


def test_redirect_to_internal_address_is_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Plan step 0.6.2: each hop is validated, so a public host cannot bounce inward."""
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        if request.url.host == "ocw.mit.edu":
            return httpx.Response(302, headers={"location": "http://metadata.internal/latest/"})
        return httpx.Response(200, text=PAGE_HTML)

    extractor = _extractor_with(handler, monkeypatch)
    monkeypatch.setattr(extractor, "_resolver", _resolver_for({"metadata.internal": "169.254.169.254"}))

    with pytest.raises(UnsafeUrlError, match="non-public address"):
        extractor.extract_url("https://ocw.mit.edu/statics")

    assert requested == ["https://ocw.mit.edu/statics"]


def test_safe_redirect_is_followed_and_reports_final_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/statics":
            return httpx.Response(301, headers={"location": "/courses/statics/notes"})
        return httpx.Response(200, text=PAGE_HTML, headers={"content-type": "text/html"})

    content = _extractor_with(handler, monkeypatch).extract_url("https://ocw.mit.edu/statics")

    assert content.final_url == "https://ocw.mit.edu/courses/statics/notes"
    assert "bodies in equilibrium" in content.text


def test_redirect_loop_stops_at_the_hop_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    hops: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        hops.append(str(request.url))
        return httpx.Response(302, headers={"location": f"/hop{len(hops)}"})

    settings = RagSettings(max_redirect_hops=3)
    extractor = _extractor_with(handler, monkeypatch, settings)

    document = extractor.extract(_source())

    assert document.extraction_status is ExtractionStatus.FAILED
    assert "Exceeded 3 redirect hops" in document.extraction_error
    assert len(hops) == 4


def test_redirect_without_location_is_a_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302)

    document = _extractor_with(handler, monkeypatch).extract(_source())

    assert document.extraction_status is ExtractionStatus.FAILED
    assert "carried no location" in document.extraction_error
