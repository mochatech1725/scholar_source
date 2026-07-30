"""Generate a structured study-guide draft from selected evidence only."""

from __future__ import annotations

import re
from typing import Protocol, cast
from uuid import UUID

from langchain_openai import ChatOpenAI

from backend.rag.config import RagSettings
from backend.rag.errors import SynthesisError
from backend.rag.models import (
    CitedRecommendation,
    CitedStudyGuide,
    SelectedEvidence,
    StudyGuideDraft,
    WeakEvidenceStatus,
)
from backend.rag.synthesis.prompt import SYSTEM_PROMPT, build_user_message

INSUFFICIENT_MESSAGE = (
    "ScholarSource could not find enough trustworthy material on this topic "
    "to build a study guide. Try a more specific topic, or provide a course "
    "page or textbook to search from."
)

WEAK_PREFIX = (
    "Evidence for this topic was limited, so treat these suggestions as "
    "starting points rather than a complete study plan."
)


class StructuredSynthesisModel(Protocol):
    """Minimal interface needed from a structured-output chat model."""

    def invoke(self, input: object) -> StudyGuideDraft:
        """Invoke the model with chat messages."""
        ...


class SynthesisChatModel(Protocol):
    """Chat-model interface used to configure structured synthesis output."""

    def with_structured_output(self, schema: type[StudyGuideDraft]) -> object:
        """Bind a Pydantic output schema to the model."""
        ...


class EvidenceSynthesizer:
    """Create study-guide drafts without exposing unselected context."""

    def __init__(
        self,
        settings: RagSettings,
        llm: SynthesisChatModel | None = None,
    ) -> None:
        base_llm = llm or ChatOpenAI(
            model=settings.chat_model,
            temperature=0.0,
            seed=settings.llm_seed,
        )
        self._structured_llm = cast(
            StructuredSynthesisModel,
            base_llm.with_structured_output(StudyGuideDraft),
        )

    def synthesize(
        self,
        topic: str,
        evidence: list[SelectedEvidence],
        *,
        status: WeakEvidenceStatus,
        status_reason: str | None,
    ) -> CitedStudyGuide:
        """Generate a guide or return a transparent insufficient-evidence response."""
        if status is WeakEvidenceStatus.NOT_EVALUATED:
            raise SynthesisError("Evidence must be assessed before synthesis.")
        if status is WeakEvidenceStatus.INSUFFICIENT or not evidence:
            return CitedStudyGuide(
                overview=INSUFFICIENT_MESSAGE,
                limitations=status_reason or "No usable evidence was retrieved.",
                weak_evidence_status=WeakEvidenceStatus.INSUFFICIENT,
                weak_evidence_reason=status_reason,
            )

        draft = self._structured_llm.invoke(
            [
                ("system", SYSTEM_PROMPT),
                ("human", build_user_message(topic, evidence)),
            ]
        )
        if not isinstance(draft, StudyGuideDraft):
            raise SynthesisError("Synthesis did not return a structured study guide.")
        self._validate_citations(draft, evidence)
        overview = self._grounded_overview(len(draft.recommendations))
        limitations = draft.limitations
        if status is WeakEvidenceStatus.WEAK:
            overview = f"{WEAK_PREFIX}\n\n{overview}"
            limitations = self._weak_limitations(
                limitations,
                status_reason=status_reason,
            )
        return self._resolve_citations(
            draft,
            evidence,
            overview=overview,
            limitations=limitations,
            status=status,
            status_reason=status_reason,
        )

    @staticmethod
    def _resolve_citations(
        draft: StudyGuideDraft,
        evidence: list[SelectedEvidence],
        *,
        overview: str,
        limitations: str,
        status: WeakEvidenceStatus,
        status_reason: str | None,
    ) -> CitedStudyGuide:
        """Join authoritative source titles and URLs from selected evidence."""
        evidence_by_chunk_id = {item.chunk_id: item for item in evidence}
        recommendations: list[CitedRecommendation] = []
        cited_source_ids: set[UUID] = set()

        for recommendation in draft.recommendations:
            cited_chunk_ids = [UUID(support.chunk_id) for support in recommendation.evidence_support]
            primary_evidence = evidence_by_chunk_id[cited_chunk_ids[0]]
            cited_source_ids.update(evidence_by_chunk_id[chunk_id].source_id for chunk_id in cited_chunk_ids)
            recommendations.append(
                CitedRecommendation(
                    resource_title=primary_evidence.title,
                    url=primary_evidence.url,
                    source_title=primary_evidence.title,
                    why_useful=recommendation.why_useful,
                    how_to_use=recommendation.how_to_use,
                    cited_chunk_ids=cited_chunk_ids,
                )
            )

        return CitedStudyGuide(
            overview=overview,
            recommendations=recommendations,
            limitations=limitations,
            weak_evidence_status=status,
            weak_evidence_reason=status_reason,
            cited_source_ids=sorted(cited_source_ids, key=str),
        )

    @staticmethod
    def _weak_limitations(
        draft_limitations: str,
        *,
        status_reason: str | None,
    ) -> str:
        """Preserve both the deterministic retrieval warning and model caveats."""
        parts = [part for part in (status_reason, draft_limitations) if part]
        return "\n\n".join(parts)

    @staticmethod
    def _grounded_overview(recommendation_count: int) -> str:
        """Build overview prose from validated output shape, not model claims."""
        noun = "resource" if recommendation_count == 1 else "resources"
        return f"ScholarSource found {recommendation_count} cited {noun} for this study guide."

    @staticmethod
    def _validate_citations(
        draft: StudyGuideDraft,
        evidence: list[SelectedEvidence],
    ) -> None:
        """Reject recommendations that cite anything outside selected evidence."""
        evidence_by_chunk_id = {str(item.chunk_id): item for item in evidence}
        for recommendation in draft.recommendations:
            support_chunk_ids = {support.chunk_id for support in recommendation.evidence_support}
            unknown_chunk_ids = support_chunk_ids - evidence_by_chunk_id.keys()
            if unknown_chunk_ids:
                raise SynthesisError("Synthesis cited chunk IDs that were not present in selected evidence.")
            for support in recommendation.evidence_support:
                evidence_content = evidence_by_chunk_id[support.chunk_id].content
                if _normalize_whitespace(support.quote) not in _normalize_whitespace(evidence_content):
                    raise SynthesisError(
                        "Synthesis included a supporting quote that was not present in its cited chunk."
                    )


def _normalize_whitespace(value: str) -> str:
    """Normalize whitespace so copied quotes survive harmless line wrapping."""
    return re.sub(r"\s+", " ", value).strip()
