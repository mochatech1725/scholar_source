"""Tests for course-page and general educational-page normalization."""

from dataclasses import dataclass
from unittest.mock import Mock

import pytest

from backend.models import CourseInputRequest
from backend.rag.config import DEFAULT_SETTINGS, RagSettings
from backend.rag.errors import InputNormalizationError
from backend.rag.extraction.extractor import ExtractedContent
from backend.rag.input_adapters import AdapterDispatcher
from backend.rag.input_adapters.url_page import LearningOutline, StructuredLearningOutlineDeriver, UrlPageAdapter
from backend.rag.models import LearningInputKind, NormalizedLearningField, ProvenanceOrigin


@dataclass
class StubExtractor:
    content: ExtractedContent | None = None
    error: Exception | None = None
    received_url: str | None = None

    def extract_url(self, url: str) -> ExtractedContent:
        self.received_url = url
        if self.error:
            raise self.error
        assert self.content is not None
        return self.content


@dataclass
class StubOutlineDeriver:
    outline: LearningOutline
    received: dict[str, str] | None = None

    def derive(self, *, text: str, source_url: str, media_type: str) -> LearningOutline:
        self.received = {"text": text, "source_url": source_url, "media_type": media_type}
        return self.outline


def _content(
    text: str = "Course description. Limits and derivatives. Learning objectives include integration.",
    *,
    media_type: str = "html",
    title: str | None = "Calculus I | Example University",
) -> ExtractedContent:
    return ExtractedContent(
        text=text,
        media_type=media_type,
        title=title,
        final_url="https://EXAMPLE.edu/calculus/?term=fall#overview",
    )


def _outline() -> LearningOutline:
    return LearningOutline(
        title="Calculus I",
        institution="Example University",
        subject="Mathematics",
        topics=["Limits", "Derivatives", "limits"],
        chapters=["Differential calculus"],
        sections=["Integration basics"],
        confidence=0.9,
    )


def test_url_adapter_reuses_extraction_and_builds_course_outline() -> None:
    extractor = StubExtractor(content=_content())
    deriver = StubOutlineDeriver(_outline())
    adapter = UrlPageAdapter(settings=DEFAULT_SETTINGS, extractor=extractor, outline_deriver=deriver)
    request = CourseInputRequest(
        course_url="https://example.edu/calculus/",
        chapter="Week 2",
        sections="Limits review, Integration basics",
        targeted_sites="mit.edu",
    )

    result = adapter.normalize(request)

    assert extractor.received_url == request.course_url
    assert deriver.received == {
        "text": extractor.content.text,
        "source_url": extractor.content.final_url,
        "media_type": "html",
    }
    assert result.input_kind is LearningInputKind.COURSE_PAGE
    assert result.canonical_identifier == "url:https://example.edu/calculus?term=fall"
    assert result.title == "Calculus I"
    assert result.institution == "Example University"
    assert result.subject == "Mathematics"
    assert result.topics == ["Limits", "Derivatives"]
    assert result.chapters == ["Week 2", "Differential calculus"]
    assert result.sections == ["Limits review", "Integration basics"]
    assert result.user_constraints.targeted_sites == ["mit.edu"]
    assert result.confidence == 0.9
    assert result.field_provenance[NormalizedLearningField.TOPICS].origin is ProvenanceOrigin.EXTRACTED_CONTENT
    assert result.field_provenance[NormalizedLearningField.CHAPTERS].origin is ProvenanceOrigin.USER_INPUT


def test_url_adapter_classifies_general_educational_html() -> None:
    extractor = StubExtractor(content=_content("Photosynthesis converts light energy into chemical energy."))
    adapter = UrlPageAdapter(
        settings=DEFAULT_SETTINGS,
        extractor=extractor,
        outline_deriver=StubOutlineDeriver(
            LearningOutline(topics=["Photosynthesis"], subject="Biology", confidence=0.8)
        ),
    )

    result = adapter.normalize(CourseInputRequest(course_url="https://example.edu/biology/photosynthesis"))

    assert result.input_kind is LearningInputKind.EDUCATIONAL_PAGE
    assert result.topics == ["Photosynthesis"]


