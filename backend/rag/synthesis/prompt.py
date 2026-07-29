"""Prompt construction for evidence-only study-guide synthesis."""

from __future__ import annotations

from backend.rag.models import SelectedEvidence

SYSTEM_PROMPT = """You are ScholarSource, an assistant that recommends study resources to students.

You will receive a student topic and selected evidence chunks. Each chunk was
retrieved, reranked, and stored before this request.

Rules:
- Build the study guide using ONLY the provided evidence chunks.
- Do not use external knowledge about websites, books, courses, or the topic.
- Refer to evidence exclusively by chunk_id. Never write or invent a URL.
- Every recommendation must include at least one supporting_chunk_ids entry.
- Use only chunk_ids that appear in the evidence.
- If the evidence is thin, contradictory, or off-topic, say so plainly in
  limitations and return fewer recommendations, or none.
- Never pad weak evidence into confident-sounding advice.
- Explain why each recommended resource helps and how a student should use it.
"""


def format_evidence_context(evidence: list[SelectedEvidence]) -> str:
    """Format selected evidence as stable, model-citable context blocks."""
    blocks = [(f"[chunk_id: {item.chunk_id}]\n[resource: {item.title}]\n{item.content}") for item in evidence]
    return "\n\n---\n\n".join(blocks)


def build_user_message(topic: str, evidence: list[SelectedEvidence]) -> str:
    """Build a synthesis request containing only the topic and selected evidence."""
    context = format_evidence_context(evidence)
    return f"Student topic: {topic}\n\nSelected evidence chunks:\n{context}"
