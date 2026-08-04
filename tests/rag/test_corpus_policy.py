"""Corpus tenancy policy tests (plan step 0.6.8)."""

from uuid import uuid4

import pytest

from backend.rag.errors import CorpusPolicyError
from backend.rag.models import SourceRecord
from backend.rag.sources.catalog import CatalogSourceCollector
from backend.rag.sources.corpus import (
    CORPUS_ELIGIBLE_SOURCE_TYPES,
    assert_corpus_eligible,
    is_corpus_eligible,
)


def _source(source_type: str) -> SourceRecord:
    return SourceRecord(
        source_id=uuid4(),
        url="https://ocw.mit.edu/statics",
        normalized_url="https://ocw.mit.edu/statics",
        title="Statics Notes",
        source_type=source_type,
    )


@pytest.mark.parametrize("source_type", sorted(CORPUS_ELIGIBLE_SOURCE_TYPES))
def test_pipeline_discovered_sources_may_enter_the_corpus(source_type: str) -> None:
    assert is_corpus_eligible(source_type) is True
    assert_corpus_eligible(_source(source_type))


@pytest.mark.parametrize("source_type", ["course_url", "book_url", "uploaded_pdf", "user_supplied", ""])
def test_user_supplied_sources_may_not_enter_the_corpus(source_type: str) -> None:
    assert is_corpus_eligible(source_type) is False
    with pytest.raises(CorpusPolicyError, match="may not enter the shared corpus"):
        assert_corpus_eligible(_source(source_type))


def test_unrecognized_source_type_fails_closed() -> None:
    """A new input path cannot reach the corpus without an explicit decision."""
    with pytest.raises(CorpusPolicyError):
        assert_corpus_eligible(_source("some_future_input_type"))


def test_collector_and_catalog_source_types_stay_corpus_eligible() -> None:
    """The two producers of shared-corpus sources must keep matching the policy."""
    catalog = CatalogSourceCollector()
    catalog_sources = catalog.collect(catalog.topics()[0])

    assert is_corpus_eligible("web_search")
    assert catalog_sources
    assert all(is_corpus_eligible(source.source_type) for source in catalog_sources)