def test_url_adapter_detects_pdf_and_preserves_warning() -> None:
    extractor = StubExtractor(content=_content(media_type="pdf", title=None))
    adapter = UrlPageAdapter(
        settings=DEFAULT_SETTINGS,
        extractor=extractor,
        outline_deriver=StubOutlineDeriver(_outline()),
    )

    result = adapter.normalize(CourseInputRequest(course_url="https://example.edu/notes"))

    assert result.input_kind is LearningInputKind.COURSE_PAGE
    assert result.warnings == ["The submitted URL resolved to a PDF; its text was normalized as an educational page."]


def test_url_adapter_prefers_explicit_context_with_user_provenance() -> None:
    adapter = UrlPageAdapter(
        settings=DEFAULT_SETTINGS,
        extractor=StubExtractor(content=_content()),
        outline_deriver=StubOutlineDeriver(_outline()),
    )

    result = adapter.normalize(
        CourseInputRequest(
            course_url="https://example.edu/calculus",
            course_name="Honors Calculus",
            university_name="User University",
            subject="Applied Mathematics",
        )
    )

    assert result.title == "Honors Calculus"
    assert result.institution == "User University"
    assert result.subject == "Applied Mathematics"
    for field in (
        NormalizedLearningField.TITLE,
        NormalizedLearningField.INSTITUTION,
        NormalizedLearningField.SUBJECT,
    ):
        assert result.field_provenance[field].origin is ProvenanceOrigin.USER_INPUT


def test_url_adapter_records_configured_versions() -> None:
    settings = RagSettings(url_page_adapter_version="adapter-test", learning_outline_prompt_version="prompt-test")
    adapter = UrlPageAdapter(
        settings=settings,
        extractor=StubExtractor(content=_content()),
        outline_deriver=StubOutlineDeriver(_outline()),
    )

    result = adapter.normalize(CourseInputRequest(course_url="https://example.edu/calculus"))

    assert result.field_provenance[NormalizedLearningField.CANONICAL_IDENTIFIER].method.endswith("adapter-test")
    assert result.field_provenance[NormalizedLearningField.TOPICS].method.endswith("prompt-test")


@pytest.mark.parametrize(
    ("extractor", "message"),
    [
        (StubExtractor(error=RuntimeError("offline")), "Could not extract learning content"),
        (StubExtractor(content=_content("")), "no extractable learning content"),
    ],
)
def test_url_adapter_returns_structured_normalization_errors(extractor: StubExtractor, message: str) -> None:
    adapter = UrlPageAdapter(
        settings=DEFAULT_SETTINGS,
        extractor=extractor,
        outline_deriver=StubOutlineDeriver(_outline()),
    )

    with pytest.raises(InputNormalizationError, match=message):
        adapter.normalize(CourseInputRequest(course_url="https://example.edu/course"))


def test_dispatcher_runs_registered_url_adapter() -> None:
    adapter = UrlPageAdapter(
        settings=DEFAULT_SETTINGS,
        extractor=StubExtractor(content=_content()),
        outline_deriver=StubOutlineDeriver(_outline()),
    )
    dispatcher = AdapterDispatcher({LearningInputKind.COURSE_PAGE: adapter})

    result = dispatcher.dispatch(CourseInputRequest(course_url="https://example.edu/course"))

    assert result.input_kind is LearningInputKind.COURSE_PAGE


def test_structured_outline_deriver_sends_only_extracted_page_context() -> None:
    llm = Mock()
    structured_llm = llm.with_structured_output.return_value
    structured_llm.invoke.return_value = _outline()
    deriver = StructuredLearningOutlineDeriver(DEFAULT_SETTINGS, llm=llm)

    result = deriver.derive(
        text="Limits and derivatives are the first learning objectives.",
        source_url="https://example.edu/calculus",
        media_type="html",
    )

    assert result == _outline()
    llm.with_structured_output.assert_called_once_with(LearningOutline)
    messages = structured_llm.invoke.call_args.args[0]
    assert messages[0][0] == "system"
    assert "Use only the supplied extracted content" in messages[0][1]
    assert "https://example.edu/calculus" in messages[1][1]
    assert "Limits and derivatives" in messages[1][1]


