from uuid import uuid4

import pytest

from backend.rag.chunking.chunker import CHUNKING_METHOD, chunk_document, chunk_text, describe_chunks
from backend.rag.config import RagSettings
from backend.rag.errors import ChunkingError
from backend.rag.hashing import sha256_text
from backend.rag.models import ExtractedDocument, ExtractionStatus


def _paragraph(label: str) -> str:
    sentence = (
        f"{label} explains equilibrium, reactions, diagrams, and the way a "
        "student should connect definitions to worked examples."
    )
    return " ".join([sentence] * 4)


def _document(*, persisted: bool = True) -> ExtractedDocument:
    text = "\n\n".join([_paragraph("First"), _paragraph("Second"), _paragraph("Third")])
    return ExtractedDocument(
        document_id=uuid4() if persisted else None,
        source_id=uuid4(),
        url="https://ocw.mit.edu/statics",
        title="Statics Notes",
        text=text,
        extracted_text_hash=sha256_text(text),
        extraction_status=ExtractionStatus.COMPLETED,
    )


def test_chunk_document_preserves_source_metadata_on_every_chunk() -> None:
    settings = RagSettings(chunk_target_chars=360, chunk_overlap_chars=80, chunk_min_chars=120)
    document = _document()

    chunks = chunk_document(document, settings=settings)

    assert len(chunks) > 1
    for index, chunk in enumerate(chunks):
        assert chunk.source_id == document.source_id
        assert chunk.extracted_document_id == document.document_id
        assert chunk.url == document.url
        assert chunk.title == document.title
        assert chunk.chunk_index == index
        assert chunk.metadata["chunk_index"] == index
        assert chunk.metadata["source_order"] == index
        assert chunk.content_hash == sha256_text(chunk.content)
        assert chunk.embedding_model == settings.embedding_model
        assert chunk.metadata["chunking_method"] == CHUNKING_METHOD
        assert chunk.metadata["source_id"] == str(document.source_id)
        assert chunk.metadata["source_url"] == document.url
        assert chunk.metadata["source_title"] == document.title
        assert chunk.metadata["extracted_document_id"] == str(document.document_id)
        assert chunk.metadata["extracted_text_hash"] == document.extracted_text_hash


def test_chunk_document_preserves_chunk_order_within_source() -> None:
    settings = RagSettings(chunk_target_chars=150, chunk_overlap_chars=25, chunk_min_chars=40)
    markers = ["ORDER_MARKER_000", "ORDER_MARKER_001", "ORDER_MARKER_002"]
    text = "\n\n".join(
        f"{marker} introduces a distinct source section for ordering checks. The section ends with stable filler text."
        for marker in markers
    )
    document = ExtractedDocument(
        document_id=uuid4(),
        source_id=uuid4(),
        url="https://ocw.mit.edu/ordered-notes",
        title="Ordered Notes",
        text=text,
        extracted_text_hash=sha256_text(text),
        extraction_status=ExtractionStatus.COMPLETED,
    )

    chunks = chunk_document(document, settings=settings)

    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert [chunk.metadata["source_order"] for chunk in chunks] == list(range(len(chunks)))
    assert [marker for chunk in chunks for marker in markers if marker in chunk.content] == markers


def test_chunk_document_requires_persisted_document_for_traceability() -> None:
    with pytest.raises(ChunkingError, match="persisted before chunking"):
        chunk_document(_document(persisted=False), settings=RagSettings())


def test_chunk_text_returns_no_chunks_for_blank_text() -> None:
    assert chunk_text(" \n\n\t ", settings=RagSettings()) == []


def test_describe_chunks_returns_inspection_summary_for_single_source() -> None:
    settings = RagSettings(chunk_target_chars=360, chunk_overlap_chars=80, chunk_min_chars=120)
    document = _document()
    chunks = chunk_document(document, settings=settings)

    description = describe_chunks(chunks, preview_chars=80)

    assert f"{len(chunks)} chunks from {document.title}" in description
    assert f"source_id={document.source_id} url={document.url}" in description
    assert "[000]" in description
    assert "chars" in description
    assert "equilibrium" in description


def test_describe_chunks_returns_empty_message_when_no_chunks_exist() -> None:
    assert describe_chunks([]) == "No chunks."


def test_describe_chunks_rejects_mixed_source_chunks() -> None:
    settings = RagSettings(chunk_target_chars=360, chunk_overlap_chars=80, chunk_min_chars=120)
    first_chunk = chunk_document(_document(), settings=settings)[0]
    second_chunk = chunk_document(_document(), settings=settings)[0]

    with pytest.raises(ChunkingError, match="single source"):
        describe_chunks([first_chunk, second_chunk])
