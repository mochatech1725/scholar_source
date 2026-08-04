"""Shared Pydantic models for the ScholarSource RAG pipeline."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class QualityStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


class ExtractionStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WeakEvidenceStatus(StrEnum):
    NOT_EVALUATED = "not_evaluated"
    STRONG = "strong"
    WEAK = "weak"
    INSUFFICIENT = "insufficient"


class LearningInputKind(StrEnum):
    """Supported primary inputs that normalize into one learning request."""

    TOPIC_LIST = "topic_list"
    COURSE_PAGE = "course_page"
    EDUCATIONAL_PAGE = "educational_page"
    BOOK_URL = "book_url"
    ISBN = "isbn"
    BOOK_METADATA = "book_metadata"


class ProvenanceOrigin(StrEnum):
    """Origin of a normalized field value."""

    USER_INPUT = "user_input"
    EXTRACTED_CONTENT = "extracted_content"
    PROVIDER_METADATA = "provider_metadata"
    ADAPTER_DERIVED = "adapter_derived"


class NormalizedLearningField(StrEnum):
    """Fields whose values require traceable normalization provenance."""

    CANONICAL_IDENTIFIER = "canonical_identifier"
    TITLE = "title"
    AUTHOR = "author"
    EDITION = "edition"
    INSTITUTION = "institution"
    SUBJECT = "subject"
    TOPICS = "topics"
    CHAPTERS = "chapters"
    SECTIONS = "sections"
    USER_CONSTRAINTS = "user_constraints"


class RagModel(BaseModel):
    """Base model: reject unexpected fields, strip whitespace."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class FieldProvenance(RagModel):
    """Trace describing how one normalized learning-request field was obtained."""

    origin: ProvenanceOrigin
    source_reference: str = Field(
        min_length=1,
        description="Non-secret input field, URL, upload ID, or provider record reference.",
    )
    method: str = Field(
        min_length=1,
        description="Deterministic adapter operation or versioned extraction method.",
    )
    confidence: float = Field(ge=0.0, le=1.0)


class LearningConstraints(RagModel):
    """Optional user preferences preserved for downstream query generation."""

    desired_resource_types: list[str] = Field(default_factory=list)
    excluded_sites: list[str] = Field(default_factory=list)
    targeted_sites: list[str] = Field(default_factory=list)
    preferred_creators: list[str] = Field(default_factory=list)


class NormalizedLearningRequest(RagModel):
    """Canonical learning context emitted by every successful input adapter."""

    input_kind: LearningInputKind
    canonical_identifier: str = Field(min_length=1)
    title: str | None = None
    author: str | None = None
    edition: str | None = None
    institution: str | None = None
    subject: str | None = None
    topics: list[str] = Field(min_length=1)
    chapters: list[str] = Field(default_factory=list)
    sections: list[str] = Field(default_factory=list)
    user_constraints: LearningConstraints = Field(default_factory=LearningConstraints)
    field_provenance: dict[NormalizedLearningField, FieldProvenance]
    warnings: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def require_provenance_for_populated_fields(self) -> NormalizedLearningRequest:
        """Reject normalized values that cannot be traced to their origin."""

        populated_fields = {
            NormalizedLearningField.CANONICAL_IDENTIFIER,
            NormalizedLearningField.TOPICS,
        }
        optional_fields = {
            NormalizedLearningField.TITLE: self.title,
            NormalizedLearningField.AUTHOR: self.author,
            NormalizedLearningField.EDITION: self.edition,
            NormalizedLearningField.INSTITUTION: self.institution,
            NormalizedLearningField.SUBJECT: self.subject,
            NormalizedLearningField.CHAPTERS: self.chapters,
            NormalizedLearningField.SECTIONS: self.sections,
        }
        populated_fields.update(field for field, value in optional_fields.items() if value)
        if self.user_constraints != LearningConstraints():
            populated_fields.add(NormalizedLearningField.USER_CONSTRAINTS)

        missing_fields = populated_fields.difference(self.field_provenance)
        if missing_fields:
            names = ", ".join(sorted(field.value for field in missing_fields))
            raise ValueError(f"Missing provenance for normalized fields: {names}")
        return self