def test_structured_outline_deriver_rejects_non_schema_response() -> None:
    llm = Mock()
    llm.with_structured_output.return_value.invoke.return_value = {"topics": ["Limits"]}
    deriver = StructuredLearningOutlineDeriver(DEFAULT_SETTINGS, llm=llm)

    with pytest.raises(InputNormalizationError, match="did not return a structured"):
        deriver.derive(text="Limits", source_url="https://example.edu", media_type="html")


def test_url_adapter_truncates_extracted_text_and_warns() -> None:
    oversized = "Course description. " + ("Limits and derivatives are covered here. " * 200)
    deriver = StubOutlineDeriver(_outline())
    adapter = UrlPageAdapter(
        settings=RagSettings(max_outline_input_chars=200),
        extractor=StubExtractor(content=_content(oversized)),
        outline_deriver=deriver,
    )

    result = adapter.normalize(CourseInputRequest(course_url="https://example.edu/calculus/"))

    assert deriver.received is not None
    assert len(deriver.received["text"]) <= 200
    assert result.warnings[-1] == (
        f"Only the first {len(deriver.received['text'])} of {len(oversized)} extracted characters were used to "
        "derive the learning outline; it may be incomplete."
    )


def test_url_adapter_drops_topics_the_page_does_not_support() -> None:
    deriver = StubOutlineDeriver(LearningOutline(topics=["Limits", "Offshore banking incorporation"], confidence=0.7))
    adapter = UrlPageAdapter(
        settings=DEFAULT_SETTINGS,
        extractor=StubExtractor(content=_content()),
        outline_deriver=deriver,
    )

    result = adapter.normalize(CourseInputRequest(course_url="https://example.edu/calculus"))

    assert result.topics == ["Limits"]
    assert result.warnings[0] == "1 derived topic(s) were dropped because the extracted content did not support them."
    assert "Offshore" not in result.warnings[0]


def test_url_adapter_rejects_an_outline_with_no_supported_topic() -> None:
    adapter = UrlPageAdapter(
        settings=DEFAULT_SETTINGS,
        extractor=StubExtractor(content=_content()),
        outline_deriver=StubOutlineDeriver(LearningOutline(topics=["Offshore banking incorporation"], confidence=0.7)),
    )

    with pytest.raises(InputNormalizationError, match="No derived learning topic was supported"):
        adapter.normalize(CourseInputRequest(course_url="https://example.edu/calculus"))


def test_structured_outline_deriver_drops_topics_absent_from_the_budgeted_text() -> None:
    llm = Mock()
    structured_llm = llm.with_structured_output.return_value
    structured_llm.invoke.return_value = LearningOutline(
        topics=["Derivatives", "Offshore banking incorporation"], confidence=0.7
    )
    deriver = StructuredLearningOutlineDeriver(DEFAULT_SETTINGS, llm=llm)

    result = deriver.derive(
        text="Limits and derivatives are the first learning objectives.",
        source_url="https://example.edu/calculus",
        media_type="html",
    )

    assert result.topics == ["Derivatives"]
    assert result.warnings == ["1 derived topic(s) were dropped because the extracted content did not support them."]


def test_structured_outline_deriver_rejects_a_fully_unsupported_outline() -> None:
    llm = Mock()
    llm.with_structured_output.return_value.invoke.return_value = LearningOutline(
        topics=["Offshore banking incorporation"], confidence=0.7
    )
    deriver = StructuredLearningOutlineDeriver(DEFAULT_SETTINGS, llm=llm)

    with pytest.raises(InputNormalizationError, match="No derived learning topic was supported"):
        deriver.derive(
            text="Limits and derivatives are the first learning objectives.",
            source_url="https://example.edu/calculus",
            media_type="html",
        )


def test_structured_outline_deriver_enforces_the_budget_on_its_own() -> None:
    llm = Mock()
    structured_llm = llm.with_structured_output.return_value
    structured_llm.invoke.return_value = _outline()
    deriver = StructuredLearningOutlineDeriver(RagSettings(max_outline_input_chars=50), llm=llm)

    result = deriver.derive(
        text="Limits and derivatives are the first learning objectives. " * 20,
        source_url="https://example.edu/calculus",
        media_type="html",
    )

    prompt = structured_llm.invoke.call_args.args[0][1][1]
    assert len(prompt.split("Extracted content:\n", maxsplit=1)[1]) <= 50
    assert result.warnings[-1].startswith("Only the first 50 of 1160 extracted characters")
