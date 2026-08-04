"""Input routing for the ScholarSource v2 normalization boundary."""

from backend.rag.input_adapters.book_metadata import BookMetadataAdapter
from backend.rag.input_adapters.book_url import BookUrlAdapter
from backend.rag.input_adapters.dispatcher import (
    AdapterDispatcher,
    InputAdapter,
    PrimaryInputSelection,
    select_primary_input,
)
from backend.rag.input_adapters.isbn import (
    CachedIsbnMetadataProvider,
    IsbnAdapter,
    IsbnMetadata,
    IsbnMetadataProvider,
    canonicalize_isbn,
)
from backend.rag.input_adapters.references import InputSourceReference
from backend.rag.input_adapters.topic_list import TopicListAdapter
from backend.rag.input_adapters.uploaded_pdf import UploadedPdfAdapter
from backend.rag.input_adapters.url_page import (
    LearningOutline,
    LearningOutlineDeriver,
    StructuredLearningOutlineDeriver,
    UrlPageAdapter,
)

__all__ = [
    "AdapterDispatcher",
    "BookUrlAdapter",
    "BookMetadataAdapter",
    "InputAdapter",
    "InputSourceReference",
    "CachedIsbnMetadataProvider",
    "IsbnAdapter",
    "IsbnMetadata",
    "IsbnMetadataProvider",
    "PrimaryInputSelection",
    "TopicListAdapter",
    "UploadedPdfAdapter",
    "LearningOutline",
    "LearningOutlineDeriver",
    "StructuredLearningOutlineDeriver",
    "UrlPageAdapter",
    "canonicalize_isbn",
    "select_primary_input",
]
