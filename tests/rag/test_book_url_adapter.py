"""Tests for book-URL normalization."""

from dataclasses import dataclass

import pytest

from backend.models import CourseInputRequest
from backend.rag.config import DEFAULT_SETTINGS, RagSettings
from backend.rag.errors import InputNormalizationError
from backend.rag.extraction.extractor import ExtractedContent
from backend.rag.input_adapters import AdapterDispatcher, BookUrlAdapter
from backend.rag.input_adapters.book_url import BOOK_CONTEXT_WARNING, DIRECT_PDF_WARNING
from backend.rag.input_adapters.url_page import LearningOutline
from backend.rag.models import LearningInputKind, NormalizedLearningField, ProvenanceOrigin


@dataclass
class StubExtractor:
    content: ExtractedContent | None = None
    error: Exception | None = None

    def extract_url(self, url: str) -> ExtractedContent:
        if self.error:
            raise self.error
        assert self.content is not None
        return self.content


@dataclass
class StubOutlineDeriver:
    outline: LearningOutline
    received_text: str = ""

    def derive(self, *, text: str, source_url: str, media_type: str) -> LearningOutline:
        self.received_text = text
        return self.outline


def _content(*, media_type: str = "html", title: str | None = "Catalog title") -> ExtractedContent:
    return ExtractedContent(
        text="Chapter 1: Algorithms. Chapter 2: Data Structures.",
        media_type=media_type,
        title=title,
        final_url="https://PUBLISHER.example/books/algorithms/?ref=catalog#details",
    )


def _outline() -> LearningOutline:
    return LearningOutline(
        title="Algorithms Explained",
        author="Ada Author",
        subject="Computer Science",
        topics=["Algorithm analysis", "Data structures", "algorithm analysis"],
        chapters=["Foundations"],
        sections=["Asymptotic notation"],
        confidence=0.88,
    )


@pytest.mark.parametrize("page_title", ["Publisher catalog", "Readable online book"])
def test_book_url_adapter_normalizes_catalog_and_readable_pages(page_title: str) -> None:
    adapter = BookUrlAdapter(
        settings=DEFAULT_SETTINGS,
        extractor=StubExtractor(content=_content(title=page_title)),
        outline_deriver=StubOutlineDeriver(_outline()),
    )

    result = adapter.normalize(
        CourseInputRequest(book_url="https://publisher.example/books/algorithms", chapter="Chapter 3")
    )

    assert result.input_kind is LearningInputKind.BOOK_URL
    assert result.canonical_identifier == "url:https://publisher.example/books/algorithms"
    assert result.title == "Algorithms Explained"
    assert result.author == "Ada Author"
    assert result.subject == "Computer Science"
    assert result.topics == ["Algorithm analysis", "Data structures"]
    assert result.chapters == ["Chapter 3", "Foundations"]
    assert BOOK_CONTEXT_WARNING in result.warnings
    assert result.field_provenance[NormalizedLearningField.AUTHOR].origin is ProvenanceOrigin.EXTRACTED_CONTENT
    assert result.field_provenance[NormalizedLearningField.CHAPTERS].origin is ProvenanceOrigin.USER_INPUT


def test_book_url_adapter_marks_direct_pdf_without_approving_it() -> None:
    adapter = BookUrlAdapter(
        settings=DEFAULT_SETTINGS,
        extractor=StubExtractor(content=_content(media_type="pdf", title=None)),
        outline_deriver=StubOutlineDeriver(_outline()),
    )

    result = adapter.normalize(CourseInputRequest(book_url="https://publisher.example/book.pdf"))

    assert result.warnings == [BOOK_CONTEXT_WARNING, DIRECT_PDF_WARNING]


def test_book_url_adapter_records_configured_versions() -> None:
    settings = RagSettings(book_url_adapter_version="book-test", learning_outline_prompt_version="outline-test")
    adapter = BookUrlAdapter(
        settings=settings,
        extractor=StubExtractor(content=_content()),
        outline_deriver=StubOutlineDeriver(_outline()),
    )

    result = adapter.normalize(CourseInputRequest(book_url="https://publisher.example/book"))

    assert result.field_provenance[NormalizedLearningField.CANONICAL_IDENTIFIER].method.endswith("book-test")
    assert result.field_provenance[NormalizedLearningField.TOPICS].method.endswith("outline-test")


@pytest.mark.parametrize(
    ("extractor", "message"),
    [
        (StubExtractor(error=RuntimeError("offline")), "Could not extract learning content"),
        (
            StubExtractor(content=ExtractedContent(text="", media_type="html", title=None, final_url="https://x.test")),
            "no extractable learning content",
        ),
    ],
)
def test_book_url_adapter_returns_structured_errors(extractor: StubExtractor, message: str) -> None:
    adapter = BookUrlAdapter(
        settings=DEFAULT_SETTINGS,
        extractor=extractor,
        outline_deriver=StubOutlineDeriver(_outline()),
    )

    with pytest.raises(InputNormalizationError, match=message):
        adapter.normalize(CourseInputRequest(book_url="https://publisher.example/book"))


def test_dispatcher_runs_registered_book_url_adapter() -> None:
    adapter = BookUrlAdapter(
        settings=DEFAULT_SETTINGS,
        extractor=StubExtractor(content=_content()),
        outline_deriver=StubOutlineDeriver(_outline()),
    )
    dispatcher = AdapterDispatcher({LearningInputKind.BOOK_URL: adapter})

    result = dispatcher.dispatch(CourseInputRequest(book_url="https://publisher.example/book"))

    assert result.input_kind is LearningInputKind.BOOK_URL


def test_book_url_adapter_truncates_extracted_text_and_warns() -> None:
    oversized = "Chapter 1: Algorithms. " * 200
    content = ExtractedContent(
        text=oversized,
        media_type="html",
        title="Catalog title",
        final_url="https://publisher.example/books/algorithms",
    )
    deriver = StubOutlineDeriver(_outline())
    adapter = BookUrlAdapter(
        settings=RagSettings(max_outline_input_chars=300),
        extractor=StubExtractor(content=content),
        outline_deriver=deriver,
    )

    result = adapter.normalize(CourseInputRequest(book_url="https://publisher.example/books/algorithms"))

    assert len(deriver.received_text) <= 300
    assert result.warnings[-1] == (
        f"Only the first {len(deriver.received_text)} of {len(oversized)} extracted characters were used to "
        "derive the learning outline; it may be incomplete."
    )
