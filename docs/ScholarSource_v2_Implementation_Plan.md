# ScholarSource v2 Implementation Plan

## Overview

This plan turns the ScholarSource v2 learning plan into an execution checklist. The goal is to rebuild ScholarSource as a production-style RAG system while preserving the most important constraint: you write the implementation first, and AI acts as a tutor, reviewer, debugger, and architecture partner.

ScholarSource v2 replaces the current agent-first resource discovery flow with a controlled retrieval pipeline. The system should collect source content, split it into reusable chunks, embed those chunks, store them in a vector-enabled database, retrieve the most relevant evidence for a student query, rerank the evidence, and synthesize a cited study resource guide. Orchestration is added only after the basic pipeline is stable, tested, observable, and repeatable.

Each numbered section describes what to build, what to learn, what to
verify, and what evidence proves the phase is complete. Unnumbered
reference implementation sections — merged from the former
`ScholarSource_RAG_Reference_Implementation.md` — sit beneath the
checklists they support, so the plan and the concrete code it describes
live in one document. See "How to Use the Reference Code Sections" below.

---

## Guiding Rules

- You write the first version of each core module yourself.
- AI may explain concepts, review code, debug errors, suggest tests, and help compare design options.
- AI should not generate the initial production implementation for modules you want to defend in interviews.
- Every core behavior needs a short explanation you can give from memory.
- Every phase ends with a working artifact, not just notes.
- Every new abstraction should have a measurable reason to exist.
- Every retrieved source shown to a user must be traceable to stored evidence.
- Every generated answer must distinguish retrieved evidence from model synthesis.
- Determinism, observability, and evals are product features, not cleanup work.

---

## How to Use the Reference Code Sections

This plan originally avoided implementation code on principle. That rule is
now revised: the full reference implementation (formerly the separate
`docs/ScholarSource_RAG_Reference_Implementation.md`) is merged into this plan
so there is one source of truth. Numbered sections remain the checklist — what
to build, what to learn, what to verify, and what evidence proves a phase is
complete. The unnumbered `Reference: ...` sections beneath them show concrete
code for exactly those steps. None of the reference code has been applied to
the repo yet.

The guiding rules above still say you write the first version of every core
module: chunker, embedder, vector store client, retriever, reranker, and
synthesis prompt. The reference code is a complete answer key. Two honest ways
to use it:

1. Write your own first version of each module from the books and your
   `agentic-rag-tutorial` solutions, then diff against the reference section
   as a review step. This preserves the interview-defensibility goal.
2. Consciously waive the authorship rule for specific modules (for example the
   vector store client, which is mostly plumbing) and paste from the
   reference.

Either way, the *decisions* in the reference sections (embedding model, chunk
sizing, weak-evidence thresholds, deterministic query generation) are the part
worth internalizing — they are the answers to questions this plan explicitly
asks you to be able to defend (steps 1.4.1, 1.5.6, 1.8.6).

---

## What Each Book Contributes to ScholarSource

| Source | Take into ScholarSource | Leave behind |
| --- | --- | --- |
| Book 1: Vector Database and Document Retrieval | Extraction and text cleaning, chunk records with ordered metadata, embedding validation (count and dimension checks), batched upserts, top-k search with score inspection, retrieval smoke tests with known queries | Qdrant collections/points/payloads (translate to `rag_chunks` + `rag_embeddings` rows), `all-MiniLM-L6-v2` at 384 dims (your schema is `vector(1536)`), `SemanticChunker` (nondeterministic boundaries, heavy sentence-transformers dependency), keyword topic labels |
| Book 2: Hybrid Search and Retrieval Evaluation | Lexical retrieval as a second path, reciprocal rank fusion (RRF) as the reranker, precision@k / recall@k / MRR / NDCG metric functions for the Phase 3 eval harness | Qdrant sparse vectors with a hand-built vocabulary (breaks as the corpus grows; Postgres full-text search is the correct translation), server-side `FusionQuery(RRF)` (do RRF in Python) |
| Book 3: Prompt Engineering for Context-Aware Q&A | Context-only system prompt, `[chunk_id: ...]` context blocks, structured output with citations, citation filtering against provided IDs, explicit cannot-answer behavior, error-wrapped LLM calls | OpenRouter free models, string `source_ids` with confidence self-reporting (ScholarSource derives confidence from retrieval scores, not model self-assessment) |
| Book 4: Building an Agentic RAG System with LangGraph | The graph shape (analyze → retrieve → generate → evaluate with a bounded refinement loop) as the Phase 4 design, retry-with-fallback around LLM calls | Everything, until Phases 1–3 are done. Also note the solution notebook contains a real bug: `time.sleep(30 ** attempt)` sleeps 1s, then 30s, then 900s — use sane exponential backoff |
| AI Agents and Applications (ch. 6–9) | Concepts only: ingestion/query separation, advanced indexing, query transformations as later experiments | ChromaDB specifics, tutorial corpora |

Three decisions in this translation matter more than everything else:

- **Embeddings move to OpenAI `text-embedding-3-small` (1536 dims).** The
  books use `all-MiniLM-L6-v2` (384 dims), but your migration already commits
  `rag_embeddings.embedding` to `vector(1536)`, your stack already has an
  OpenAI key and `langchain-openai` (which gives you LangSmith tracing from
  Phase 0 for free), and Railway does not want a 90 MB sentence-transformers
  model in the worker image.