class SourceRecord(RagModel):
    source_id: UUID | None = None
    url: str
    normalized_url: str
    title: str
    source_type: str
    quality_status: QualityStatus = QualityStatus.PENDING
    quality_reason: str = ""
    metadata: dict = Field(default_factory=dict)


class ExtractedDocument(RagModel):
    document_id: UUID | None = None
    source_id: UUID
    url: str
    title: str
    text: str = Field(exclude=True, default="")
    extracted_text_hash: str
    extraction_status: ExtractionStatus
    extraction_error: str | None = None
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict = Field(default_factory=dict)


class ChunkRecord(RagModel):
    chunk_id: UUID | None = None
    source_id: UUID
    extracted_document_id: UUID | None = None
    url: str
    title: str
    chunk_index: int = Field(ge=0)
    content: str = Field(min_length=1)
    content_hash: str
    embedding_model: str
    token_count: int | None = None
    metadata: dict = Field(default_factory=dict)


class EmbeddingRecord(RagModel):
    chunk_id: UUID
    content_hash: str
    embedding_model: str
    embedding_dimensions: int = Field(gt=0)
    embedding: list[float] = Field(exclude=True, default_factory=list)


class RetrievalHit(RagModel):
    """Stored chunk with raw, retrieval-path-specific similarity scores."""

    chunk_id: UUID
    source_id: UUID
    url: str = Field(min_length=1)
    title: str = Field(min_length=1)
    chunk_index: int = Field(ge=0)
    content: str = Field(min_length=1)
    content_hash: str = Field(min_length=1)
    semantic_score: float | None = None
    lexical_score: float | None = None


class SelectedEvidence(RagModel):
    """Retrieved chunk with raw debug scores and a final relevance ranking."""

    chunk_id: UUID
    source_id: UUID
    url: str
    title: str
    chunk_index: int = Field(ge=0)
    content: str = Field(min_length=1)
    semantic_score: float | None = Field(
        default=None,
        description="Original semantic retrieval score retained for debugging.",
    )
    lexical_score: float | None = Field(
        default=None,
        description="Original lexical retrieval score retained for debugging.",
    )
    rerank_score: float = Field(
        description=("Final relevance score retained for debugging; not comparable to raw retrieval scores."),
    )
    evidence_rank: int = Field(
        ge=1,
        description="One-based final relevance position after reranking.",
    )


class EvidenceSupport(RagModel):
    """Model-provided quote that grounds a recommendation in one chunk."""

    chunk_id: str
    quote: str = Field(
        min_length=1,
        description="Exact quote from the selected chunk that supports the recommendation.",
    )


class RecommendationDraft(RagModel):
    """Model-facing synthesis output. Chunk IDs only — never URLs."""

    resource_title: str
    why_useful: str
    how_to_use: str
    evidence_support: list[EvidenceSupport] = Field(
        min_length=1,
        description="Selected chunk IDs and exact quotes that support every factual claim.",
    )


class StudyGuideDraft(RagModel):
    """Raw structured output from the synthesis LLM call."""

    overview: str
    recommendations: list[RecommendationDraft] = Field(default_factory=list)
    limitations: str = ""


class CitedRecommendation(RagModel):
    """User-facing recommendation with citations resolved from storage."""

    resource_title: str
    url: str
    source_title: str
    why_useful: str
    how_to_use: str
    cited_chunk_ids: list[UUID]


class CitedStudyGuide(RagModel):
    overview: str
    recommendations: list[CitedRecommendation] = Field(default_factory=list)
    limitations: str = ""
    weak_evidence_status: WeakEvidenceStatus = WeakEvidenceStatus.NOT_EVALUATED
    weak_evidence_reason: str | None = None
    cited_source_ids: list[UUID] = Field(default_factory=list)


class PipelineResult(RagModel):
    run_id: UUID
    guide: CitedStudyGuide
    evidence: list[SelectedEvidence] = Field(default_factory=list)
    generated_queries: list[str] = Field(default_factory=list)
    completed_at: datetime | None = None
