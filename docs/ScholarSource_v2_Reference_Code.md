# ScholarSource v2 Reference Code

This companion file holds the concrete reference snippets for `docs/ScholarSource_v2_Implementation_Plan.md`. The implementation plan stays focused on the build order, learning goals, verification steps, and decision records.

Use this file as review material after writing your own first version of core RAG modules, unless you intentionally decide to waive that authorship rule for a specific support module.

---

## Reference: Target Layout for `backend/rag/`

The empty subdirectories already in the repo map onto this layout. One file
per responsibility, mirrored by `tests/rag/`.

```text
backend/rag/
|-- __init__.py
|-- config.py               # RagSettings, all tunable knobs in one place
|-- errors.py               # domain exception hierarchy
|-- hashing.py              # normalization + SHA-256 helpers
|-- models.py               # shared Pydantic records
|-- pipeline.py             # Phase 1 linear orchestrator (no LangGraph)
|-- sources/
|   |-- __init__.py
|   |-- queries.py          # deterministic search-query templates
|   |-- policy.py           # quality rules matching, fed by rag_domain_policies
|   `-- collector.py        # Serper collection -> SourceRecord
|-- extraction/
|   |-- __init__.py
|   `-- extractor.py        # fetch, HTML/PDF text extraction, cleaning
|-- chunking/
|   |-- __init__.py
|   `-- chunker.py          # deterministic paragraph chunker + inspection
|-- embeddings/
|   |-- __init__.py
|   `-- embedder.py         # OpenAI embeddings with hash dedupe
|-- vector_store/
|   |-- __init__.py
|   `-- client.py           # Supabase/pgvector persistence + search RPCs
|-- retrieval/
|   |-- __init__.py
|   `-- service.py          # semantic + lexical retrieval -> RetrievalHit
|-- reranking/
|   |-- __init__.py
|   `-- reranker.py         # RRF fusion, evidence selection, weak-evidence
|-- synthesis/
|   |-- __init__.py
|   |-- prompt.py           # system prompt + context formatting
|   `-- synthesizer.py      # structured cited synthesis + citation guard
|-- runs/
|   |-- __init__.py
|   `-- logger.py           # rag_runs / rag_run_steps writer
`-- orchestration/
    `-- __init__.py         # empty until Phase 4
```

Design choices that differ from the notebooks and from Codex's guide:

- **The pipeline is synchronous.** It runs inside the Celery worker (like the
  existing crew runner), and `supabase-py` is a synchronous client. Async
  wrappers around sync I/O would be ceremony without concurrency. If a
  retrieval-only endpoint later serves interactive queries from FastAPI, wrap
  the retriever call in `run_in_threadpool` or add an async variant then.
- **The LLM never sees or produces URLs.** Synthesis output references
  evidence only by `chunk_id`; titles and URLs are joined back from stored
  chunk metadata. A hallucinated URL becomes structurally impossible, which is
  your project contract's hard rule.
- **Weak-evidence policy is score-driven**, not model-self-reported. The
  Book 3 notebooks let the model report `confidence`; ScholarSource decides
  from retrieval scores before synthesis is even called.

---

## Reference: Shared Foundations (`config`, `errors`, `hashing`, `models`)

### `backend/rag/config.py`

Every number you will be asked to defend, in one frozen dataclass with the
reasoning attached here rather than scattered through modules.

```python
"""Configuration for the ScholarSource v2 RAG pipeline.

All tunable values live here so Phase 3 evals can sweep them and so every
threshold has one authoritative definition.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RagSettings:
    """Runtime knobs for the deterministic RAG pipeline."""

    # Embeddings: matches the vector(1536) column in rag_embeddings.
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    embedding_batch_size: int = 64

    # Synthesis: temperature 0 + fixed seed per Phase 2 determinism goals.
    chat_model: str = "gpt-4o-mini"
    llm_seed: int = 7
    prompt_version: str = "study-guide-synthesis-v1"

    # Chunking: ~1400 chars is roughly 350 tokens. Large enough that a chunk
    # carries a complete explanation, small enough that retrieval stays
    # precise. Overlap keeps definitions that straddle a boundary retrievable
    # from both neighboring chunks.
    chunk_target_chars: int = 1400
    chunk_overlap_chars: int = 200
    chunk_min_chars: int = 200

    # Retrieval and reranking.
    retrieval_limit: int = 12
    lexical_limit: int = 12
    rrf_k: int = 60
    evidence_limit: int = 6

    # Weak-evidence policy (starting points; tune with Phase 3 evals).
    # Below min_semantic_score a hit is treated as noise. Between the two
    # thresholds evidence is usable but the answer must be softened.
    min_semantic_score: float = 0.25
    weak_semantic_score: float = 0.35
    min_strong_evidence: int = 3

    # Source collection and extraction.
    max_sources_per_run: int = 8
    results_per_query: int = 5
    fetch_timeout_seconds: float = 15.0
    max_fetch_bytes: int = 2_000_000


DEFAULT_SETTINGS = RagSettings()
```

### `backend/rag/errors.py`

Codex's error hierarchy is correct and worth keeping as-is; one addition
(`SourceCollectionError`) covers Serper failures.

```python
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
```

### `backend/rag/hashing.py`

Same shape as Codex's version (it is the standard pattern); kept minimal.

```python
"""Stable hashing helpers for deduplication and run comparison."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def normalize_for_hash(value: str) -> str:
    """Collapse whitespace and case so equivalent text hashes identically."""
    return " ".join(value.split()).casefold()


def sha256_text(value: str) -> str:
    """Return the SHA-256 hex digest of normalized text."""
    return hashlib.sha256(normalize_for_hash(value).encode("utf-8")).hexdigest()


def sha256_json(value: dict[str, Any] | list[Any]) -> str:
    """Return a deterministic SHA-256 digest for JSON-compatible values."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def short_hash(value: str, *, length: int = 12) -> str:
    """Return a short stable hash for trace keys and log lines."""
    if length <= 0:
        raise ValueError("length must be greater than zero.")
    return sha256_text(value)[:length]
```

### `backend/rag/models.py`

Aligned column-for-column with `migrations/001_create_rag_traceability_schema.sql`
so a record maps to a row with no translation layer.

```python
"""Shared Pydantic models for the ScholarSource RAG pipeline."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class QualityStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


class ExtractionStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WeakEvidenceStatus(StrEnum):
    NOT_EVALUATED = "not_evaluated"
    STRONG = "strong"
    WEAK = "weak"
    INSUFFICIENT = "insufficient"


class RagModel(BaseModel):
    """Base model: reject unexpected fields, strip whitespace."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SourceRecord(RagModel):
    source_id: UUID | None = None
    url: str
    normalized_url: str
    title: str
    source_type: str
    quality_status: QualityStatus = QualityStatus.PENDING
    quality_reason: str = ""
    metadata: dict = Field(default_factory=dict)


class ExtractedDocument(RagModel):
    document_id: UUID | None = None
    source_id: UUID
    url: str
    title: str
    text: str = Field(exclude=True, default="")
    extracted_text_hash: str
    extraction_status: ExtractionStatus
    extraction_error: str | None = None
    metadata: dict = Field(default_factory=dict)


class ChunkRecord(RagModel):
    chunk_id: UUID | None = None
    source_id: UUID
    extracted_document_id: UUID | None = None
    url: str
    title: str
    chunk_index: int = Field(ge=0)
    content: str = Field(min_length=1)
    content_hash: str
    embedding_model: str
    token_count: int | None = None
    metadata: dict = Field(default_factory=dict)


class EmbeddingRecord(RagModel):
    chunk_id: UUID
    content_hash: str
    embedding_model: str
    embedding_dimensions: int = Field(gt=0)
    embedding: list[float] = Field(exclude=True, default_factory=list)


class RetrievalHit(RagModel):
    chunk_id: UUID
    source_id: UUID
    url: str
    title: str
    chunk_index: int = Field(ge=0)
    content: str = Field(min_length=1)
    content_hash: str
    semantic_score: float | None = None
    lexical_score: float | None = None


class SelectedEvidence(RagModel):
    chunk_id: UUID
    source_id: UUID
    url: str
    title: str
    chunk_index: int = Field(ge=0)
    content: str = Field(min_length=1)
    semantic_score: float | None = None
    lexical_score: float | None = None
    rerank_score: float
    evidence_rank: int = Field(ge=1)


class RecommendationDraft(RagModel):
    """Model-facing synthesis output. Chunk IDs only — never URLs."""

    resource_title: str
    why_useful: str
    how_to_use: str
    supporting_chunk_ids: list[str] = Field(default_factory=list)


class StudyGuideDraft(RagModel):
    """Raw structured output from the synthesis LLM call."""

    overview: str
    recommendations: list[RecommendationDraft] = Field(default_factory=list)
    limitations: str = ""


class CitedRecommendation(RagModel):
    """User-facing recommendation with citations resolved from storage."""

    resource_title: str
    url: str
    source_title: str
    why_useful: str
    how_to_use: str
    cited_chunk_ids: list[UUID]


class CitedStudyGuide(RagModel):
    overview: str
    recommendations: list[CitedRecommendation] = Field(default_factory=list)
    limitations: str = ""
    weak_evidence_status: WeakEvidenceStatus = WeakEvidenceStatus.NOT_EVALUATED
    weak_evidence_reason: str | None = None
    cited_source_ids: list[UUID] = Field(default_factory=list)


class PipelineResult(RagModel):
    run_id: UUID
    guide: CitedStudyGuide
    evidence: list[SelectedEvidence] = Field(default_factory=list)
    generated_queries: list[str] = Field(default_factory=list)
    completed_at: datetime | None = None
```

---

## Reference: Sources — Deterministic Queries, Collection, Quality Policy

### `backend/rag/sources/queries.py`

The direct fix for your Phase 0 root cause. v1 let an agent invent queries
like `Engineering Mechanics Statics practice exam PDF site:edu` differently on
every run; v2 makes query generation a pure function.

```python
"""Deterministic search-query generation for a normalized student input.

