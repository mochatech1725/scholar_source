"""Generate a structured study-guide draft from selected evidence only."""

from __future__ import annotations

from typing import Protocol, cast

from langchain_openai import ChatOpenAI

from backend.rag.config import RagSettings
from backend.rag.errors import SynthesisError
from backend.rag.models import SelectedEvidence, StudyGuideDraft, WeakEvidenceStatus
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
    ) -> StudyGuideDraft:
        """Generate a guide or return a transparent insufficient-evidence response."""
        if status is WeakEvidenceStatus.NOT_EVALUATED:
            raise SynthesisError("Evidence must be assessed before synthesis.")
        if status is WeakEvidenceStatus.INSUFFICIENT or not evidence:
            return StudyGuideDraft(
                overview=INSUFFICIENT_MESSAGE,
                limitations=status_reason or "No usable evidence was retrieved.",
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
        if status is WeakEvidenceStatus.WEAK:
            return draft.model_copy(
                update={
                    "overview": f"{WEAK_PREFIX}\n\n{draft.overview}",
                    "limitations": self._weak_limitations(
                        draft.limitations,
                        status_reason=status_reason,
                    ),
                }
            )
        return draft

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
    def _validate_citations(
        draft: StudyGuideDraft,
        evidence: list[SelectedEvidence],
    ) -> None:
        """Reject recommendations that cite anything outside selected evidence."""
        selected_chunk_ids = {str(item.chunk_id) for item in evidence}
        for recommendation in draft.recommendations:
            unknown_chunk_ids = set(recommendation.supporting_chunk_ids) - selected_chunk_ids
            if unknown_chunk_ids:
                raise SynthesisError("Synthesis cited chunk IDs that were not present in selected evidence.")
