"""Fetch accepted sources and extract clean text with failure isolation."""

from __future__ import annotations

import io
import re

import httpx
from lxml import html as lxml_html
from pypdf import PdfReader

from backend.rag.config import RagSettings
from backend.rag.errors import ExtractionError
from backend.rag.hashing import sha256_text
from backend.rag.models import ExtractedDocument, ExtractionStatus, SourceRecord

REMOVED_HTML_NODES = "//script | //style | //nav | //header | //footer | //noscript | //iframe"


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

    def __init__(self, settings: RagSettings) -> None:
        self._settings = settings

    def extract(self, source: SourceRecord) -> ExtractedDocument:
        if source.source_id is None:
            raise ExtractionError("Source must be persisted before extraction.")
        try:
            text = self._fetch_and_extract(source)
        except Exception as error:  # noqa: BLE001 - isolate any fetch failure per 1.3.4
            failure_reason = "extraction_failed" if isinstance(error, ExtractionError) else "fetch_or_parse_failed"
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
        with httpx.Client(
            timeout=self._settings.fetch_timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "ScholarSourceBot/2.0 (+study resource finder)"},
        ) as client:
            response = client.get(source.url)
            response.raise_for_status()
            if len(response.content) > self._settings.max_fetch_bytes:
                raise ExtractionError(f"Response exceeds {self._settings.max_fetch_bytes} bytes.")

            content_type = response.headers.get("content-type", "").casefold()
            if "pdf" in content_type or source.url.casefold().endswith(".pdf"):
                return extract_text_from_pdf(response.content)
            return extract_text_from_html(response.text)

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