v1's largest instability was LLM-generated search queries changing between
identical runs. v2 expands the normalized input through fixed templates so
the same input always produces the same queries, in the same order.
"""

from __future__ import annotations

QUERY_TEMPLATES: tuple[str, ...] = (
    "{topic} study guide",
    "{topic} lecture notes",
    "{topic} open textbook",
    "{topic} tutorial explained",
    "{topic} practice problems with solutions",
)


def normalize_topic(raw_input: str) -> str:
    """Collapse whitespace so equivalent inputs generate identical queries."""
    return " ".join(raw_input.split())


def generate_search_queries(raw_input: str) -> list[str]:
    """Expand a student topic into a fixed, ordered set of search queries."""
    topic = normalize_topic(raw_input)
    if not topic:
        raise ValueError("Cannot generate search queries for empty input.")
    return [template.format(topic=topic) for template in QUERY_TEMPLATES]
```

### `backend/rag/sources/policy.py`

The plan (1.2.1) asks what makes a source eligible versus rejected. This is
core, human-owned judgment — but the judgment lives in data, not code. The
rules are rows in `rag_domain_policies` (migration 003, the SQL reference
below), seeded
with a starting position matching the golden-case idea in Phase 3
(low-quality sources are tempting). New domains encountered in real runs
(pirated mirrors, fresh answer mills) become an `INSERT`, not a deploy, and
each row carries its own `reason` that surfaces directly in
`quality_reason` for traceability.

One semantic point worth being precise about: this is not an
allowlist/blocklist pair. `preferred` rules are a fast-accept list; a domain
matching no rule at all is still accepted by the default checks. `rejected`
rules are the only hard filter.

This module holds only the pure matching logic. The rule set is loaded once
per pipeline run by `SupabaseVectorStore.fetch_domain_policy()` (the vector
store reference in section 1.6)
and passed in, so `evaluate_source` stays a pure function — same rules, same
record, same decision — and tests construct their own rule sets without
touching the database.

```python
"""Source quality policy: which candidate URLs are eligible for extraction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from backend.security_utils import validate_url
from backend.rag.models import QualityStatus, SourceRecord

MatchType = Literal["domain", "suffix"]
PolicyAction = Literal["rejected", "preferred"]

# Drop analytics/referrer params so one real source maps to one normalized URL.
TRACKING_PARAM_PREFIXES: tuple[str, ...] = ("utm_", "fbclid", "gclid", "ref")


@dataclass(frozen=True)
class DomainRule:
    """One row from rag_domain_policies.

    A 'domain' rule matches the domain and all of its subdomains; a 'suffix'
    rule matches any host ending with the pattern (e.g. '.edu').
    """

    pattern: str
    match_type: MatchType
    policy: PolicyAction
    reason: str | None = None

    def matches(self, domain: str) -> bool:
        if self.match_type == "suffix":
            return domain.endswith(self.pattern)
        return domain == self.pattern or domain.endswith(f".{self.pattern}")


@dataclass(frozen=True)
class DomainPolicy:
    """The full rule set for one pipeline run, loaded from rag_domain_policies."""

    rules: tuple[DomainRule, ...]

    def first_match(self, domain: str, policy: PolicyAction) -> DomainRule | None:
        return next(
            (rule for rule in self.rules if rule.policy == policy and rule.matches(domain)),
            None,
        )


def normalize_url(url: str) -> str:
    """Canonicalize a URL so the same page always maps to one source row.

    Lowercases scheme and host, drops fragments and tracking parameters, and
    strips a trailing slash. This is the dedupe key for rag_sources.
    """
    parts = urlsplit(url.strip())
    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.casefold().startswith(TRACKING_PARAM_PREFIXES)
    ]
    normalized = urlunsplit(
        (
            parts.scheme.casefold(),
            parts.netloc.casefold(),
            parts.path.rstrip("/") or "/",
            urlencode(query_pairs),
            "",
        )
    )
    return normalized


def registered_domain(normalized_url: str) -> str:
    """Return the host with any www prefix removed."""
    host = urlsplit(normalized_url).netloc
    return host.removeprefix("www.")


def evaluate_source(source: SourceRecord, policy: DomainPolicy) -> SourceRecord:
    """Apply the accept/reject policy and return the updated record."""
    if not validate_url(source.url):
        return _decided(source, QualityStatus.REJECTED, "URL failed safety validation.")

    domain = registered_domain(source.normalized_url)
    rejected = policy.first_match(domain, "rejected")
    if rejected is not None:
        detail = rejected.reason or "on the rejected list"
        return _decided(source, QualityStatus.REJECTED, f"Domain {domain} rejected: {detail}.")

    if policy.first_match(domain, "preferred") is not None:
        return _decided(source, QualityStatus.ACCEPTED, f"Domain {domain} is a preferred education source.")

    return _decided(source, QualityStatus.ACCEPTED, f"Domain {domain} passed default checks.")


def _decided(source: SourceRecord, status: QualityStatus, reason: str) -> SourceRecord:
    return source.model_copy(update={"quality_status": status, "quality_reason": reason})
```

### `backend/rag/sources/collector.py`

Serper is already in the stack (`SERPER_API_KEY`). Collection returns pending
records; the policy decides; the store persists both outcomes.

```python
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
```

### `backend/rag/sources/catalog.py` — the first source type

Per the sourcing plan in the learning plan (Phase 1, "Where the sources come
from"), the *first* collector is not search at all: it is a hand-curated seed
catalog. While extraction, chunking, embedding, and retrieval are being
built, the input side of the pipeline stays perfectly stable. The Serper
collector from 5.3 is enabled afterward.

`backend/rag/sources/catalog.json` — starter content matching the Phase 0
baseline topic; add 3–5 URLs per manual test topic as you go:

```json
{
  "engineering mechanics statics": [
    {
      "url": "https://ocw.mit.edu/courses/2-01-elements-of-structures-fall-2006/",
      "title": "MIT OCW 2.01 Elements of Structures"
    },
    {
      "url": "https://eng.libretexts.org/Bookshelves/Mechanical_Engineering/Engineering_Statics_(Baker_and_Haynes)",
      "title": "Engineering Statics (LibreTexts)"
    },
    {
      "url": "https://openstax.org/books/college-physics-2e/pages/9-introduction-to-statics-and-torque",
      "title": "OpenStax College Physics: Statics and Torque"
    }
  ],
  "cellular respiration": [
    {
      "url": "https://openstax.org/books/biology-2e/pages/7-introduction",
      "title": "OpenStax Biology 2e: Cellular Respiration"
    },
    {
      "url": "https://www.khanacademy.org/science/ap-biology/cellular-energetics/cellular-respiration-ap/a/intro-to-cellular-respiration-and-redox",
      "title": "Khan Academy: Intro to Cellular Respiration"
    }
  ]
}
```

`backend/rag/sources/catalog.py`:

```python
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
        self._catalog: dict[str, list[dict[str, str]]] = json.loads(
            catalog_path.read_text(encoding="utf-8")
        )

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
```

Pipeline wiring: in `run_rag_pipeline` (the linear pipeline reference at the
end of Phase 1), the `collect_sources`
step becomes catalog-first with search as the fallback once both collectors
exist:

```python
catalog_candidates = CatalogSourceCollector().collect(topic)
candidates = catalog_candidates or SerperSourceCollector(settings).collect(queries)
```

During the first weeks of Phase 1, use only the catalog line and skip
constructing the Serper collector entirely.

---

## Reference: SQL Migration 003 — Domain Policy Rules

Add as `migrations/003_create_rag_domain_policies.sql` and mirror into
`supabase_schema.sql`. The source quality rules (the policy reference above) live in a table rather than hardcoded constants, so a
pirated mirror or fresh answer mill spotted in a real run is an `INSERT`, not
a code change and redeploy. Each row keeps a `reason` (the audit trail for
why a domain is on the list) and `created_at` (when it got there). The seed
rows below are the day-one policy; the table follows the same
RLS-enabled-no-user-policies pattern as the other `rag_*` infrastructure
tables (service-role client only).

```sql
-- ScholarSource v2 RAG domain policy rules.
-- Replaces the hardcoded REJECTED_DOMAINS / PREFERRED_DOMAINS constants so
-- new domains can be added without a deploy. Not an allowlist/blocklist
-- pair: 'preferred' rows are a fast-accept list, and a domain matching no
-- row is still accepted by default checks. 'rejected' is the only hard
-- filter. A 'domain' rule matches the domain and its subdomains; a 'suffix'
-- rule matches any host ending with the pattern (e.g. '.edu').