- **The vector store is Supabase pgvector, not a dedicated vector database
  (Qdrant, Pinecone, ChromaDB).** The books use Qdrant, but ScholarSource
  already runs Supabase Postgres for jobs and auth, so pgvector adds vector
  search without a new service to provision, pay for, secure, and keep in
  sync with the relational data. Chunks, embeddings, and job records live in
  one database under one set of RLS policies, and the corpus size (one
  course's worth of sources per run) is nowhere near the scale where a
  dedicated vector engine earns its operational cost.
- **Query generation becomes deterministic templates, not an LLM.** Your
  Phase 0 diagnosis found the v1 instability came from nondeterministic
  search-query planning in the resource discovery agent. The single highest
  value change in v2 is that `generate_search_queries()` below is a pure
  function: same input, same queries, every run.

---

## [x] Phase 0: Baseline, Diagnosis, and Project Contract

**Goal:** Understand the current system failure modes before replacing them.

**Primary learning focus:** Diagnosis, observability mindset, system boundaries.

### [x] 0.1 Baseline Current Behavior

- [x] 0.1.1 Pick one representative course or textbook input.
- [x] 0.1.2 Run the current system five times with the same input.
  - Current evidence captures five completed same-input runs from Railway API and worker logs. One additional same-input job in the worker log was cancelled before execution and is not counted as a completed baseline run.
- [x] 0.1.3 Save each final output.
  - Current saved evidence is log-derived, not clean machine-readable final result JSON per job. Use stored job results later if exact final URL comparison is needed.
- [x] 0.1.4 Record whether the same sources appear across runs.
- [x] 0.1.5 Record whether the same search terms appear across runs.
- [x] 0.1.6 Record whether the same topics are extracted across runs.
- [x] 0.1.7 Record whether the final prose changes while sources stay stable.
- [x] 0.1.8 Summarize the largest inconsistency in one paragraph.
- [x] 0.1.9 Results: the largest inconsistency is the agentic retrieval harness. The resource search agent makes different search-planning decisions for the same input, which leads to different search queries, different candidate resources, different validation inputs, and different final outputs.

### [x] 0.2 Identify Root Cause Categories

The main inconsistency appears to come from nondeterministic query generation inside the agentic retrieval harness, specifically in the `resource_discovery_agent` during `resource_search_task`. The `course_intelligence_agent` creates the topic frame from the course page, but the saved baseline evidence does not show that course-topic extraction is where same-input runs diverged. The documented divergence begins when the resource discovery step chooses live search queries and decides how many Serper searches to run.

For the same submitted course URL, the resource search step generated different queries such as `Engineering Mechanics Statics practice exam PDF site:edu`, `Engineering Mechanics practice exam site:edu`, `Engineering mechanics statics exam pdf site:edu`, and `Engineering Mechanics Statics exam problems PDF site:edu`. Those search-planning differences changed the web results returned, the candidate resources selected for validation, and the material passed into final formatting and synthesis. Source validation, extraction, and final prose may amplify the differences, but they are downstream effects rather than the primary root cause.

Interview explanation: the inconsistent results were primarily caused by the `resource_discovery_agent`, not the `course_intelligence_agent`. More precisely, the failure mode was nondeterministic agentic retrieval planning: the system delegated search-query generation and source selection to an LLM agent with live search tools, so identical input could produce different retrieval plans and therefore different final resource lists. Missing structured run logs make exact reconstruction harder, but the behavior points to resource search-planning nondeterminism as the root instability source.

### [x] 0.3 Define the Development Contract

- [x] 0.3.1 Confirm the project rules for what you write and what AI can assist with.
- [x] 0.3.2 Add hard rules for citations, source quality, and hallucinated URLs.
- [x] 0.3.3 Add hard rules for logging and traceability.
- [x] 0.3.4 Add hard rules for when a result is too weak to show confidently.
- [x] 0.3.5 Add a short explanation of the v2 architecture goal.

### [x] 0.4 Set Up Observability

- [x] 0.4.1 Create tracing accounts or projects needed for LLM and retrieval visibility.
  - Sign up at [smith.langchain.com](https://smith.langchain.com) (free tier). Generate an API key from **Settings → API Keys**.
  - Note which **organization/workspace** the key belongs to — it's shown in the top-left selector in the LangSmith UI. Traces only appear in the workspace the key was scoped to.
- [x] 0.4.2 Add local environment values for tracing.
  - Required vars in `.env.local`: `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT` (any project name; LangSmith creates it on first trace if it doesn't exist), `LANGSMITH_ENDPOINT=https://api.smith.langchain.com`.
  - `OPENAI_API_KEY` must also be set — the env vars above only configure *where traces go*, not what makes the LLM call.
- [x] 0.4.3 Verify that a simple LLM call appears in the tracing dashboard.
  - Env vars alone produce no traces. Something has to call an LLM through an instrumented client: either a LangChain wrapper (e.g. `ChatOpenAI` from `langchain-openai`) or the raw OpenAI SDK wrapped in the `langsmith` SDK's `@traceable` decorator.
  - Added `langchain-openai==1.3.3` and `langsmith==0.9.5` to `pyproject.toml` for this reason — install them (`pip install langchain-openai==1.3.3 langsmith==0.9.5` or `uv sync`) before expecting any trace to appear.
  - Verified using `scripts/verify_langsmith_trace.py`, a rerunnable script that loads `.env.local` and makes one `ChatOpenAI` call.
- [x] 0.4.4 Verify that request timing and token usage are visible.
  - Both appear automatically on the trace detail page — no extra configuration needed once 0.4.3 works.
- [x] 0.4.5 Document where to inspect traces during debugging.
  - Traces appear at smith.langchain.com under **Projects → `<LANGSMITH_PROJECT value>`** (e.g. `scholar-source-v2-local`), not on the dashboard home page.
  - Click into a run to see input/output, latency, and token counts. For multi-step pipeline code (Phase 1+), the same view shows a run tree of nested steps (retrieve → rerank → synthesize), not just a single call.
  - If a trace doesn't show up: check the org/workspace selector (top-left) — API keys are scoped to one org, and traces silently land wherever the key belongs, which may not be the workspace you're currently viewing.

### 0.5 Phase Completion Criteria

- [x] 0.5.1 You have five saved baseline runs from v1.
- [x] 0.5.2 You can explain what changed between those runs.
- [x] 0.5.3 You have a written diagnosis of the most likely instability source.
- [x] 0.5.4 You have a project contract that defines AI usage and system guardrails.
- [x] 0.5.5 You can view at least one traced LLM call.

### Phase 0 Status

Phase 0 is complete. Current saved evidence contains five completed same-input v1 runs. The completed runs show nondeterministic search-query generation, different search counts, different candidate resources, and different final resource counts for the same submitted input.

---

## [ ] Phase 1: Controlled Non-Agentic RAG Pipeline

**Goal:** Build the simplest reliable retrieval pipeline before adding orchestration or agent behavior.

**Primary learning focus:** Chunking, embeddings, vector search, reranking, cited synthesis.

### 1.0 Phase 1 Course Checkpoints, Not Implementation Steps

This subsection tracks when to use the Manning liveProjects while building Phase 1. It is not a separate coding section. Production code work starts in section 1.1 and proceeds through section 1.10. Some course checkpoints happen before coding a module, and some happen after a basic version of earlier modules already works.

- [X] 1.0.1 Start *Vector Database and Document Retrieval* (Manning liveProject, Matteus Tanha) before writing the Phase 1 RAG modules. Covers chunking, embeddings, and vector storage using Qdrant.
- [X] 1.0.2 Finish the chunking, embedding, and vector storage lessons in *Vector Database and Document Retrieval* before implementing `backend/rag/chunking/`, `backend/rag/embeddings/`, and the vector storage layer in `backend/rag/retrieval/`. The course uses Qdrant, so treat its storage code as conceptual guidance; the implementation translation to Supabase and pgvector happens in section 1.6.
- [ ] 1.0.3 Start *Hybrid Search and Retrieval Evaluation* (Manning liveProject, Matteus Tanha) after sections 1.2 through 1.7 have produced one basic retrieval path: source collection, text extraction, chunking, embedding, vector storage, and semantic retrieval. This checkpoint comes before implementing section 1.8 reranking. Covers BM25, reciprocal rank fusion, and retrieval metrics like precision, recall, MRR, and NDCG.
- [ ] 1.0.4 Finish the hybrid ranking and evaluation lessons before implementing `backend/rag/reranking/`.
- [ ] 1.0.5 Start *Prompt Engineering for Context-Aware Q&A* (Manning liveProject, Matteus Tanha) before implementing cited synthesis. Covers system prompt design for staying on context, context injection for top ranked chunks, and source attribution.
- [ ] 1.0.6 Finish the prompt design and source attribution lessons before implementing the cited synthesis logic in section 1.9.

### 1.1 Define the Pipeline Boundary

- [x] 1.1.1 Decide the pipeline boundary: the minimum accepted input for v2, the minimum accepted output, which existing frontend behavior stays unchanged, and which current backend flow gets bypassed or replaced during v2 work.
- [x] 1.1.2 Write a short pipeline diagram in prose.
- [x] 1.1.3 Apply the shared foundations from the reference sections: create the `backend/rag/` package skeleton (`__init__.py` in every subpackage) plus `config.py`, `errors.py`, `hashing.py`, and `models.py`, and verify imports and basic behavior with a smoke test.

#### Boundary Decision Record (1.1.1)

- **Minimum accepted input:** a topic list, plus optional context fields
  (course title, level, subject). The context fields are metadata riding
  along with the topic list — the request already carries `course_name`
  and `university_name` today — used only to sharpen the deterministic
  search queries; the pipeline must work with topics alone. The pipeline
  boundary is topics-in. URL input is supported by a thin pre-step
  adapter *outside* the boundary: one HTTP fetch of the given course page
  with HTML cleaning (reusing the section 1.3 extraction machinery), then
  one structured LLM call that reads the cleaned page text and returns
  `{course_title, subject, topics}` from whatever syllabus, schedule, or
  outline content the page contains. No hand-written syllabus parser —
  course page structures vary too much for rules; the LLM reading the
  cleaned page is the parser. v2 minimum is single-page extraction only;
  a one-hop follow of a syllabus link found on the page is a later
  enhancement, added only if real course pages prove too thin in
  practice. The adapter is built late in Phase 1, after the core path
  works with hand-fed topic lists. ISBN, PDF, and book-title inputs stay
  on the CrewAI path for now.
- **Minimum accepted output:** the same envelope the frontend already
  renders — a completed job with `results` (a list of resources with type,
  title, source, URL, description) and `raw_output` (the markdown study
  guide). Hard guarantees inside that envelope: every URL is joined back
  from a stored source record by chunk ID and never produced by the LLM;
  the guide is organized by topic with resources cited under each topic;
  topics whose retrieval scores fall below the weak-evidence threshold are
  explicitly noted as thin rather than padded. A run completes with
  however many resources survive quality policy and notes the gaps; it
  fails only when zero resources survive. The 5–7 resource count is a
  target, not a floor.
- **Frontend behavior that stays unchanged:** all of it. Same submit form,
  same 2-second status polling, same results table and NotebookLM copy
  flow. v2 is invisible to `web/`.
- **Backend flow that gets bypassed:** dispatch happens at the existing
  seam in `backend/crew_runner.py`, controlled by a `RAG_PIPELINE_ENABLED`
  environment flag. With the flag on, supported input types (topic list;
  later URL via the adapter) route to `backend/rag/pipeline.py`; input
  types the RAG path does not yet handle fall through to the CrewAI crew,
  so no legal frontend input ever errors. With the flag off, behavior is
  identical to today everywhere.

#### Numbered Pipeline Flow (1.1.2)

```text
1. User input
   topic list + optional course context
   |
   v
2. URL-to-topics adapter, when the user submits a course URL
   fetch page once -> clean HTML -> structured LLM topic extraction
   |
   v
3. Deterministic query generation
   render stable search queries for each topic
   |
   v
4. Source collection
   run Serper searches -> deduplicate normalized URLs
   |
   v
5. Source quality policy
   accept/reject candidates -> persist accepted source records
   |
   v
6. Extraction
   fetch accepted HTML/PDF sources -> clean text -> hash extracted text
   |
   v
7. Chunking
   split text into ordered overlapping chunks with source metadata
   |
   v
8. Embedding and vector storage
   embed missing chunks -> store chunks/vectors in Supabase pgvector
   |
   v
9. Retrieval
   run semantic + lexical search per topic over stored chunks
   |
   v
10. Reranking and weak-evidence check
    fuse scores -> rank hits -> select evidence or flag weak evidence
    |
    v
11. Cited synthesis
    send only selected chunk evidence to synthesis -> draft guide by chunk ID
    |
    v
12. Citation resolution and job completion
    join titles/URLs from stored metadata -> return `results` + `raw_output`
```

The frontend-facing envelope stays unchanged: the job still completes with a
`results` resource list and `raw_output` markdown that the existing UI can
render. The hard boundary is that synthesis sees selected chunk evidence only;
source titles, URLs, and citation metadata are joined back from storage after
generation.

### Reference: Target Layout for `backend/rag/`

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

### Reference: Shared Foundations (`config`, `errors`, `hashing`, `models`)

#### `backend/rag/config.py`

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

#### `backend/rag/errors.py`

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

#### `backend/rag/hashing.py`

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

#### `backend/rag/models.py`

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

### 1.2 Source Collection

*Reference: the source collection design (tiers, curated domains, denylist, metadata contract, and eligibility checklist) is written out in `docs/ScholarSourcev2Learning Plan.md`, Phase 1, "Where the sources come from".*

- [x] 1.2.1 Decide the source collection design: the first source type to support, what metadata must be saved for every source, and what makes a source eligible versus rejected.
- [x] 1.2.2 Add a manual test input with known good source candidates.
- [x] 1.2.3 Verify source collection can return stable source records for the same input.
- [x] 1.2.4 Broaden subject coverage beyond STEM: humanities golden eval cases (French Revolution, Hamlet) and a prose-heavy catalog topic, so retrieval and chunking are never tuned on STEM content alone.
- [x] 1.2.5 Deduplicate universal forbidden domains in the golden-case suite: suite-level `shared_forbidden_domains` merged with additive per-case `additional_forbidden_domains` (golden cases contract v2).

### Reference: Sources — Deterministic Queries, Collection, Quality Policy

#### `backend/rag/sources/queries.py`

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

#### `backend/rag/sources/policy.py`

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

#### `backend/rag/sources/collector.py`

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

#### `backend/rag/sources/catalog.py` — the first source type

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

### Reference: SQL Migration 003 — Domain Policy Rules

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

### 1.3 Text Extraction

- [X] 1.3.1 Extract readable text from collected sources.
- [X] 1.3.2 Preserve source title, URL, and extraction timestamp.
- [X] 1.3.3 Handle pages with no usable text.
- [X] 1.3.4 Handle fetch failures without crashing the entire run.
- [X] 1.3.5 Store or log enough information to debug extraction failures.
- [X] 1.3.6 Verify the same source produces the same extracted content when cached.

### Reference: Extraction (`backend/rag/extraction/extractor.py`)

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

### 1.4 Chunking

*Reference: Vector Database and Document Retrieval (Manning liveProject, Matteus Tanha).*

- [ ] 1.4.1 Decide the initial chunk size and overlap, and be ready to explain why the overlap value is useful.
- [ ] 1.4.2 Preserve source metadata on every chunk.
- [ ] 1.4.3 Preserve chunk order within the source.
- [ ] 1.4.4 Add a way to inspect chunks for a single source.
- [ ] 1.4.5 Verify chunks are neither too tiny to be useful nor too large to retrieve precisely.

### Reference: Chunking (`backend/rag/chunking/chunker.py`)

Deliberate departure from the course: Book 1 (and your tutorial solution) use
LangChain's `SemanticChunker`, which needs sentence-transformers and produces
boundaries that shift when the chunking model changes. ScholarSource v2's
priority is *repeatability*, so the chunker below is a pure function over
text: paragraph-aware packing with sentence-level splitting for oversized
paragraphs and fixed-size overlap. Semantic chunking stays available as a
Phase 3 experiment once evals can measure whether it actually retrieves
better.

Your defense for 1.4.1: ~1400 characters targets chunks that hold one complete
explanation (~350 tokens) while staying precise to retrieve; 200 characters of
overlap means a definition that straddles a boundary still matches from either
side.

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

### 1.5 Embeddings

*Reference: Vector Database and Document Retrieval (Manning liveProject, Matteus Tanha).*

- [ ] 1.5.1 Generate embeddings for extracted chunks.
- [ ] 1.5.2 Log the embedding model used.
- [ ] 1.5.3 Store the embedding model version or identifier with each embedded chunk.
- [ ] 1.5.4 Add a deduplication rule so identical content is not embedded repeatedly.
- [ ] 1.5.5 Verify repeated runs do not create duplicate embeddings for unchanged content.
- [ ] 1.5.6 Explain what the embedding vector represents in plain English.

### Reference: Embeddings (`backend/rag/embeddings/embedder.py`)

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


class ChunkEmbedder:
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

### 1.6 Vector Storage

*Reference: Vector Database and Document Retrieval (Manning liveProject, Matteus Tanha). The course uses Qdrant; translate concepts to the Supabase and pgvector schema below.*

### Qdrant to Postgres and pgvector Translation Reference

| Concept | Qdrant Term / Call | Postgres and pgvector Equivalent |
| --- | --- | --- |
| Table of vectors | Collection | Table with a vector column |
| Stored item | Point (id, vector, payload) | Row (vector column plus ordinary metadata columns) |
| Create the table | `client.create_collection()`, vector size and distance metric set upfront | `CREATE TABLE` with a `vector(1536)` column, then `CREATE INDEX` for HNSW separately |
| Insert data | `client.upsert()` | `INSERT INTO` or `UPSERT` statement |
| Similarity search | `client.search()`, returns scored results | SQL query using `<=>` for cosine distance, ordered and limited to top N |
| Metadata filtering combined with search | Qdrant's built in filter query objects | Normal `WHERE` clause combined with the vector distance ordering in the same SQL query |
| Distance metric setting | Set explicitly at collection creation | Determined by which operator you use in the query (`<=>` for cosine, `<->` for Euclidean, etc.) |

**Rule of thumb:** any method call starting with `client.` that creates, inserts, or searches is Qdrant specific and needs a Postgres translation. Anything conceptual the course explains before the code, such as why you chunk a certain way, why you pick a certain vector size, or why cosine distance makes sense, carries over directly with no translation needed.

- Schema contract files:
  - Fresh database bootstrap: `supabase_schema.sql`
  - Incremental migration: `migrations/001_create_rag_traceability_schema.sql`
  - Required v2 tables: `rag_sources`, `rag_source_rejections`, `rag_extracted_documents`, `rag_chunks`, `rag_embeddings`, `rag_runs`, and `rag_run_steps`
  - Legacy note: older databases may still have `course_cache`; the current backend does not reference it, so the v2 migration leaves it untouched and fresh installs do not recreate it.
  - Current schema status: SQL contract exists, but it still needs to be applied and verified against Supabase before marking vector storage complete.

- [ ] 1.6.1 Enable vector search in the database.
- [ ] 1.6.2 Create storage for chunk text, vector values, source metadata, content hashes, and timestamps.
- [ ] 1.6.3 Add indexes required for retrieval performance.
- [ ] 1.6.4 Add a way to reset local test data safely.
- [ ] 1.6.5 Verify inserted chunks can be retrieved by source and by semantic similarity.

### Reference: SQL Migration 002 — Search Functions

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
- The existing HNSW index (`idx_rag_embeddings_vector_hnsw`) already covers
  the semantic path.

### Reference: Vector Store (`backend/rag/vector_store/client.py`)

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

### 1.7 Semantic Retrieval

*Reference: Vector Database and Document Retrieval (Manning liveProject, Matteus Tanha).*

- [ ] 1.7.1 Convert the user query into the same embedding space as stored chunks.
- [ ] 1.7.2 Retrieve the top matching chunks.
- [ ] 1.7.3 Return similarity scores with retrieved chunks.
- [ ] 1.7.4 Preserve enough metadata to cite every retrieved chunk.
- [ ] 1.7.5 Verify known queries retrieve expected source chunks.
- [ ] 1.7.6 Verify irrelevant queries do not return confident looking weak results.

### Reference: Retrieval (`backend/rag/retrieval/service.py`)

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

### 1.8 Reranking

*Reference: Hybrid Search and Retrieval Evaluation (Manning liveProject, Matteus Tanha). The course uses BM25 fused with reciprocal rank fusion rather than a cross encoder, but it satisfies the same requirement below.*

- [ ] 1.8.1 Score retrieved chunks against the original user need.
- [ ] 1.8.2 Separate retrieval similarity from final relevance ranking.
- [ ] 1.8.3 Keep the original retrieval score for debugging.
- [ ] 1.8.4 Keep the rerank score for debugging.
- [ ] 1.8.5 Verify reranking changes order when the nearest chunk is not the most useful chunk.
- [ ] 1.8.6 Define what score is too weak to include.

### Reference: Reranking (`backend/rag/reranking/reranker.py`)

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

### 1.9 Cited Synthesis

*Reference: Prompt Engineering for Context-Aware Q&A (Manning liveProject, Matteus Tanha).*

- [ ] 1.9.1 Generate a final study guide from only the selected evidence.
- [ ] 1.9.2 Require every recommendation to include a source citation.
- [ ] 1.9.3 Refuse or soften the answer when retrieved evidence is insufficient.
- [ ] 1.9.4 Include source titles and URLs in the final response.
- [ ] 1.9.5 Avoid presenting unsupported claims as facts.
- [ ] 1.9.6 Verify the answer can be traced back to stored chunks.

### Reference: Synthesis — Prompt and Cited Generation

#### `backend/rag/synthesis/prompt.py`

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

#### `backend/rag/synthesis/synthesizer.py`

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

### Reference: The Linear Pipeline (`backend/rag/pipeline.py`)

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
from backend.rag.embeddings.embedder import ChunkEmbedder
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
            embedder = ChunkEmbedder(store, settings)
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

### Reference: Tests to Write First (`tests/rag/`)

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

### 1.10 Phase Completion Criteria

- [ ] 1.10.1 One input can complete the full path from query to cited answer.
- [ ] 1.10.2 The answer is based on stored chunks, not live only search output.
- [ ] 1.10.3 Every cited recommendation maps back to source metadata.
- [ ] 1.10.4 You can explain each pipeline step from memory.
- [ ] 1.10.5 You have at least one manual test case that proves the pipeline works end to end.
- [ ] 1.10.6 You can articulate the retrieval evaluation metrics from *Hybrid Search and Retrieval Evaluation* (precision, recall, MRR, NDCG, groundedness) for your own pipeline's results, even informally.

---

## [ ] Phase 2: Repeatability, Caching, and Run Logs

**Goal:** Make identical inputs produce stable, debuggable results.

**Primary learning focus:** Caching, content hashes, run records, deterministic settings.

### 2.1 Deterministic Configuration

- [ ] 2.1.1 Identify every LLM call in the v2 pipeline.
- [ ] 2.1.2 Set deterministic settings wherever stable behavior is required.
- [ ] 2.1.3 Document any step that intentionally allows variation.
- [ ] 2.1.4 Ensure query generation uses stable settings.
- [ ] 2.1.5 Ensure synthesis uses stable settings unless there is a clear reason not to.

### 2.2 Source and Extraction Cache

- [ ] 2.2.1 Cache collected source results by normalized query or query hash.
- [ ] 2.2.2 Cache fetched source content by normalized URL or URL hash.
- [ ] 2.2.3 Store fetch timestamp and cache freshness rules.
- [ ] 2.2.4 Avoid refetching unchanged sources during repeated runs.
- [ ] 2.2.5 Add a manual way to invalidate cached source content during development.

### 2.3 Embedding Deduplication

- [ ] 2.3.1 Hash chunk content before embedding.
- [ ] 2.3.2 Check whether an embedding already exists before calling the embedding provider.
- [ ] 2.3.3 Reuse existing embeddings when content and model match.
- [ ] 2.3.4 Re-embed content only when the model changes or the content changes.
- [ ] 2.3.5 Track duplicate avoidance in logs.

### 2.4 Run Logging

- [ ] 2.4.1 Create a run record for every submitted query.
- [ ] 2.4.2 Log normalized input.
- [ ] 2.4.3 Log generated search terms.
- [ ] 2.4.4 Log collected source identifiers.
- [ ] 2.4.5 Log retrieved chunk identifiers.
- [ ] 2.4.6 Log reranked order.
- [ ] 2.4.7 Log final selected evidence.
- [ ] 2.4.8 Log total latency and major step timings.
- [ ] 2.4.9 Log token usage and provider cost when available.
- [ ] 2.4.10 Log failure states in a structured way.

### Reference: Run Logging (`backend/rag/runs/logger.py`)

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

### 2.5 Run Comparison

- [ ] 2.5.1 Add a simple way to compare two runs with the same input.
- [ ] 2.5.2 Compare collected sources.
- [ ] 2.5.3 Compare retrieved chunks.
- [ ] 2.5.4 Compare reranked order.
- [ ] 2.5.5 Compare final cited sources.
- [ ] 2.5.6 Use the comparison to explain any differences between runs.

### 2.6 Phase Completion Criteria

- [ ] 2.6.1 Run the same input five times through v2.
- [ ] 2.6.2 Confirm the same top evidence appears each time, unless cache freshness intentionally changes it.
- [ ] 2.6.3 Confirm final citations are stable.
- [ ] 2.6.4 Confirm run logs make differences explainable.
- [ ] 2.6.5 You can point to one run record and explain the full path from input to output.

---

## [ ] Phase 3: Evaluation Harness

**Goal:** Define what good means and make regressions visible before they reach users.

**Primary learning focus:** Golden datasets, retrieval metrics, answer groundedness, CI gates.

### 3.0 Phase 3 Course Checkpoint

- [ ] 3.0.1 Start [Evaluating AI Agents - DeepLearning.AI](https://www.deeplearning.ai/courses/evaluating-ai-agents) before creating the Phase 3 golden test set and eval metrics.
- [ ] 3.0.2 Finish the evaluation design lessons before setting final local and CI eval thresholds.

### 3.1 Golden Test Set

- [ ] 3.1.1 Create twenty representative student queries.
- [ ] 3.1.2 Include a mix of textbook-based, topic-based, and course-based inputs.
- [ ] 3.1.3 For each case, list expected source domains or URLs.
- [ ] 3.1.4 For each case, list forbidden source types.
- [ ] 3.1.5 For each case, list key concepts that should appear in the answer.
- [ ] 3.1.6 Include at least three cases where good sources are hard to find.
- [ ] 3.1.7 Include at least three cases where low-quality sources are tempting.

### 3.2 Retrieval Evaluation

- [ ] 3.2.1 Measure whether retrieved chunks are relevant to the query.
- [ ] 3.2.2 Measure whether expected source domains appear.
- [ ] 3.2.3 Measure whether forbidden source types are excluded.
- [ ] 3.2.4 Measure whether top results are better than lower-ranked results.
- [ ] 3.2.5 Set an initial threshold for acceptable retrieval quality.
- [ ] 3.2.6 Save baseline retrieval scores.

### Reference: Metric Functions for `evals/`

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

### 3.3 Generation Evaluation

- [ ] 3.3.1 Measure whether answers are grounded in retrieved evidence.
- [ ] 3.3.2 Measure whether answers include required concepts.
- [ ] 3.3.3 Measure whether answers avoid forbidden claims.
- [ ] 3.3.4 Measure whether citations are present and usable.
- [ ] 3.3.5 Set an initial threshold for acceptable answer quality.
- [ ] 3.3.6 Save baseline generation scores.

### 3.4 Regression Gate

- [ ] 3.4.1 Add a repeatable command to run the eval suite locally.
  - Scaffold command exists: `uv run --extra dev run-evals`. If `just` is installed, `just evals` runs the same command. It validates `evals/golden_cases.json`; RAG pipeline scoring is not implemented yet.
- [ ] 3.4.2 Add eval output that is easy to compare over time.
- [ ] 3.4.3 Add thresholds that fail when quality drops too far.
- [ ] 3.4.4 Add a lightweight CI path for the golden test set.
- [ ] 3.4.5 Decide which expensive evals run locally only and which run in CI.

### Eval Harness Scaffold Status

Initial eval scaffold exists at `evals/`:

- `evals/golden_cases.json`
- `evals/README.md`
- `evals/run_evals.py`
- `evals/results/.gitkeep`

Verified scaffold commands:

- `uv run --extra dev run-evals`
- `just evals`
- `uv run --extra dev ruff check evals/run_evals.py`
- `uv run --extra dev ruff format --check evals/run_evals.py`

Project task aliases now live in `justfile`. Use `just --list` to inspect available commands such as `just lint`, `just test`, `just frontend-test`, `just evals`, and `just validate`.

Current status: schema validation works; RAG pipeline scoring is not implemented yet.

### 3.5 Phase Completion Criteria

- [ ] 3.5.1 You have twenty golden cases.
- [ ] 3.5.2 You can run evals repeatedly.
- [ ] 3.5.3 You have baseline scores for retrieval and generation.
- [ ] 3.5.4 A bad retrieval change can fail the eval suite.
- [ ] 3.5.5 You can explain the difference between a normal test and an eval.

---

## [ ] Phase 4: Stateful Orchestration

**Goal:** Add workflow control only after the retrieval pipeline is reliable.

**Primary learning focus:** Graph state, node boundaries, conditional routing, fallbacks.

### 4.0 Phase 4 Course Checkpoint

- [ ] 4.0.1 Start [AI Agents in LangGraph - DeepLearning.AI](https://www.deeplearning.ai/courses/ai-agents-in-langgraph) before designing the Phase 4 graph state or node boundaries.
- [ ] 4.0.2 Finish the graph construction and state management lessons before implementing LangGraph orchestration in the repo.
- [ ] 4.0.3 Start *Building an Agentic RAG System with LangGraph* (Manning liveProject, Matteus Tanha) after Phases 1 through 3 are stable and before implementing retry, fallback, or self-evaluation loops. That project covers tool wrapping, self-evaluation nodes, and retry and fallback loops.

### Reference: LangGraph Orchestration Preview (Do Not Build Yet)

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

### 4.1 Preconditions

- [ ] 4.1.1 Confirm Phase 1 end-to-end flow works.
- [ ] 4.1.2 Confirm Phase 2 repeatability checks pass.
- [ ] 4.1.3 Confirm Phase 3 evals have a baseline.
- [ ] 4.1.4 Identify what orchestration problem actually needs solving.
- [ ] 4.1.5 Avoid adding orchestration just to make the architecture look more advanced.

### 4.2 Define Graph State

- [ ] 4.2.1 List every field that moves through the workflow.
- [ ] 4.2.2 Identify which step creates each field.
- [ ] 4.2.3 Identify which step reads each field.
- [ ] 4.2.4 Identify which fields are user-facing.
- [ ] 4.2.5 Identify which fields are debug-only.
- [ ] 4.2.6 Decide how errors and fallback reasons are represented.

### 4.3 Define Workflow Steps

- [ ] 4.3.1 Add a request classification step.
- [ ] 4.3.2 Add a search term generation step.
- [ ] 4.3.3 Add a candidate retrieval step.
- [ ] 4.3.4 Add a candidate quality evaluation step.
- [ ] 4.3.5 Add a reranking step.
- [ ] 4.3.6 Add a synthesis step.
- [ ] 4.3.7 Add a fallback path for weak evidence.
- [ ] 4.3.8 Add a transparent user response when quality is too low.

### 4.4 Fallback Behavior

- [ ] 4.4.1 Decide the fallback policy: what counts as insufficient evidence, when to broaden a query, when to try alternate source types, and when to stop and return a transparent limitation message.
- [ ] 4.4.2 Log every fallback decision.
- [ ] 4.4.3 Include fallback behavior in eval coverage.

### 4.5 Phase Completion Criteria

- [ ] 4.5.1 The workflow produces the same successful outputs as the linear pipeline.
- [ ] 4.5.2 Weak retrieval results follow a clear fallback path.
- [ ] 4.5.3 The graph state can be inspected in traces.
- [ ] 4.5.4 You can draw the workflow from memory.
- [ ] 4.5.5 You can explain why orchestration was added after the pipeline was stable.

---

## [ ] Phase 5: Product Integration and User Experience

**Goal:** Connect the v2 pipeline to the existing product surface and make the experience usable beyond a demo.

**Primary learning focus:** Full-stack integration, async UX, error states, user trust.

### 5.1 Backend Integration

- [ ] 5.1.1 Decide the backend integration approach: how v2 jobs are submitted, how job status is stored, and whether v1 and v2 run side by side during migration.
- [ ] 5.1.2 Preserve authentication requirements.
- [ ] 5.1.3 Preserve rate limiting requirements.
- [ ] 5.1.4 Preserve job ownership checks.
- [ ] 5.1.5 Return structured failure messages to the frontend.

### 5.2 Frontend Flow

- [ ] 5.2.1 Keep the input experience simple.
- [ ] 5.2.2 Show meaningful progress while the pipeline runs.
- [ ] 5.2.3 Show retrieval and synthesis stages in user-friendly language.
- [ ] 5.2.4 Show final cited results clearly.
- [ ] 5.2.5 Show source links in a way that encourages inspection.
- [ ] 5.2.6 Show weak-result warnings when confidence is low.
- [ ] 5.2.7 Handle empty results without a blank screen.
- [ ] 5.2.8 Handle expired sessions.

### 5.3 Trust and Safety

- [ ] 5.3.1 Make citations visible.
- [ ] 5.3.2 Make source quality signals visible.
- [ ] 5.3.3 Avoid implying that a generated guide replaces the original course material.
- [ ] 5.3.4 Avoid storing unnecessary user-provided sensitive content.
- [ ] 5.3.5 Limit repeated expensive requests.
- [ ] 5.3.6 Make failures understandable without exposing internal details.

### 5.4 Mobile and Accessibility

- [ ] 5.4.1 Test the main submission flow on a phone-sized viewport.
- [ ] 5.4.2 Test the final results page on a phone-sized viewport.
- [ ] 5.4.3 Verify keyboard navigation for form controls.
- [ ] 5.4.4 Verify visible focus states.
- [ ] 5.4.5 Verify color contrast for status and warning messages.
- [ ] 5.4.6 Verify long URLs and long source titles do not break layout.

### 5.5 Phase Completion Criteria

- [ ] 5.5.1 A signed-in user can submit a v2 request from the frontend.
- [ ] 5.5.2 The user can watch progress without refreshing.
- [ ] 5.5.3 The final response includes usable citations.
- [ ] 5.5.4 Expected error states are visible and understandable.
- [ ] 5.5.5 The flow works on desktop and mobile.

---

## [ ] Phase 6: Shipping, Feedback, and Portfolio Evidence

**Goal:** Ship the project as a credible personal project with measurable quality and a clear story.

**Primary learning focus:** Release discipline, user feedback, interview readiness.

### 6.1 Release Readiness

- [ ] 6.1.1 Run backend tests.
- [ ] 6.1.2 Run frontend tests.
- [ ] 6.1.3 Run the eval suite.
- [ ] 6.1.4 Run the same-input repeatability check.
- [ ] 6.1.5 Check logs for noisy warnings.
- [ ] 6.1.6 Check production environment variables.
- [ ] 6.1.7 Check rate limits and provider quotas.
- [ ] 6.1.8 Verify deployment health checks.

### 6.2 User Feedback

- [ ] 6.2.1 Recruit ten non-friend users.
- [ ] 6.2.2 Give users one clear task to complete.
- [ ] 6.2.3 Record where users hesitate.
- [ ] 6.2.4 Record which results they trust.
- [ ] 6.2.5 Record which results they ignore.
- [ ] 6.2.6 Ask whether the source citations are useful.
- [ ] 6.2.7 Turn feedback into a prioritized fix list.

### 6.3 Public Project Evidence

- [ ] 6.3.1 Add a concise v2 explanation to the project README.
- [ ] 6.3.2 Add a dated changelog entry for the v2 rewrite.
- [ ] 6.3.3 Add a short architecture summary.
- [ ] 6.3.4 Add current eval scores.
- [ ] 6.3.5 Add current repeatability result.
- [ ] 6.3.6 Add known limitations.
- [ ] 6.3.7 Add planned next improvements.

### 6.4 Interview Readiness

- [ ] 6.4.1 Memorize the 60-second project pitch.
- [ ] 6.4.2 Practice drawing the architecture in two minutes.
- [ ] 6.4.3 Prepare one tradeoff you made.
- [ ] 6.4.4 Prepare one bug you diagnosed from traces.
- [ ] 6.4.5 Prepare one example where evals caught a regression.
- [ ] 6.4.6 Prepare one example where you rejected an AI suggestion.
- [ ] 6.4.7 Prepare one user feedback story.

### 6.5 Phase Completion Criteria

- [ ] 6.5.1 The app is deployed.
- [ ] 6.5.2 At least ten users have tried the v2 flow.
- [ ] 6.5.3 The README explains what changed and why.
- [ ] 6.5.4 Eval and repeatability metrics are documented.
- [ ] 6.5.5 You can explain the architecture without reading the code.

---

## Implementation Order

- [ ] Diagnose current v1 behavior with repeated runs.
- [ ] Set up tracing and project guardrails.
- [ ] Build source collection for one source type.
- [ ] Build extraction and caching.
- [ ] Build chunking.
- [ ] Build embedding generation and deduplication.
- [ ] Build vector storage.
- [ ] Build semantic retrieval.
- [ ] Build reranking.
- [ ] Build cited synthesis.
- [ ] Add run logging.
- [ ] Add run comparison.
- [ ] Build the golden eval set.
- [ ] Add retrieval evals.
- [ ] Add generation evals.
- [ ] Add CI thresholds.
- [ ] Add stateful orchestration and fallback routing.
- [ ] Connect the v2 flow to the backend job system.
- [ ] Connect the v2 flow to the frontend.
- [ ] Test desktop, mobile, errors, and empty states.
- [ ] Ship to real users.
- [ ] Document metrics, lessons, and next steps.

### Module Build Order (Reference)

The reference modules in build order, mapped to plan sections and course
checkpoints:

| Step | Builds | Plan section | Course checkpoint |
| --- | --- | --- | --- |
| 1 | Apply migration 001 + new 002 and 003 to local Supabase; verify with a hand INSERT, a `match_rag_chunks` call, and a `SELECT` showing the seeded `rag_domain_policies` rows | 1.6.1–1.6.3 | Book 1 done (1.0.1–1.0.2 checked) |
| 2 | `config.py`, `errors.py`, `hashing.py`, `models.py` + tests | foundations | — |
| 3 | `sources/` (queries, policy, collector) + tests | 1.2 | — |
| 4 | `extraction/extractor.py` + tests | 1.3 | — |
| 5 | `chunking/chunker.py` + inspection helper + tests | 1.4 | Book 1 |
| 6 | `vector_store/client.py`, `embeddings/embedder.py` | 1.5, 1.6 | Book 1 |
| 7 | `retrieval/service.py`; verify known queries hit expected chunks | 1.7 | start Book 2 (1.0.3) |
| 8 | `reranking/reranker.py` (RRF + weak evidence) | 1.8 | Book 2 (1.0.4) |
| 9 | `synthesis/` (prompt + synthesizer + grounding tests) | 1.9 | Book 3 (1.0.5–1.0.6) |
| 10 | `runs/logger.py`, `pipeline.py`; run one topic end to end five times | 1.10, 2.4 | — |
| 11 | `evals/metrics.py` + golden case scoring | 3.2–3.4 | DeepLearning.AI evals course |
| 12 | LangGraph orchestration, only if evals justify it | 4.x | Book 4 (4.0.3) |

Environment: no new secrets. The pipeline needs `OPENAI_API_KEY`,
`SERPER_API_KEY`, `SUPABASE_URL`, and `SUPABASE_SERVICE_ROLE_KEY` (the store
and run logger use the service-role client). `httpx` is currently a dev-only
dependency — promote it to runtime dependencies when the collector and
extractor land.

Validation gates, per AGENTS.md:

```bash
uv run --extra dev ruff check backend/rag tests/rag
uv run --extra dev ruff format --check backend/rag tests/rag
uv run --extra dev pytest tests/rag -x
uv run --extra dev run-evals
```

---

## Review Checkpoints

Use these checkpoints when asking AI for help. The goal is to review your work without replacing your authorship.

### Checkpoint A: After Diagnosis

- [ ] Ask for feedback on whether the diagnosis is evidence-based.
- [ ] Ask what additional logs would make the conclusion stronger.
- [ ] Ask whether the proposed v2 architecture addresses the observed failure mode.

### Checkpoint B: After Chunking and Embeddings

- [ ] Ask for review of chunk boundaries and metadata preservation.
- [ ] Ask whether deduplication is robust enough.
- [ ] Ask whether the storage shape supports future debugging.

### Checkpoint C: After Retrieval

- [ ] Ask whether retrieval results are explainable.
- [ ] Ask whether similarity scores are being interpreted carefully.
- [ ] Ask what edge cases are missing from manual tests.

### Checkpoint D: After Reranking and Synthesis

- [ ] Ask whether citations are grounded.
- [ ] Ask whether the answer overstates weak evidence.
- [ ] Ask whether failure behavior is honest and user-friendly.

### Checkpoint E: After Evals

- [ ] Ask whether the golden set is diverse enough.
- [ ] Ask whether thresholds are too loose or too strict.
- [ ] Ask whether metrics align with the product goal.

### Checkpoint F: Before Shipping

- [ ] Ask for a code review focused on bugs and regressions.
- [ ] Ask for a UX review focused on error, empty, and loading states.
- [ ] Ask for an interview-readiness review of the architecture explanation.

---

## Metrics

| Metric | Why It Matters | Initial Target |
| --- | --- | --- |
| Eval pass rate | Shows whether output quality is improving or regressing | Above 80 percent |
| Retrieval consistency | Shows whether identical inputs retrieve stable evidence | 100 percent for top evidence in cached runs |
| Citation coverage | Shows whether recommendations are traceable | 100 percent for final recommendations |
| Retrieval latency | Shows whether the app feels responsive | Under 3 seconds for common cached retrieval |
| End-to-end latency | Shows whether the full workflow is usable | Track baseline first, then improve |
| User completion rate | Shows whether users can finish the main flow | Track after first user test |

---

## Definition of Done for ScholarSource v2

- [ ] The system can return cited study resources for real student inputs.
- [ ] Retrieved evidence is stored and traceable.
- [ ] Repeated cached runs produce stable top evidence.
- [ ] The eval suite runs locally.
- [ ] The eval suite protects against obvious retrieval regressions.
- [ ] The frontend displays progress, success, empty, and failure states.
- [ ] The production deployment has required environment values.
- [ ] The README explains the rewrite and current metrics.
- [ ] At least one real user feedback cycle has produced a shipped improvement.
- [ ] You can explain and debug every major part of the pipeline.

---

## Appendix: How This Differs From the Codex Guide

Codex's guide (`docs/ScholarSource_RAG_Backend_Implementation_Guide.docx`)
took the authorship contract literally: it ships typed contracts, hashing,
citation utilities, RRF, and `Protocol` interfaces that raise
`NotImplementedError`, and explicitly defers every core module to you. That is
a valid reading, and its foundational files (errors, hashing, model shapes)
are deliberately kept compatible here.

The reference sections in this plan make the opposite bet — show the whole thing — plus several
substantive decisions Codex left open:

| Area | Codex guide | This plan's reference sections |
| --- | --- | --- |
| Core modules | Interfaces only, `NotImplementedError` | Full reference implementations |
| Query generation | Not addressed | Deterministic templates — the direct fix for your Phase 0 root cause |
| pgvector search | Deferred to human | SQL RPC functions written (`match_rag_chunks`, lexical FTS) |
| Lexical path | "later experiment" | Postgres full-text search now, fused with RRF as the reranker |
| Hallucinated URLs | Citation filtering after the fact | Structural: the LLM only outputs chunk_ids; URLs are joined from storage |
| Sync vs async | Async interfaces | Sync, matching supabase-py and the Celery worker where this runs |
| Weak evidence | Policy deferred | Concrete thresholds in `RagSettings`, marked as Phase 3 tuning targets |

Where the two agree — module boundaries, the `rag_*` schema as the
source of truth, evals before orchestration, LangGraph last — treat that
agreement as strong signal: two independent reviews of the same material
landed on the same architecture.
