"""Generate a structured study-guide draft from selected evidence only."""

from __future__ import annotations

from typing import Protocol, cast

from langchain_openai import ChatOpenAI

from backend.rag.config import RagSettings
from backend.rag.errors import SynthesisError
from backend.rag.models import SelectedEvidence, StudyGuideDraft
from backend.rag.synthesis.prompt import SYSTEM_PROMPT, build_user_message


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
    ) -> StudyGuideDraft:
        """Generate a guide from selected evidence, never from empty context."""
        if not evidence:
            raise SynthesisError("Cannot synthesize a study guide without selected evidence.")

        draft = self._structured_llm.invoke(
            [
                ("system", SYSTEM_PROMPT),
                ("human", build_user_message(topic, evidence)),
            ]
        )
        if not isinstance(draft, StudyGuideDraft):
            raise SynthesisError("Synthesis did not return a structured study guide.")
        return draft