CREATE TABLE IF NOT EXISTS rag_domain_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern TEXT NOT NULL,
    match_type TEXT NOT NULL CHECK (match_type IN ('domain', 'suffix')),
    policy TEXT NOT NULL CHECK (policy IN ('rejected', 'preferred')),
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (pattern, match_type)
);

CREATE INDEX IF NOT EXISTS idx_rag_domain_policies_policy
    ON rag_domain_policies(policy);

ALTER TABLE rag_domain_policies ENABLE ROW LEVEL SECURITY;

-- Day-one policy. Rejected: paywalled answer mills, scraped-content
-- aggregators, and pages with no extractable study text. Never cite these.
INSERT INTO rag_domain_policies (pattern, match_type, policy, reason) VALUES
    ('chegg.com', 'domain', 'rejected', 'paywalled answer mill'),
    ('coursehero.com', 'domain', 'rejected', 'paywalled answer mill'),
    ('studocu.com', 'domain', 'rejected', 'scraped-content aggregator'),
    ('scribd.com', 'domain', 'rejected', 'paywalled document aggregator'),
    ('numerade.com', 'domain', 'rejected', 'paywalled answer mill'),
    ('bartleby.com', 'domain', 'rejected', 'paywalled answer mill'),
    ('quizlet.com', 'domain', 'rejected', 'no extractable study text'),
    ('slideshare.net', 'domain', 'rejected', 'no extractable study text'),
    ('pinterest.com', 'domain', 'rejected', 'no extractable study text'),
    ('khanacademy.org', 'domain', 'preferred', 'open education source'),
    ('openstax.org', 'domain', 'preferred', 'open textbook publisher'),
    ('libretexts.org', 'domain', 'preferred', 'open textbook publisher'),
    ('ocw.mit.edu', 'domain', 'preferred', 'open courseware'),
    ('wikipedia.org', 'domain', 'preferred', 'open encyclopedia'),
    ('brilliant.org', 'domain', 'preferred', 'interactive courseware'),
    ('.edu', 'suffix', 'preferred', 'accredited US institution'),
    ('.gov', 'suffix', 'preferred', 'government publication'),
    ('.ac.uk', 'suffix', 'preferred', 'accredited UK institution')
ON CONFLICT (pattern, match_type) DO NOTHING;
```

---

## Reference: Extraction (`backend/rag/extraction/extractor.py`)

Book 1's `extract_text_from_pdf` + `clean_text` generalized to ScholarSource's
real inputs (web pages first, PDFs via the already-installed `pypdf`). The
extraction hash is what makes caching (Phase 2.2) work: same URL, same text,
same hash — skip re-chunking and re-embedding.

```python
"""Fetch accepted sources and extract clean text with failure isolation."""

from __future__ import annotations

import io
import re

import httpx
from lxml import html as lxml_html
from pypdf import PdfReader

from backend.rag.config import RagSettings
from backend.rag.errors import ExtractionError
from backend.rag.hashing import sha256_text
from backend.rag.models import ExtractedDocument, ExtractionStatus, SourceRecord

REMOVED_HTML_NODES = "//script | //style | //nav | //header | //footer | //noscript | //iframe"


def clean_text(text: str) -> str:
    """Normalize whitespace and drop non-printable characters."""
    text = re.sub(r"[ \t]+", " ", text)
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text_from_html(raw_html: str) -> str:
    """Strip boilerplate elements and return readable page text."""
    tree = lxml_html.fromstring(raw_html)
    for element in tree.xpath(REMOVED_HTML_NODES):
        element.drop_tree()
    return clean_text(tree.text_content())


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes, preserving page order."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return clean_text("\n\n".join(pages))


class SourceExtractor:
    """Fetch a source and produce an ExtractedDocument, never raising.

    Per plan step 1.3.4 a single failed fetch must not crash the run, so
    failures come back as records with extraction_status=failed and an error
    message good enough to debug from (plan step 1.3.5).
    """

    def __init__(self, settings: RagSettings) -> None:
        self._settings = settings

    def extract(self, source: SourceRecord) -> ExtractedDocument:
        if source.source_id is None:
            raise ExtractionError("Source must be persisted before extraction.")
        try:
            text = self._fetch_and_extract(source)
        except Exception as error:  # noqa: BLE001 - isolate any fetch failure per 1.3.4
            return self._failed(source, f"{type(error).__name__}: {error}")

        if len(text) < self._settings.chunk_min_chars:
            return self._failed(source, "Page contained no usable text after cleaning.")

        return ExtractedDocument(
            source_id=source.source_id,
            url=source.url,
            title=source.title,
            text=text,
            extracted_text_hash=sha256_text(text),
            extraction_status=ExtractionStatus.COMPLETED,
            metadata={"text_length": len(text)},
        )

    def _fetch_and_extract(self, source: SourceRecord) -> str:
        with httpx.Client(
            timeout=self._settings.fetch_timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "ScholarSourceBot/2.0 (+study resource finder)"},
        ) as client:
            response = client.get(source.url)
            response.raise_for_status()
            if len(response.content) > self._settings.max_fetch_bytes:
                raise ExtractionError(f"Response exceeds {self._settings.max_fetch_bytes} bytes.")

            content_type = response.headers.get("content-type", "").casefold()
            if "pdf" in content_type or source.url.casefold().endswith(".pdf"):
                return extract_text_from_pdf(response.content)
            return extract_text_from_html(response.text)

    def _failed(self, source: SourceRecord, error: str) -> ExtractedDocument:
        return ExtractedDocument(
            source_id=source.source_id,
            url=source.url,
            title=source.title,
            text="",
            extracted_text_hash=sha256_text(source.normalized_url),
            extraction_status=ExtractionStatus.FAILED,
            extraction_error=error[:500],
        )
```

---

## Reference: Chunking (`backend/rag/chunking/chunker.py`)

Deliberate departure from the course: Book 1 (and your tutorial solution) use
LangChain's `SemanticChunker`, which needs sentence-transformers and produces
boundaries that shift when the chunking model changes. ScholarSource v2's
priority is *repeatability*, so the chunker below is a pure function over
text: paragraph-aware packing with sentence-level splitting for oversized
paragraphs and fixed-size overlap. Semantic chunking stays available as a
Phase 3 experiment once evals can measure whether it actually retrieves
better.

Decision for 1.4.1: start with `chunk_target_chars = 1400`,
`chunk_overlap_chars = 200`, and `chunk_min_chars = 200` in `RagSettings`.
Your defense: ~1400 characters is roughly 350 tokens, which is large enough to
hold one complete explanation from a study guide while still being narrow enough
for precise retrieval. A 200-character overlap keeps boundary-crossing concepts
retrievable from either neighboring chunk; for example, if a term is introduced
near the end of one chunk and explained at the start of the next, both chunks
still carry enough shared context for embeddings and reranking. The overlap is
deliberately smaller than the chunk target so duplicate context helps recall
without flooding storage or retrieval with near-identical chunks.

Verification for 1.4.5: `tests/rag/test_chunker.py` asserts that
representative multi-paragraph sources produce several chunks, every normal
chunk meets `chunk_min_chars`, and no chunk exceeds
`chunk_target_chars + chunk_overlap_chars + 2`. The `+ 2` accounts for the
paragraph separator added when overlap is carried into the next chunk. A
separate test covers an oversized sentence with no punctuation so extracted
text without clean sentence boundaries still stays within the retrieval-size
band.

```python
"""Deterministic paragraph chunking with overlap and metadata preservation."""

from __future__ import annotations

import re
from textwrap import shorten

from backend.rag.config import RagSettings
from backend.rag.errors import ChunkingError
from backend.rag.hashing import sha256_text
from backend.rag.models import ChunkRecord, ExtractedDocument

SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


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
        if current and len(current) + len(sentence) + 1 > target_chars:
            pieces.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
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
    for unit in units:
        if current and len(current) + len(unit) + 2 > settings.chunk_target_chars:
            chunks.append(current)
            # Carry the tail of the previous chunk forward as overlap.
            overlap = current[-settings.chunk_overlap_chars :]
            current = f"{overlap}\n\n{unit}"
        else:
            current = f"{current}\n\n{unit}".strip()
    if len(current) >= settings.chunk_min_chars or not chunks:
        chunks.append(current)
    else:
        chunks[-1] = f"{chunks[-1]}\n\n{current}"
    return chunks


def chunk_document(document: ExtractedDocument, *, settings: RagSettings) -> list[ChunkRecord]:
    """Convert an extracted document into ordered, hashable chunk records."""
    if document.document_id is None:
        raise ChunkingError("Document must be persisted before chunking.")
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
                    "chunking_method": "paragraph_pack_v1",
                    "chunk_target_chars": settings.chunk_target_chars,
                    "chunk_overlap_chars": settings.chunk_overlap_chars,
                    "length": len(content),
                },
            )
        )
    return records


