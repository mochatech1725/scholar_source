"""Collect candidate source records from Serper web search."""

from __future__ import annotations

import os

import httpx

from backend.rag.config import RagSettings
from backend.rag.errors import SourceCollectionError
from backend.rag.models import SourceRecord
from backend.rag.sources.policy import normalize_url

SERPER_SEARCH_URL = "https://google.serper.dev/search"


class SerperSourceCollector:
    """Turn deterministic queries into deduplicated candidate sources."""

    def __init__(self, settings: RagSettings, api_key: str | None = None) -> None:
        self._settings = settings
        self._api_key = api_key or os.getenv("SERPER_API_KEY", "")
        if not self._api_key:
            raise SourceCollectionError("SERPER_API_KEY is not configured.")

    def collect(self, queries: list[str]) -> list[SourceRecord]:
        """Run each query and return unique candidates in stable order."""
        seen: set[str] = set()
        candidates: list[SourceRecord] = []
        with httpx.Client(timeout=self._settings.fetch_timeout_seconds) as client:
            for query in queries:
                for record in self._search(client, query):
                    if record.normalized_url in seen:
                        continue
                    seen.add(record.normalized_url)
                    candidates.append(record)
                    if len(candidates) >= self._settings.max_sources_per_run:
                        return candidates
        return candidates

    def _search(self, client: httpx.Client, query: str) -> list[SourceRecord]:
        response = client.post(
            SERPER_SEARCH_URL,
            headers={"X-API-KEY": self._api_key, "Content-Type": "application/json"},
            json={"q": query, "num": self._settings.results_per_query},
        )
        if response.status_code != 200:
            raise SourceCollectionError(f"Serper returned {response.status_code} for query {query!r}.")

        records: list[SourceRecord] = []
        for item in response.json().get("organic", []):
            url = item.get("link", "")
            if not url:
                continue
            records.append(
                SourceRecord(
                    url=url,
                    normalized_url=normalize_url(url),
                    title=item.get("title", url),
                    source_type="web_search",
                    metadata={"query": query, "serper_position": item.get("position")},
                )
            )
        return records
