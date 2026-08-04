"""Deterministic paragraph chunking with traceable source metadata."""

from __future__ import annotations

import re
from textwrap import shorten

from backend.rag.config import RagSettings
from backend.rag.errors import ChunkingError
from backend.rag.hashing import sha256_text
from backend.rag.models import ChunkRecord, ExtractedDocument, SourceRecord
from backend.rag.sources.corpus import assert_corpus_eligible

SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
CHUNKING_METHOD = "paragraph_pack_v1"


def split_paragraphs(text: str) -> list[str]:
    """Split text into non-empty paragraphs."""
    return [part.strip() for part in text.split("\n\n") if part.strip()]


def split_oversized(paragraph: str, target_chars: int) -> list[str]:
    """Split a paragraph larger than the target at sentence boundaries."""
    if len(paragraph) <= target_chars:
        return [paragraph]

    pieces: list[str] = []
    current = ""
    for sentence in SENTENCE_BOUNDARY.split(paragraph):
        if len(sentence) > target_chars:
            if current:
                pieces.append(current)
                current = ""
            pieces.extend(_split_long_sentence(sentence, target_chars))
            continue
        if current and len(current) + len(sentence) + 1 > target_chars:
            pieces.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        pieces.append(current)
    return pieces


def _split_long_sentence(sentence: str, target_chars: int) -> list[str]:
    """Split sentence text that has no usable punctuation boundary."""
    pieces: list[str] = []
    current = ""
    for word in sentence.split():
        if len(word) > target_chars:
            if current:
                pieces.append(current)
                current = ""
            pieces.extend(word[start : start + target_chars] for start in range(0, len(word), target_chars))
            continue
        if current and len(current) + len(word) + 1 > target_chars:
            pieces.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        pieces.append(current)
    return pieces


def chunk_text(text: str, *, settings: RagSettings) -> list[str]:
    """Pack paragraphs into chunks near the target size with overlap."""
    units: list[str] = []
    for paragraph in split_paragraphs(text):
        units.extend(split_oversized(paragraph, settings.chunk_target_chars))
    if not units:
        return []

    chunks: list[str] = []
    current = ""
    max_chunk_chars = settings.chunk_target_chars + settings.chunk_overlap_chars + 2
    for unit in units:
        combined_length = len(current) + len(unit) + 2
        if (
            current
            and combined_length > settings.chunk_target_chars
            and (len(current) >= settings.chunk_min_chars or combined_length > max_chunk_chars)
        ):
            chunks.append(current)
            overlap = current[-settings.chunk_overlap_chars :]
            current = f"{overlap}\n\n{unit}"
        else:
            current = f"{current}\n\n{unit}".strip()
    if len(current) >= settings.chunk_min_chars or not chunks:
        chunks.append(current)
    else:
        chunks[-1] = f"{chunks[-1]}\n\n{current}"
    return chunks


def chunk_document(
    document: ExtractedDocument,
    *,
    source: SourceRecord,
    settings: RagSettings,
) -> list[ChunkRecord]:
    """Convert an extracted document into chunk records with source metadata.

    The source record is required rather than inferred from the document so the
    corpus tenancy rule (plan step 0.6.8) is checked at the one boundary where
    text becomes retrievable: nothing can be chunked without presenting the
    source it came from.
    """
    if document.document_id is None:
        raise ChunkingError("Document must be persisted before chunking.")
    if source.source_id != document.source_id:
        raise ChunkingError("Source record does not match the extracted document.")
    assert_corpus_eligible(source)
    if not document.text:
        return []

    records: list[ChunkRecord] = []
    for index, content in enumerate(chunk_text(document.text, settings=settings)):
        records.append(
            ChunkRecord(
                source_id=document.source_id,
                extracted_document_id=document.document_id,
                url=document.url,
                title=document.title,
                chunk_index=index,
                content=content,
                content_hash=sha256_text(content),
                embedding_model=settings.embedding_model,
                metadata={
                    "chunking_method": CHUNKING_METHOD,
                    "chunk_index": index,
                    "source_order": index,
                    "chunk_target_chars": settings.chunk_target_chars,
                    "chunk_overlap_chars": settings.chunk_overlap_chars,
                    "length": len(content),
                    "source_id": str(document.source_id),
                    "source_url": document.url,
                    "source_title": document.title,
                    "extracted_document_id": str(document.document_id),
                    "extracted_text_hash": document.extracted_text_hash,
                },
            )
        )
    return records


def describe_chunks(chunks: list[ChunkRecord], *, preview_chars: int = 120) -> str:
    """Return a human-readable chunk summary for one source."""
    if not chunks:
        return "No chunks."

    source_ids = {chunk.source_id for chunk in chunks}
    if len(source_ids) > 1:
        raise ChunkingError("Chunk inspection requires chunks from a single source.")

    first_chunk = chunks[0]
    lines = [
        f"{len(chunks)} chunks from {first_chunk.title}",
        f"source_id={first_chunk.source_id} url={first_chunk.url}",
    ]
    for chunk in chunks:
        preview = shorten(" ".join(chunk.content.split()), width=preview_chars, placeholder="...")
        lines.append(f"  [{chunk.chunk_index:03d}] {len(chunk.content):>5} chars  {preview}")
    return "\n".join(lines)