def describe_chunks(chunks: list[ChunkRecord], *, preview_chars: int = 120) -> str:
    """Human-readable chunk inspection for one source (plan step 1.4.4)."""
    if not chunks:
        return "No chunks."
    lines = [f"{len(chunks)} chunks from {chunks[0].title}"]
    for chunk in chunks:
        preview = shorten(" ".join(chunk.content.split()), width=preview_chars, placeholder="...")
        lines.append(f"  [{chunk.chunk_index:03d}] {len(chunk.content):>5} chars  {preview}")
    return "\n".join(lines)
```

---

## Reference: Embeddings (`backend/rag/embeddings/embedder.py`)

Book 1's embed-validate-upload flow with two ScholarSource changes: OpenAI
embeddings through `langchain-openai` (already pinned, traces to LangSmith),
and hash-based dedupe against `rag_embeddings` before any provider call
(plan 1.5.4, 2.3.2). The count and dimension validations are kept exactly as
the course teaches them.

```python
"""Generate OpenAI embeddings for chunks that do not already have one."""

from __future__ import annotations

from langchain_openai import OpenAIEmbeddings

from backend.rag.config import RagSettings
from backend.rag.errors import EmbeddingError
from backend.rag.models import ChunkRecord, EmbeddingRecord
from backend.rag.vector_store.client import SupabaseVectorStore


