"""Domain errors for the ScholarSource RAG pipeline."""

from __future__ import annotations


class RagError(Exception):
    """Base class for expected RAG pipeline failures."""


class SourceCollectionError(RagError):
    """Raised when candidate sources cannot be collected for a run."""


class SourceRejectedError(RagError):
    """Raised when a candidate source fails source-quality checks."""


class ExtractionError(RagError):
    """Raised when text cannot be extracted from an accepted source."""


class ChunkingError(RagError):
    """Raised when extracted text cannot be converted into valid chunks."""


class EmbeddingError(RagError):
    """Raised when chunk embeddings cannot be generated or validated."""


class VectorStoreError(RagError):
    """Raised when Supabase/pgvector storage or search fails."""


class RetrievalError(RagError):
    """Raised when retrieval cannot return traceable chunk results."""


class SynthesisError(RagError):
    """Raised when answer synthesis fails after valid evidence exists."""


class InputNormalizationError(RagError):
    """Raised when a validated API request cannot enter input normalization."""


class AmbiguousLearningInputError(InputNormalizationError):
    """Raised when a request contains more than one primary learning input."""


class UnsupportedLearningInputError(InputNormalizationError):
    """Raised when a request does not contain a complete supported primary input."""
