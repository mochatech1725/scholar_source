"""Seed-catalog source collection: the deterministic first source type.

The catalog is a versioned JSON file mapping normalized topics to known-good
URLs. It exists so the input side of the pipeline is perfectly stable while
extraction, chunking, embedding, and retrieval are being built (implementation
plan 1.2.2 and 1.2.3). Search-based collection is layered on afterward.
"""

from __future__ import annotations

import json
from pathlib import Path

from backend.rag.errors import SourceCollectionError
from backend.rag.models import SourceRecord
from backend.rag.sources.policy import normalize_url
from backend.rag.sources.queries import normalize_topic

CATALOG_PATH = Path(__file__).parent / "catalog.json"


class CatalogSourceCollector:
    """Return hand-curated candidate sources for a known topic."""

    def __init__(self, catalog_path: Path = CATALOG_PATH) -> None:
        if not catalog_path.exists():
            raise SourceCollectionError(f"Source catalog not found at {catalog_path}.")
        self._catalog: dict[str, list[dict[str, str]]] = json.loads(catalog_path.read_text(encoding="utf-8"))

    def topics(self) -> list[str]:
        """Return the topics the catalog can answer, for inspection and tests."""
        return sorted(self._catalog)

    def collect(self, topic: str) -> list[SourceRecord]:
        """Return catalog entries for the topic, empty when unknown.

        An unknown topic is not an error: the pipeline falls through to the
        search collector (or, before that exists, reports no sources).
        """
        entries = self._catalog.get(normalize_topic(topic).casefold(), [])
        return [
            SourceRecord(
                url=entry["url"],
                normalized_url=normalize_url(entry["url"]),
                title=entry.get("title", entry["url"]),
                source_type="seed_catalog",
                metadata={"tier": 1, "collector": "catalog"},
            )
            for entry in entries
        ]