class RagEmbedder:
    """Embed new chunk content, skipping content already embedded."""

    def __init__(
        self,
        store: SupabaseVectorStore,
        settings: RagSettings,
        embeddings: OpenAIEmbeddings | None = None,
    ) -> None:
        self._store = store
        self._settings = settings
        self._embeddings = embeddings or OpenAIEmbeddings(
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
            chunk_size=settings.embedding_batch_size,
        )

    def embed_missing(self, chunks: list[ChunkRecord]) -> tuple[list[EmbeddingRecord], int]:
        """Embed chunks with no stored embedding; return (records, skipped)."""
        if not chunks:
            return [], 0
        if any(chunk.chunk_id is None for chunk in chunks):
            raise EmbeddingError("Chunks must be persisted before embedding.")

        existing = self._store.existing_embedding_hashes(
            [chunk.content_hash for chunk in chunks], self._settings.embedding_model
        )
        pending = [chunk for chunk in chunks if chunk.content_hash not in existing]
        skipped = len(chunks) - len(pending)
        if not pending:
            return [], skipped

        vectors = self._embeddings.embed_documents([chunk.content for chunk in pending])
        self._validate(pending, vectors)

        records = [
            EmbeddingRecord(
                chunk_id=chunk.chunk_id,
                content_hash=chunk.content_hash,
                embedding_model=self._settings.embedding_model,
                embedding_dimensions=self._settings.embedding_dimensions,
                embedding=vector,
            )
            for chunk, vector in zip(pending, vectors)
        ]
        return records, skipped

    def _validate(self, chunks: list[ChunkRecord], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise EmbeddingError(
                f"Embedding count {len(vectors)} does not match chunk count {len(chunks)}."
            )
        bad_sizes = {len(v) for v in vectors if len(v) != self._settings.embedding_dimensions}
        if bad_sizes:
            raise EmbeddingError(
                f"Expected {self._settings.embedding_dimensions}-dim vectors, found {sorted(bad_sizes)}."
            )
```

Plain-English answer for plan step 1.5.6: the embedding is a list of 1536
numbers that places the chunk's meaning as a point in space, where chunks that
talk about the same idea sit close together even when they share no exact
words — that closeness (cosine similarity) is what retrieval measures.

---

## Reference: SQL Migration 002 — Search Functions

Add as `migrations/002_create_rag_search_functions.sql` and mirror into
`supabase_schema.sql`. `supabase-py` cannot
express the pgvector `<=>` operator through PostgREST, so similarity search
and lexical search live in SQL functions called via `client.rpc(...)`. This
is the pgvector translation of Qdrant's `query_points`.

```sql
-- ScholarSource v2 RAG search functions.
-- Semantic search: pgvector cosine similarity over rag_embeddings.
-- Lexical search: Postgres full-text search over rag_chunks.content.
-- Both are called through PostgREST RPC by the service-role client only;
-- rag_chunks/rag_embeddings have RLS enabled with no user policies.

CREATE INDEX IF NOT EXISTS idx_rag_chunks_content_fts
    ON rag_chunks USING gin (to_tsvector('english', content));

CREATE OR REPLACE FUNCTION match_rag_chunks(
    query_embedding vector(1536),
    match_limit INT DEFAULT 12,
    model_filter TEXT DEFAULT 'text-embedding-3-small'
)
RETURNS TABLE (
    chunk_id UUID,
    source_id UUID,
    url TEXT,
    title TEXT,
    chunk_index INT,
    content TEXT,
    content_hash TEXT,
    embedding_model TEXT,
    similarity DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        c.id,
        c.source_id,
        c.url,
        c.title,
        c.chunk_index,
        c.content,
        c.content_hash,
        e.embedding_model,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM rag_embeddings e
    JOIN rag_chunks c ON c.id = e.chunk_id
    WHERE e.embedding_model = model_filter
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_limit;
$$;

CREATE OR REPLACE FUNCTION search_rag_chunks_lexical(
    query_text TEXT,
    match_limit INT DEFAULT 12
)
RETURNS TABLE (
    chunk_id UUID,
    source_id UUID,
    url TEXT,
    title TEXT,
    chunk_index INT,
    content TEXT,
    content_hash TEXT,
    lexical_score REAL
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        c.id,
        c.source_id,
        c.url,
        c.title,
        c.chunk_index,
        c.content,
        c.content_hash,
        ts_rank(
            to_tsvector('english', c.content),
            websearch_to_tsquery('english', query_text)
        ) AS lexical_score
    FROM rag_chunks c
    WHERE to_tsvector('english', c.content)
          @@ websearch_to_tsquery('english', query_text)
    ORDER BY lexical_score DESC
    LIMIT match_limit;
$$;
```

Notes:

- `1 - (embedding <=> query)` converts cosine distance to similarity so scores
  read the same way as the Qdrant scores in the course (higher is better,
  roughly 0–1 for normalized vectors).
- Full-text search replaces the course's hand-built sparse vocabulary. The
  vocabulary approach requires rebuilding indices whenever the corpus changes;
  `to_tsvector` handles stemming and new documents for free.
- The HNSW index (`idx_rag_embeddings_vector_hnsw`) covers vector-distance
  ordering. Migration 005 adds the supporting retrieval indexes for
  model-filtered semantic search and source-ordered chunk inspection.

---

## Reference: Vector Store (`backend/rag/vector_store/client.py`)

The Qdrant-to-Postgres translation from the plan's table, made concrete.
Everything the course did with `client.upsert` / `client.query_points` becomes
Supabase table writes and the two SQL functions from migration 002 (the
reference above). Uses the
service-role client because the `rag_*` content tables have RLS enabled with
no user policies (they are shared infrastructure, not per-user data).

`fetch_domain_policy` fails loudly on an empty table rather than returning an
empty rule set: with no rules, every answer mill would sail through the
default-accept path, and that failure mode should be impossible to miss.

```python
"""Supabase/pgvector persistence and search for the RAG pipeline."""

from __future__ import annotations

from uuid import UUID

from supabase import Client

from backend.database import get_supabase_client
from backend.rag.errors import VectorStoreError
from backend.rag.models import (
    ChunkRecord,
    EmbeddingRecord,
    ExtractedDocument,
    RetrievalHit,
    SourceRecord,
)
from backend.rag.sources.policy import DomainPolicy, DomainRule


class SupabaseVectorStore:
    """Persist sources, documents, chunks, and embeddings; run searches."""

    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_supabase_client(use_service_role=True)

    def upsert_source(self, source: SourceRecord) -> UUID:
        """Insert or refresh a source row keyed by normalized_url."""
        response = (
            self._client.table("rag_sources")
            .upsert(
                {
                    "url": source.url,
                    "normalized_url": source.normalized_url,
                    "title": source.title,
                    "source_type": source.source_type,
                    "quality_status": source.quality_status.value,
                    "quality_reason": source.quality_reason,
                    "metadata": source.metadata,
                },
                on_conflict="normalized_url",
            )
            .execute()
        )
        if not response.data:
            raise VectorStoreError(f"Failed to upsert source {source.normalized_url}.")
        return UUID(response.data[0]["id"])

    def record_rejection(self, run_id: UUID, source: SourceRecord) -> None:
        """Persist a rejected candidate for traceability (plan 1.2.1)."""
        self._client.table("rag_source_rejections").insert(
            {
                "run_id": str(run_id),
                "url": source.url,
                "normalized_url": source.normalized_url,
                "rejection_reason": source.quality_reason,
                "metadata": source.metadata,
            }
        ).execute()

    def fetch_domain_policy(self) -> DomainPolicy:
        """Load the source quality rule set, once per pipeline run."""
        response = (
            self._client.table("rag_domain_policies")
            .select("pattern, match_type, policy, reason")
            .order("pattern")
            .execute()
        )
        if not response.data:
            raise VectorStoreError(
                "rag_domain_policies is empty; apply migration 003 seed rows."
            )
        return DomainPolicy(
            rules=tuple(
                DomainRule(
                    pattern=row["pattern"],
                    match_type=row["match_type"],
                    policy=row["policy"],
                    reason=row["reason"],
                )
                for row in response.data
            )
        )

    def find_extracted_document(self, source_id: UUID, text_hash: str) -> UUID | None:
        """Return an existing document id when content is unchanged (cache hit)."""
        response = (
            self._client.table("rag_extracted_documents")
            .select("id")
            .eq("source_id", str(source_id))
            .eq("extracted_text_hash", text_hash)
            .limit(1)
            .execute()
        )
        return UUID(response.data[0]["id"]) if response.data else None

    def insert_extracted_document(self, document: ExtractedDocument) -> UUID:
        response = (
            self._client.table("rag_extracted_documents")
            .upsert(
                {
                    "source_id": str(document.source_id),
                    "url": document.url,
                    "title": document.title,
                    "extracted_text_hash": document.extracted_text_hash,
                    "extraction_status": document.extraction_status.value,
                    "extraction_error": document.extraction_error,
                    "metadata": document.metadata,
                },
                on_conflict="source_id,extracted_text_hash",
            )
            .execute()
        )
        if not response.data:
            raise VectorStoreError(f"Failed to insert extracted document for {document.url}.")
        return UUID(response.data[0]["id"])

    def upsert_chunks(self, chunks: list[ChunkRecord]) -> list[UUID]:
        """Upsert chunk rows and return their ids in input order."""
        if not chunks:
            return []
        rows = [
            {
                "source_id": str(chunk.source_id),
                "extracted_document_id": str(chunk.extracted_document_id)
                if chunk.extracted_document_id
                else None,
                "url": chunk.url,
                "title": chunk.title,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "content_hash": chunk.content_hash,
                "embedding_model": chunk.embedding_model,
                "token_count": chunk.token_count,
                "metadata": chunk.metadata,
            }
            for chunk in chunks
        ]
        response = (
            self._client.table("rag_chunks")
            .upsert(rows, on_conflict="source_id,chunk_index,content_hash")
            .execute()
        )
        if len(response.data) != len(chunks):
            raise VectorStoreError("Chunk upsert returned an unexpected row count.")
        return [UUID(row["id"]) for row in response.data]

    def existing_embedding_hashes(self, content_hashes: list[str], embedding_model: str) -> set[str]:
        """Return hashes already embedded with this model (dedupe check)."""
        if not content_hashes:
            return set()
        response = (
            self._client.table("rag_embeddings")
            .select("content_hash")
            .eq("embedding_model", embedding_model)
            .in_("content_hash", content_hashes)
            .execute()
        )
        return {row["content_hash"] for row in response.data}

    def insert_embeddings(self, embeddings: list[EmbeddingRecord]) -> int:
        """Insert embedding rows, ignoring rows that already exist."""
        if not embeddings:
            return 0
        rows = [
            {
                "chunk_id": str(record.chunk_id),
                "content_hash": record.content_hash,
                "embedding_model": record.embedding_model,
                "embedding_dimensions": record.embedding_dimensions,
                "embedding": record.embedding,
            }
            for record in embeddings
        ]
        response = (
            self._client.table("rag_embeddings")
            .upsert(rows, on_conflict="chunk_id,embedding_model", ignore_duplicates=True)
            .execute()
        )
        return len(response.data)

    def semantic_search(
        self, query_embedding: list[float], *, limit: int, embedding_model: str
    ) -> list[RetrievalHit]:
        """Cosine-similarity search through the match_rag_chunks function."""
        response = self._client.rpc(
            "match_rag_chunks",
            {
                "query_embedding": query_embedding,
                "match_limit": limit,
                "model_filter": embedding_model,
            },
        ).execute()
        return [
            _hit_from_row(row, semantic_score=float(row["similarity"]))
            for row in response.data
        ]

    def lexical_search(self, query_text: str, *, limit: int) -> list[RetrievalHit]:
        """Full-text search through the search_rag_chunks_lexical function."""
        response = self._client.rpc(
            "search_rag_chunks_lexical",
            {"query_text": query_text, "match_limit": limit},
        ).execute()
        return [
            _hit_from_row(row, lexical_score=float(row["lexical_score"]))
            for row in response.data
        ]

    def chunks_for_source(self, source_id: UUID) -> list[dict]:
        """Return stored chunks for one source (plan step 1.6.5 inspection)."""
        response = (
            self._client.table("rag_chunks")
            .select("id, chunk_index, content, content_hash")
            .eq("source_id", str(source_id))
            .order("chunk_index")
            .execute()
        )
        return response.data

    def delete_source(self, normalized_url: str) -> None:
        """Remove one source and, via cascades, its documents/chunks/embeddings.

        Local development reset only (plan step 1.6.4).
        """
        self._client.table("rag_sources").delete().eq("normalized_url", normalized_url).execute()


def _hit_from_row(
    row: dict, *, semantic_score: float | None = None, lexical_score: float | None = None
) -> RetrievalHit:
    return RetrievalHit(
        chunk_id=UUID(row["chunk_id"]),
        source_id=UUID(row["source_id"]),
        url=row["url"],
        title=row["title"],
        chunk_index=row["chunk_index"],
        content=row["content"],
        content_hash=row["content_hash"],
        semantic_score=semantic_score,
        lexical_score=lexical_score,
    )
```

---

## Reference: Retrieval (`backend/rag/retrieval/service.py`)

Your tutorial `retrieval/service.py` translated: `embed_query` keeps the rule
that queries embed with the same model as chunks (plan 1.7.1); the Qdrant
`query_points` calls become the two store searches.

```python
"""Semantic and lexical retrieval over stored chunk embeddings."""

from __future__ import annotations

from langchain_openai import OpenAIEmbeddings

from backend.rag.config import RagSettings
from backend.rag.errors import RetrievalError
from backend.rag.models import RetrievalHit
from backend.rag.vector_store.client import SupabaseVectorStore


class ChunkRetriever:
    """Retrieve traceable chunk hits for a student query."""

    def __init__(
        self,
        store: SupabaseVectorStore,
        settings: RagSettings,
        embeddings: OpenAIEmbeddings | None = None,
    ) -> None:
        self._store = store
        self._settings = settings
        self._embeddings = embeddings or OpenAIEmbeddings(
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
        )

    def embed_query(self, query: str) -> list[float]:
        """Embed the query in the same space as stored chunks."""
        if not query.strip():
            raise RetrievalError("Query must not be empty.")
        vector = self._embeddings.embed_query(query)
        if len(vector) != self._settings.embedding_dimensions:
            raise RetrievalError(
                f"Query embedding has {len(vector)} dimensions, "
                f"expected {self._settings.embedding_dimensions}."
            )
        return vector

    def semantic(self, query: str) -> list[RetrievalHit]:
        """Top-k cosine similarity retrieval with scores preserved."""
        return self._store.semantic_search(
            self.embed_query(query),
            limit=self._settings.retrieval_limit,
            embedding_model=self._settings.embedding_model,
        )

    def lexical(self, query: str) -> list[RetrievalHit]:
        """Keyword retrieval via Postgres full-text search."""
        if not query.strip():
            raise RetrievalError("Query must not be empty.")
        return self._store.lexical_search(query, limit=self._settings.lexical_limit)
```

---

## Reference: Reranking (`backend/rag/reranking/reranker.py`)

Book 2's RRF, done in Python instead of inside Qdrant, plus the weak-evidence
assessment the plan requires (1.8.6: define what score is too weak). Both
original scores survive on every evidence item for debugging (1.8.3, 1.8.4).

```python
"""Fuse semantic and lexical retrieval with RRF and select final evidence."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from backend.rag.config import RagSettings
from backend.rag.models import RetrievalHit, SelectedEvidence, WeakEvidenceStatus


def rerank_evidence(
    semantic_hits: list[RetrievalHit],
    lexical_hits: list[RetrievalHit],
    *,
    settings: RagSettings,
) -> list[SelectedEvidence]:
    """Fuse two ranked lists with reciprocal rank fusion.

    RRF scores each chunk by sum(1 / (k + rank)) across the lists it appears
    in, so chunks found by both retrieval methods rise to the top without
    needing to compare raw scores across different scales.
    """
    fused: defaultdict[UUID, float] = defaultdict(float)
    by_id: dict[UUID, RetrievalHit] = {}

    for ranked_list in (semantic_hits, lexical_hits):
        for rank, hit in enumerate(ranked_list, start=1):
            fused[hit.chunk_id] += 1.0 / (settings.rrf_k + rank)
            existing = by_id.get(hit.chunk_id)
            if existing is None:
                by_id[hit.chunk_id] = hit
            else:
                by_id[hit.chunk_id] = existing.model_copy(
                    update={
                        "semantic_score": existing.semantic_score or hit.semantic_score,
                        "lexical_score": existing.lexical_score or hit.lexical_score,
                    }
                )

    ordered = sorted(fused.items(), key=lambda item: (-item[1], str(item[0])))
    evidence: list[SelectedEvidence] = []
    for rank, (chunk_id, score) in enumerate(ordered[: settings.evidence_limit], start=1):
        hit = by_id[chunk_id]
        if _is_noise(hit, settings):
            continue
        evidence.append(
            SelectedEvidence(
                chunk_id=hit.chunk_id,
                source_id=hit.source_id,
                url=hit.url,
                title=hit.title,
                chunk_index=hit.chunk_index,
                content=hit.content,
                semantic_score=hit.semantic_score,
                lexical_score=hit.lexical_score,
                rerank_score=score,
                evidence_rank=rank,
            )
        )
    return evidence


def assess_evidence(
    evidence: list[SelectedEvidence], *, settings: RagSettings
) -> tuple[WeakEvidenceStatus, str | None]:
    """Decide whether the selected evidence supports a confident answer."""
    if not evidence:
        return WeakEvidenceStatus.INSUFFICIENT, "No evidence passed retrieval thresholds."

    strong = [
        item
        for item in evidence
        if item.semantic_score is not None and item.semantic_score >= settings.weak_semantic_score
    ]
    if len(strong) >= settings.min_strong_evidence:
        return WeakEvidenceStatus.STRONG, None
    if strong or any(item.lexical_score for item in evidence):
        return (
            WeakEvidenceStatus.WEAK,
            f"Only {len(strong)} chunks scored above {settings.weak_semantic_score}; "
            f"{settings.min_strong_evidence} required for a confident answer.",
        )
    return WeakEvidenceStatus.INSUFFICIENT, "All retrieved chunks scored below usable thresholds."


def _is_noise(hit: RetrievalHit, settings: RagSettings) -> bool:
    """A semantic-only hit below the floor is noise; lexical hits stay."""
    if hit.lexical_score is not None:
        return False
    return hit.semantic_score is not None and hit.semantic_score < settings.min_semantic_score
```

---

## Reference: Synthesis — Prompt and Cited Generation

### `backend/rag/synthesis/prompt.py`

Book 3's context-only prompt pattern, rewritten for ScholarSource's product
(a study resource guide, not document Q&A) and hardened for the citation
contract. The `[chunk_id: ...]` block format is exactly what you used in
`lib/prompting.py`.

```python
"""System prompt and context formatting for cited study-guide synthesis."""

from __future__ import annotations

from backend.rag.models import SelectedEvidence

SYSTEM_PROMPT = """You are ScholarSource, an assistant that recommends study resources to students.

You will receive a student topic and a set of evidence chunks. Each chunk is
labeled with a chunk_id and comes from a real web resource that has already
been fetched and stored.

Rules:
- Recommend resources using ONLY the provided evidence chunks. Do not use any
  external knowledge about websites, books, or courses.
- Refer to evidence exclusively by chunk_id. Never write a URL. Never invent
  a resource title that does not describe evidence you were given.
- Every recommendation must list the chunk_ids that support it in
  supporting_chunk_ids. Use only chunk_ids that appear in the context.
- If the evidence is thin, contradictory, or off-topic, say so plainly in
  limitations and return fewer recommendations, or none. Never pad weak
  evidence into confident-sounding advice.
- Write for a student: explain why each resource helps and how to use it for
  studying this topic.
"""


def format_evidence_context(evidence: list[SelectedEvidence]) -> str:
    """Format evidence with stable chunk_id labels the model can cite."""
    blocks = [
        f"[chunk_id: {item.chunk_id}]\n[resource: {item.title}]\n{item.content}"
        for item in evidence
    ]
    return "\n\n---\n\n".join(blocks)


def build_user_message(topic: str, context: str) -> str:
    """Assemble the synthesis request message."""
    return f"Student topic: {topic}\n\nEvidence chunks:\n{context}"
```

### `backend/rag/synthesis/synthesizer.py`

Three guarantees the notebooks only gesture at, made structural:

- Insufficient evidence short-circuits *before* any LLM call (your contract:
  do not call synthesis on weak evidence).
- Citations are filtered against the evidence actually provided (Book 3's
  `filter_valid_source_ids`, your `lib/grounding.py`).
- URLs and titles in the final guide are joined from stored evidence by
  chunk_id — the model's output physically cannot introduce a hallucinated
  URL.

```python
"""Cited study-guide synthesis from selected evidence."""

from __future__ import annotations

from uuid import UUID

from langchain_openai import ChatOpenAI

from backend.rag.config import RagSettings
from backend.rag.errors import SynthesisError
from backend.rag.models import (
    CitedRecommendation,
    CitedStudyGuide,
    SelectedEvidence,
    StudyGuideDraft,
    WeakEvidenceStatus,
)
from backend.rag.synthesis.prompt import SYSTEM_PROMPT, build_user_message, format_evidence_context

INSUFFICIENT_MESSAGE = (
    "ScholarSource could not find enough trustworthy material on this topic to "
    "build a study guide. Try a more specific topic, or provide a course page "
    "or textbook to search from."
)

WEAK_PREFIX = (
    "Evidence for this topic was limited, so treat these suggestions as "
    "starting points rather than a complete study plan."
)


class CitedSynthesizer:
    """Generate a study guide whose every claim maps to stored evidence."""

    def __init__(self, settings: RagSettings, llm: ChatOpenAI | None = None) -> None:
        self._settings = settings
        base_llm = llm or ChatOpenAI(
            model=settings.chat_model,
            temperature=0.0,
            seed=settings.llm_seed,
        )
        self._structured_llm = base_llm.with_structured_output(StudyGuideDraft)

    def synthesize(
        self,
        topic: str,
        evidence: list[SelectedEvidence],
        *,
        status: WeakEvidenceStatus,
        status_reason: str | None,
    ) -> CitedStudyGuide:
        """Produce a cited guide, or a transparent refusal without an LLM call."""
        if status is WeakEvidenceStatus.INSUFFICIENT or not evidence:
            return CitedStudyGuide(
                overview=INSUFFICIENT_MESSAGE,
                limitations=status_reason or "No usable evidence was retrieved.",
                weak_evidence_status=WeakEvidenceStatus.INSUFFICIENT,
                weak_evidence_reason=status_reason,
            )

        context = format_evidence_context(evidence)
        draft = self._structured_llm.invoke(
            [
                ("system", SYSTEM_PROMPT),
                ("human", build_user_message(topic, context)),
            ]
        )
        if not isinstance(draft, StudyGuideDraft):
            raise SynthesisError("Synthesis did not return a structured study guide.")
        return self._ground(draft, evidence, status=status, status_reason=status_reason)

    def _ground(
        self,
        draft: StudyGuideDraft,
        evidence: list[SelectedEvidence],
        *,
        status: WeakEvidenceStatus,
        status_reason: str | None,
    ) -> CitedStudyGuide:
        """Resolve citations against provided evidence; drop anything unsupported."""
        by_id = {item.chunk_id: item for item in evidence}
        recommendations: list[CitedRecommendation] = []
        cited_sources: set[UUID] = set()

        for rec in draft.recommendations:
            valid_ids = [
                UUID(raw)
                for raw in rec.supporting_chunk_ids
                if _is_uuid(raw) and UUID(raw) in by_id
            ]
            if not valid_ids:
                continue
            primary = by_id[valid_ids[0]]
            cited_sources.update(by_id[chunk_id].source_id for chunk_id in valid_ids)
            recommendations.append(
                CitedRecommendation(
                    resource_title=rec.resource_title,
                    url=primary.url,
                    source_title=primary.title,
                    why_useful=rec.why_useful,
                    how_to_use=rec.how_to_use,
                    cited_chunk_ids=valid_ids,
                )
            )

        if not recommendations:
            return CitedStudyGuide(
                overview=INSUFFICIENT_MESSAGE,
                limitations="Synthesis produced no recommendations supported by stored evidence.",
                weak_evidence_status=WeakEvidenceStatus.INSUFFICIENT,
                weak_evidence_reason=status_reason,
            )

        overview = draft.overview
        if status is WeakEvidenceStatus.WEAK:
            overview = f"{WEAK_PREFIX}\n\n{overview}"
        return CitedStudyGuide(
            overview=overview,
            recommendations=recommendations,
            limitations=draft.limitations,
            weak_evidence_status=status,
            weak_evidence_reason=status_reason,
            cited_source_ids=sorted(cited_sources, key=str),
        )


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
    except (ValueError, AttributeError, TypeError):
        return False
    return True
```

---

## Reference: The Linear Pipeline (`backend/rag/pipeline.py`)

Phase 1's whole story in one readable function. No LangGraph, no retries, no
routing — those are Phase 4, and only if evals prove they are needed. It
imports `RunLogger` from the run-logging reference in section 2.4; the
module build order builds both together (step 10).

```python
"""Phase 1 linear RAG pipeline: input -> cited study guide."""

from __future__ import annotations

from backend.rag.chunking.chunker import chunk_document
from backend.rag.config import DEFAULT_SETTINGS, RagSettings
from backend.rag.extraction.extractor import SourceExtractor
from backend.rag.embeddings.embedder import RagEmbedder
from backend.rag.models import (
    ExtractionStatus,
    PipelineResult,
    QualityStatus,
)
from backend.rag.reranking.reranker import assess_evidence, rerank_evidence
from backend.rag.retrieval.service import ChunkRetriever
from backend.rag.runs.logger import RunLogger
from backend.rag.sources.collector import SerperSourceCollector
from backend.rag.sources.policy import evaluate_source
from backend.rag.sources.queries import generate_search_queries, normalize_topic
from backend.rag.synthesis.synthesizer import CitedSynthesizer
from backend.rag.vector_store.client import SupabaseVectorStore


def run_rag_pipeline(
    raw_input: str,
    *,
    job_id: str | None = None,
    user_id: str | None = None,
    settings: RagSettings = DEFAULT_SETTINGS,
) -> PipelineResult:
    """Run the full controlled pipeline and return a cited study guide."""
    topic = normalize_topic(raw_input)
    store = SupabaseVectorStore()
    logger = RunLogger()
    run_id = logger.start_run(normalized_input=topic, job_id=job_id, user_id=user_id)

    try:
        with logger.step(run_id, "generate_queries") as out:
            queries = generate_search_queries(topic)
            out["queries"] = queries
        logger.update_run(run_id, generated_queries=queries)

        with logger.step(run_id, "collect_sources") as out:
            domain_policy = store.fetch_domain_policy()
            candidates = SerperSourceCollector(settings).collect(queries)
            accepted = []
            for candidate in candidates:
                decided = evaluate_source(candidate, domain_policy)
                if decided.quality_status is QualityStatus.ACCEPTED:
                    source_id = store.upsert_source(decided)
                    accepted.append(decided.model_copy(update={"source_id": source_id}))
                else:
                    store.record_rejection(run_id, decided)
            out["candidates"] = len(candidates)
            out["accepted"] = len(accepted)
        logger.update_run(
            run_id, candidate_source_urls=[c.normalized_url for c in candidates]
        )

        extractor = SourceExtractor(settings)
        all_chunk_ids: list[str] = []
        with logger.step(run_id, "extract_chunk_embed") as out:
            embedder = RagEmbedder(store, settings)
            embedded_count = 0
            skipped_count = 0
            for source in accepted:
                document = extractor.extract(source)
                if document.extraction_status is not ExtractionStatus.COMPLETED:
                    store.insert_extracted_document(document)
                    continue
                cached_id = store.find_extracted_document(
                    document.source_id, document.extracted_text_hash
                )
                document_id = cached_id or store.insert_extracted_document(document)
                document = document.model_copy(update={"document_id": document_id})

                chunks = chunk_document(document, settings=settings)
                chunk_ids = store.upsert_chunks(chunks)
                chunks = [
                    chunk.model_copy(update={"chunk_id": chunk_id})
                    for chunk, chunk_id in zip(chunks, chunk_ids)
                ]
                all_chunk_ids.extend(str(chunk_id) for chunk_id in chunk_ids)

                records, skipped = embedder.embed_missing(chunks)
                embedded_count += store.insert_embeddings(records)
                skipped_count += skipped
            out["chunks"] = len(all_chunk_ids)
            out["embedded"] = embedded_count
            out["dedupe_skipped"] = skipped_count
        logger.update_run(run_id, chunk_ids=all_chunk_ids)

        retriever = ChunkRetriever(store, settings)
        with logger.step(run_id, "retrieve") as out:
            semantic_hits = retriever.semantic(topic)
            lexical_hits = retriever.lexical(topic)
            out["semantic"] = len(semantic_hits)
            out["lexical"] = len(lexical_hits)
        logger.update_run(
            run_id,
            retrieval_scores=[
                {"chunk_id": str(hit.chunk_id), "semantic_score": hit.semantic_score}
                for hit in semantic_hits
            ],
        )

        with logger.step(run_id, "rerank") as out:
            evidence = rerank_evidence(semantic_hits, lexical_hits, settings=settings)
            status, reason = assess_evidence(evidence, settings=settings)
            out["evidence"] = len(evidence)
            out["weak_evidence_status"] = status.value
        logger.update_run(
            run_id,
            rerank_order=[str(item.chunk_id) for item in evidence],
            final_selected_evidence=[
                item.model_dump(mode="json", exclude={"content"}) for item in evidence
            ],
            weak_evidence_status=status.value,
            weak_evidence_reason=reason,
        )

        with logger.step(run_id, "synthesize") as out:
            guide = CitedSynthesizer(settings).synthesize(
                topic, evidence, status=status, status_reason=reason
            )
            out["recommendations"] = len(guide.recommendations)

        logger.complete_run(
            run_id,
            {
                "final_cited_source_ids": [str(sid) for sid in guide.cited_source_ids],
                "model_name": settings.chat_model,
                "prompt_version": settings.prompt_version,
            },
        )
        return PipelineResult(
            run_id=run_id, guide=guide, evidence=evidence, generated_queries=queries
        )
    except Exception as error:
        logger.fail_run(run_id, {"error_type": type(error).__name__, "message": str(error)[:500]})
        raise
```

---

## Reference: Tests to Write First (`tests/rag/`)

Mirror the module layout. The highest-value tests are the deterministic pure
functions — they need no network, no database, and they encode the properties
the plan asks you to verify.

```python
# tests/rag/test_queries.py
from backend.rag.sources.queries import generate_search_queries


def test_same_input_generates_identical_queries() -> None:
    first = generate_search_queries("  Engineering   Mechanics Statics ")
    second = generate_search_queries("Engineering Mechanics Statics")
    assert first == second


def test_queries_preserve_template_order() -> None:
    queries = generate_search_queries("linear algebra")
    assert queries[0] == "linear algebra study guide"
    assert len(queries) == 5
```

```python
# tests/rag/test_chunker.py
from backend.rag.chunking.chunker import chunk_text
from backend.rag.config import RagSettings

SETTINGS = RagSettings()


def test_chunking_is_deterministic() -> None:
    text = "\n\n".join(f"Paragraph {i}. " + "Sentence content here. " * 20 for i in range(12))
    assert chunk_text(text, settings=SETTINGS) == chunk_text(text, settings=SETTINGS)


def test_consecutive_chunks_share_overlap() -> None:
    text = "\n\n".join("Sentence about statics and forces. " * 15 for _ in range(6))
    chunks = chunk_text(text, settings=SETTINGS)
    assert len(chunks) >= 2
    tail = chunks[0][-SETTINGS.chunk_overlap_chars :]
    assert tail in chunks[1]


def test_no_chunk_wildly_exceeds_target() -> None:
    text = "One very long paragraph. " * 400
    chunks = chunk_text(text, settings=SETTINGS)
    assert all(len(chunk) <= SETTINGS.chunk_target_chars * 2 for chunk in chunks)
```

```python
# tests/rag/test_policy.py
from backend.rag.models import SourceRecord
from backend.rag.sources.policy import DomainPolicy, DomainRule, evaluate_source, normalize_url

POLICY = DomainPolicy(
    rules=(
        DomainRule(pattern="chegg.com", match_type="domain", policy="rejected", reason="paywalled answer mill"),
        DomainRule(pattern=".edu", match_type="suffix", policy="preferred"),
    )
)


def _source(url: str) -> SourceRecord:
    return SourceRecord(url=url, normalized_url=normalize_url(url), title="t", source_type="web_search")


def test_answer_mills_are_rejected() -> None:
    decided = evaluate_source(_source("https://www.chegg.com/homework-help/statics"), POLICY)
    assert decided.quality_status.value == "rejected"
    assert "paywalled answer mill" in decided.quality_reason


def test_edu_domains_are_accepted() -> None:
    decided = evaluate_source(_source("https://ocw.mit.edu/courses/statics"), POLICY)
    assert decided.quality_status.value == "accepted"


def test_unlisted_domains_still_pass_default_checks() -> None:
    decided = evaluate_source(_source("https://statics-notes.example.org/lectures"), POLICY)
    assert decided.quality_status.value == "accepted"


def test_normalize_url_strips_tracking_and_fragments() -> None:
    url = "https://Example.edu/Notes/?utm_source=x&topic=statics#section-2"
    assert normalize_url(url) == "https://example.edu/Notes?topic=statics"
```

```python
# tests/rag/test_reranker.py
from uuid import uuid4

from backend.rag.config import RagSettings
from backend.rag.models import RetrievalHit, WeakEvidenceStatus
from backend.rag.reranking.reranker import assess_evidence, rerank_evidence

SETTINGS = RagSettings()


def _hit(chunk_id, *, semantic=None, lexical=None) -> RetrievalHit:
    return RetrievalHit(
        chunk_id=chunk_id, source_id=uuid4(), url="https://example.edu/x", title="t",
        chunk_index=0, content="c", content_hash="h", semantic_score=semantic, lexical_score=lexical,
    )


def test_chunk_found_by_both_methods_ranks_first() -> None:
    shared, semantic_only, lexical_only = uuid4(), uuid4(), uuid4()
    evidence = rerank_evidence(
        [_hit(shared, semantic=0.8), _hit(semantic_only, semantic=0.9)],
        [_hit(lexical_only, lexical=0.5), _hit(shared, lexical=0.3)],
        settings=SETTINGS,
    )
    assert evidence[0].chunk_id == shared
    assert evidence[0].semantic_score is not None
    assert evidence[0].lexical_score is not None


def test_no_evidence_is_insufficient() -> None:
    status, _reason = assess_evidence([], settings=SETTINGS)
    assert status is WeakEvidenceStatus.INSUFFICIENT
```

```python
# tests/rag/test_synthesizer_grounding.py
from unittest.mock import MagicMock
from uuid import uuid4

from backend.rag.config import RagSettings
from backend.rag.models import (
    RecommendationDraft,
    SelectedEvidence,
    StudyGuideDraft,
    WeakEvidenceStatus,
)
from backend.rag.synthesis.synthesizer import CitedSynthesizer


def _evidence() -> SelectedEvidence:
    return SelectedEvidence(
        chunk_id=uuid4(), source_id=uuid4(), url="https://example.edu/notes",
        title="Statics Notes", chunk_index=0, content="Evidence text.",
        semantic_score=0.8, rerank_score=0.03, evidence_rank=1,
    )


def _synthesizer_with(draft: StudyGuideDraft) -> tuple[CitedSynthesizer, MagicMock]:
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.return_value = draft
    return CitedSynthesizer(RagSettings(), llm=mock_llm), mock_llm


def test_insufficient_evidence_never_calls_the_llm() -> None:
    synthesizer, mock_llm = _synthesizer_with(StudyGuideDraft(overview="unused"))
    guide = synthesizer.synthesize(
        "statics", [], status=WeakEvidenceStatus.INSUFFICIENT, status_reason="none"
    )
    mock_llm.with_structured_output.return_value.invoke.assert_not_called()
    assert guide.weak_evidence_status is WeakEvidenceStatus.INSUFFICIENT
    assert guide.recommendations == []


def test_citations_to_unknown_chunks_are_dropped() -> None:
    evidence = _evidence()
    draft = StudyGuideDraft(
        overview="Guide.",
        recommendations=[
            RecommendationDraft(
                resource_title="Real", why_useful="w", how_to_use="h",
                supporting_chunk_ids=[str(evidence.chunk_id)],
            ),
            RecommendationDraft(
                resource_title="Hallucinated", why_useful="w", how_to_use="h",
                supporting_chunk_ids=[str(uuid4())],
            ),
        ],
    )
    synthesizer, _mock = _synthesizer_with(draft)
    guide = synthesizer.synthesize(
        "statics", [evidence], status=WeakEvidenceStatus.STRONG, status_reason=None
    )
    assert len(guide.recommendations) == 1
    assert guide.recommendations[0].url == evidence.url
```

---

## Reference: Run Logging (`backend/rag/runs/logger.py`)

Writes `rag_runs` and `rag_run_steps` so every Phase 2 question ("what did
this run retrieve, in what order, and why?") is answerable from the database.

```python
"""Structured run logging into rag_runs and rag_run_steps."""

from __future__ import annotations

import time
from contextlib import contextmanager
from collections.abc import Iterator
from datetime import datetime, timezone
from uuid import UUID

from supabase import Client

from backend.database import get_supabase_client
from backend.rag.hashing import sha256_text, short_hash


class RunLogger:
    """Create and update run records as the pipeline executes."""

    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_supabase_client(use_service_role=True)
        self._step_order = 0

    def start_run(
        self,
        *,
        normalized_input: str,
        job_id: str | None = None,
        user_id: str | None = None,
        trace_key: str | None = None,
    ) -> UUID:
        """Insert the run row; rag_runs requires a user_id or a trace_key."""
        response = (
            self._client.table("rag_runs")
            .insert(
                {
                    "job_id": job_id,
                    "user_id": user_id,
                    "trace_key": trace_key or (None if user_id else short_hash(normalized_input)),
                    "status": "running",
                    "normalized_input": normalized_input,
                    "normalized_input_hash": sha256_text(normalized_input),
                }
            )
            .execute()
        )
        return UUID(response.data[0]["id"])

    def update_run(self, run_id: UUID, **fields: object) -> None:
        """Patch run-level fields (generated_queries, rerank_order, ...)."""
        self._client.table("rag_runs").update(fields).eq("id", str(run_id)).execute()

    @contextmanager
    def step(self, run_id: UUID, step_name: str) -> Iterator[dict]:
        """Record one pipeline step with timing, output summary, and errors.

        Yields a dict the caller fills with output summary values. On
        exception the step is recorded as failed and the error re-raised.
        """
        self._step_order += 1
        order = self._step_order
        summary: dict = {}
        started = time.perf_counter()
        try:
            yield summary
        except Exception as error:
            self._record_step(run_id, step_name, order, "failed", started, summary, str(error)[:500])
            raise
        self._record_step(run_id, step_name, order, "completed", started, summary, None)

    def complete_run(self, run_id: UUID, summary: dict) -> None:
        self.update_run(
            run_id,
            status="completed",
            completed_at=datetime.now(timezone.utc).isoformat(),
            **summary,
        )

    def fail_run(self, run_id: UUID, failure_state: dict) -> None:
        self.update_run(
            run_id,
            status="failed",
            completed_at=datetime.now(timezone.utc).isoformat(),
            failure_state=failure_state,
        )

    def _record_step(
        self,
        run_id: UUID,
        step_name: str,
        order: int,
        status: str,
        started: float,
        summary: dict,
        error: str | None,
    ) -> None:
        self._client.table("rag_run_steps").insert(
            {
                "run_id": str(run_id),
                "step_name": step_name,
                "step_order": order,
                "status": status,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "duration_ms": int((time.perf_counter() - started) * 1000),
                "output_summary": summary,
                "error": error,
            }
        ).execute()
```

---

## Reference: Metric Functions for `evals/`

Book 2 milestone 4, verbatim in substance — these go in `evals/metrics.py`
and are what `run_evals.py` will call once golden cases include
`relevant_chunk_ids` or expected domains.

```python
"""Retrieval quality metrics from Hybrid Search and Retrieval Evaluation."""

from __future__ import annotations

import math


def precision_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int) -> float:
    if k <= 0:
        return 0.0
    return len(set(retrieved_ids[:k]) & set(relevant_ids)) / k


def recall_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int) -> float:
    relevant = set(relevant_ids)
    if not relevant:
        return 0.0
    return len(set(retrieved_ids[:k]) & relevant) / len(relevant)


def reciprocal_rank(retrieved_ids: list[str], relevant_ids: list[str]) -> float:
    relevant = set(relevant_ids)
    for rank, retrieved_id in enumerate(retrieved_ids, start=1):
        if retrieved_id in relevant:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int) -> float:
    relevant = set(relevant_ids)
    if not relevant:
        return 0.0
    dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank, retrieved_id in enumerate(retrieved_ids[:k], start=1)
        if retrieved_id in relevant
    )
    ideal_hits = min(k, len(relevant))
    idcg = sum(1.0 / math.log2(rank + 2) for rank in range(ideal_hits))
    return dcg / idcg if idcg > 0 else 0.0


def citation_validity(cited_ids: list[str], allowed_ids: set[str]) -> float:
    """Fraction of citations that map to evidence actually provided."""
    if not cited_ids:
        return 0.0
    return sum(1 for cited in cited_ids if cited in allowed_ids) / len(cited_ids)
```

---

## Reference: LangGraph Orchestration Preview (Do Not Build Yet)

Book 4's graph translated to your state fields, recorded here so the target
is clear when Phases 1–3 are done. The refinement loop's job in ScholarSource
is *bounded evidence widening*: when the evaluate node sees weak evidence, it
retries retrieval once with a larger limit before giving the transparent
limitation answer.

```python
"""Phase 4 sketch only. The linear pipeline must be stable, repeatable, and
evaluated before any of this exists in the repo."""

from typing import TypedDict

from langgraph.graph import END, StateGraph

MAX_REFINEMENT = 2


class GuideState(TypedDict, total=False):
    topic: str
    run_id: str
    evidence: list
    weak_evidence_status: str
    guide: dict
    refinement_count: int


# Nodes wrap the existing Phase 1 modules as-is:
#   analyze   -> validate/normalize topic, route trivial input to END
#   retrieve  -> ChunkRetriever + rerank_evidence, widening retrieval_limit
#                by refinement_count * 6 on each pass
#   evaluate  -> assess_evidence; route "refine" while status != strong and
#                refinement_count < MAX_REFINEMENT, else "synthesize"
#   synthesize -> CitedSynthesizer (also the weak/insufficient fallback path)
#
# builder = StateGraph(GuideState)
# builder.add_node("analyze", analyze_node)
# builder.add_node("retrieve", retrieve_node)
# builder.add_node("evaluate", evaluate_node)
# builder.add_node("synthesize", synthesize_node)
# builder.set_entry_point("analyze")
# builder.add_conditional_edges("analyze", route_analysis, {"retrieve": "retrieve", "end": END})
# builder.add_edge("retrieve", "evaluate")
# builder.add_conditional_edges(
#     "evaluate", route_evaluation, {"retrieve": "retrieve", "synthesize": "synthesize"}
# )
# builder.add_edge("synthesize", END)
```

Note from the Book 4 solution code: its retry helper uses
`time.sleep(30 ** attempt)` — 1s, 30s, 900s. When you add retries, use
`time.sleep(2 ** attempt)` with a small max, and only around provider calls.
