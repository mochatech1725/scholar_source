"""Fetch accepted sources and extract clean text with failure isolation."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass

import httpx
from lxml import html as lxml_html
from pypdf import PdfReader

from backend.rag.config import RagSettings
from backend.rag.errors import ExtractionError
from backend.rag.hashing import sha256_text
from backend.rag.models import ExtractedDocument, ExtractionStatus, SourceRecord
from backend.rag.url_safety import HostResolver, UnsafeUrlError, resolve_host, validate_fetch_target

REMOVED_HTML_NODES = "//script | //style | //nav | //header | //footer | //noscript | //iframe"


@dataclass(frozen=True, slots=True)
class ExtractedContent:
    """Fetched text and media metadata reusable outside source ingestion."""

    text: str
    media_type: str
    title: str | None
    final_url: str


def clean_text(text: str) -> str:
    """Normalize whitespace and drop non-printable characters."""
    text = re.sub(r"[ \t]+", " ", text)
    # Keep blank lines so paragraph boundaries (\n\n) survive for chunking.
    text = "\n".join(line.strip() for line in text.splitlines())
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text_from_html(raw_html: str) -> str:
    """Strip boilerplate elements and return readable page text."""
    tree = lxml_html.fromstring(raw_html)
    for element in tree.xpath(REMOVED_HTML_NODES):
        element.drop_tree()
    return clean_text(tree.text_content())


def _failure_reason_for(error: Exception) -> str:
    """Map a fetch failure to a stable reason for run logs and debugging."""
    if isinstance(error, UnsafeUrlError):
        return "unsafe_url"
    if isinstance(error, ExtractionError):
        return "extraction_failed"
    return "fetch_or_parse_failed"


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes, preserving page order."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return clean_text("\n\n".join(pages))


class SourceExtractor:
    """Fetch a source and produce an ExtractedDocument, never raising.

    Per plan step 1.3.4 a single failed fetch must not crash the run, so
    failures come back as records with extraction_status=failed and an error
    message good enough to debug from (plan step 1.3.5).
    """

    def __init__(self, settings: RagSettings, *, resolver: HostResolver = resolve_host) -> None:
        self._settings = settings
        self._resolver = resolver

    def extract(self, source: SourceRecord) -> ExtractedDocument:
        if source.source_id is None:
            raise ExtractionError("Source must be persisted before extraction.")
        try:
            content = self.extract_url(source.url)
            text = content.text
        except Exception as error:  # noqa: BLE001 - isolate any fetch failure per 1.3.4
            failure_reason = _failure_reason_for(error)
            return self._failed(
                source,
                f"{type(error).__name__}: {error}",
                failure_reason=failure_reason,
                error_type=type(error).__name__,
            )

        if len(text) < self._settings.chunk_min_chars:
            return self._failed(
                source,
                "Page contained no usable text after cleaning.",
                failure_reason="no_usable_text",
                error_type="NoUsableText",
                metadata={"text_length": len(text)},
            )

        return ExtractedDocument(
            source_id=source.source_id,
            url=source.url,
            title=source.title,
            text=text,
            extracted_text_hash=sha256_text(text),
            extraction_status=ExtractionStatus.COMPLETED,
            metadata={"text_length": len(text)},
        )

    def _fetch_and_extract(self, source: SourceRecord) -> str:
        """Compatibility wrapper for callers that already have a source record."""

        return self.extract_url(source.url).text

    def extract_url(self, url: str) -> ExtractedContent:
        """Fetch one validated URL and detect HTML versus PDF content.

        The safety check runs here rather than at request validation because it
        resolves the host, and this is the single choke point every user-supplied
        fetch passes through. Redirect hops are still unchecked; plan step 0.6.2
        replaces `follow_redirects` with a validated hop loop.
        """

        validate_fetch_target(url, resolver=self._resolver)
        with httpx.Client(
            timeout=self._settings.fetch_timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "ScholarSourceBot/2.0 (+study resource finder)"},
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            if len(response.content) > self._settings.max_fetch_bytes:
                raise ExtractionError(f"Response exceeds {self._settings.max_fetch_bytes} bytes.")

            content_type = response.headers.get("content-type", "").casefold()
            final_url = str(response.url)
            if "pdf" in content_type or final_url.casefold().endswith(".pdf"):
                return ExtractedContent(
                    text=extract_text_from_pdf(response.content),
                    media_type="pdf",
                    title=None,
                    final_url=final_url,
                )

            tree = lxml_html.fromstring(response.text)
            title_nodes = tree.xpath("//title/text()")
            title = clean_text(title_nodes[0]) if title_nodes else None
            return ExtractedContent(
                text=extract_text_from_html(response.text),
                media_type="html",
                title=title or None,
                final_url=final_url,
            )

    def _failed(
        self,
        source: SourceRecord,
        error: str,
        *,
        failure_reason: str,
        error_type: str,
        metadata: dict | None = None,
    ) -> ExtractedDocument:
        failure_metadata = {
            "failure_reason": failure_reason,
            "error_type": error_type,
            "source_url": source.url,
            "normalized_url": source.normalized_url,
            "source_type": source.source_type,
            **(metadata or {}),
        }
        return ExtractedDocument(
            source_id=source.source_id,
            url=source.url,
            title=source.title,
            text="",
            extracted_text_hash=sha256_text(source.normalized_url),
            extraction_status=ExtractionStatus.FAILED,
            extraction_error=error[:500],
            metadata=failure_metadata,
        )
