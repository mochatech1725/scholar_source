# ScholarSource v2 Implementation Plan

## Overview

This plan turns the ScholarSource v2 learning plan into an execution checklist. The goal is to rebuild ScholarSource as a production-style RAG system with AI available to implement, test, review, explain, debug, and refine every module.

ScholarSource v2 replaces the current agent-first resource discovery flow with a controlled retrieval pipeline. The system should collect source content, split it into reusable chunks, embed those chunks, store them in a vector-enabled database, retrieve the most relevant evidence for a student query, rerank the evidence, and synthesize a cited study resource guide. Orchestration is added only after the basic pipeline is stable, tested, observable, and repeatable.

## Working Context

Current v2 implementation work is happening on the `rag-v2` Git branch.

RAG database work should default to the local Supabase CLI development stack
running in Docker, not the hosted dev or production Supabase projects. The local
stack provides Supabase HTTP APIs, Postgres, pgvector, Auth, PostgREST, Studio,
and local API keys while keeping experimental source, chunk, embedding, and run
log data disposable. Use `docs/supabase_rag_local_setup.md` for exact setup,
reset, and safety commands. Hosted Supabase commands should be treated as
explicit deployment or migration work, not routine local RAG iteration.

Each numbered section describes what to build, what to learn, what to
verify, and what evidence proves the phase is complete. Unnumbered
reference implementation sections are kept in
`docs/ScholarSource_v2_Reference_Code.md` and linked from the checklist
sections they support. See "How to Use the Reference Code Sections" below.

---

## Guiding Rules

- AI may implement, test, review, explain, debug, and refactor every module.
- Important implementation decisions and tradeoffs must remain explicit and explainable.
- Every core behavior needs a short explanation you can give from memory.
- Every phase ends with a working artifact, not just notes.
- Every new abstraction should have a measurable reason to exist.
- Every retrieved source shown to a user must be traceable to stored evidence.
- Every generated answer must distinguish retrieved evidence from model synthesis.
- Determinism, observability, and evals are product features, not cleanup work.
- Every supported product input must normalize into the same typed v2 learning
  request before query generation; input type must not select a different
  retrieval or synthesis implementation.
- ScholarSource v2 is complete only when topic lists, course pages, general
  educational page URLs, book URLs, uploaded book PDFs, ISBNs, and book
  metadata all run through v2 without invoking CrewAI.

---

## How to Use the Reference Code Sections

This plan keeps implementation code out of the main checklist. Numbered
sections remain the plan: what to build, what to learn, what to verify, and
what evidence proves a phase is complete. The unnumbered `Reference: ...`
sections link to concrete code examples in
`docs/ScholarSource_v2_Reference_Code.md`. The companion file is reference
material, not proof that the code has been applied to the repo.

The reference code is a complete implementation guide. It may be applied
directly, adapted to surrounding code, or used for comparison during review.
Verify applied reference code with focused tests and record meaningful design
decisions in the implementation plan.

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

- [x] 0.3.1 Confirm implementation authority and AI collaboration rules.
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

- **Accepted product inputs:** a topic list; a course page; a general
  educational page URL; a book URL, including a direct PDF URL; an uploaded
  book PDF; an ISBN-10 or ISBN-13; or book metadata such as title and author.
  Optional course, chapter, section, institution, level, subject, and resource
  preference fields remain supported.
- **Canonical v2 boundary:** every accepted product input first passes through
  a deterministic adapter selected from validated request fields. Each adapter
  produces one typed normalized learning request containing the input kind,
  normalized identifiers, title, author or institution when applicable,
  subject, topics, chapters or sections, user constraints, provenance for every
  derived field, normalization warnings, and confidence. Topic lists mostly
  pass through unchanged. URLs and PDFs reuse the same fetch and extraction
  machinery used elsewhere in v2, then a single schema-constrained extraction
  call derives the learning outline. ISBN input resolves bibliographic metadata
  and available table-of-contents or subject data through a replaceable,
  cached metadata provider before using the same structured extraction step.
  The downstream boundary is therefore normalized-learning-request-in, not
  topic-list-only.
- **Normalization limits:** adapters may derive only learning context and
  search topics; they do not generate recommended resources or citations.
  A scanned or image-only PDF must use an explicitly configured OCR path or
  return a transparent unsupported-document error. ISBN lookup must report
  insufficient metadata rather than inventing chapters or topics. User-provided
  book content is processed only as needed to derive the learning outline and
  must not be exposed as a recommended source unless it independently passes
  the normal source-quality and citation rules.
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
- **Backend migration and final state:** during development, v1 may remain
  available only as an explicit rollback path while individual v2 adapters are
  completed. There is no per-input permanent CrewAI fallback. Production
  cutover requires every accepted input type to pass its v2 contract and eval
  cases; then all submissions route to `backend/rag/pipeline.py`, the CrewAI
  dispatch is removed, and CrewAI dependencies, configuration, tasks, and
  tests are deleted. An adapter failure returns a structured normalization
  error and never silently reroutes the request through v1.

#### Numbered Pipeline Flow (1.1.2)

```text
1. User input
   topics | course/page URL | book URL | uploaded PDF | ISBN | book metadata
   |
   v
2. Input validation and adapter selection
   validate fields -> classify explicit input kind -> preserve user constraints
   |
   v
3. Normalize into one typed learning request
   topics: normalize directly
   page/book URL: fetch HTML or PDF -> extract text and metadata
   uploaded PDF: validate -> extract text, or OCR when configured
   ISBN: canonicalize -> cached metadata/contents lookup
   extracted material -> schema-constrained title/subject/topic derivation
   |
   v
4. Deterministic query generation
   render stable search queries for each topic
   |
   v
5. Source collection
   run Serper searches -> deduplicate normalized URLs
   |
   v
6. Source quality policy
   accept/reject candidates -> persist accepted source records
   |
   v
7. Extraction
   fetch accepted HTML/PDF sources -> clean text -> hash extracted text
   |
   v
8. Chunking
   split text into ordered overlapping chunks with source metadata
   |
   v
9. Embedding and vector storage
   embed missing chunks -> store chunks/vectors in Supabase pgvector
   |
   v
10. Retrieval
   run semantic + lexical search per topic over stored chunks
   |
   v
11. Reranking and weak-evidence check
    fuse scores -> rank hits -> select evidence or flag weak evidence
    |
    v
12. Cited synthesis
    send only selected chunk evidence to synthesis -> draft guide by chunk ID
    |
    v
13. Citation resolution and job completion
    join titles/URLs from stored metadata -> return `results` + `raw_output`
```

The frontend-facing envelope stays unchanged: the job still completes with a
`results` resource list and `raw_output` markdown that the existing UI can
render. The hard boundary is that synthesis sees selected chunk evidence only;
source titles, URLs, and citation metadata are joined back from storage after
generation.

### Reference: Target Layout for `backend/rag/`

Reference code moved to [docs/ScholarSource_v2_Reference_Code.md](ScholarSource_v2_Reference_Code.md#reference-target-layout-for-backendrag).

### Reference: Shared Foundations (`config`, `errors`, `hashing`, `models`)

Reference code moved to [docs/ScholarSource_v2_Reference_Code.md](ScholarSource_v2_Reference_Code.md#reference-shared-foundations-config-errors-hashing-models).

### 1.2 Source Collection

*Reference: the source collection design (tiers, curated domains, denylist, metadata contract, and eligibility checklist) is written out in `docs/ScholarSourcev2Learning Plan.md`, Phase 1, "Where the sources come from".*

- [x] 1.2.1 Decide the source collection design: the first source type to support, what metadata must be saved for every source, and what makes a source eligible versus rejected.
- [x] 1.2.2 Add a manual test input with known good source candidates.
- [x] 1.2.3 Verify source collection can return stable source records for the same input.
- [x] 1.2.4 Broaden subject coverage beyond STEM: humanities golden eval cases (French Revolution, Hamlet) and a prose-heavy catalog topic, so retrieval and chunking are never tuned on STEM content alone.
- [x] 1.2.5 Deduplicate universal forbidden domains in the golden-case suite: suite-level `shared_forbidden_domains` merged with additive per-case `additional_forbidden_domains` (golden cases contract v2).

### Reference: Sources — Deterministic Queries, Collection, Quality Policy

Reference code moved to [docs/ScholarSource_v2_Reference_Code.md](ScholarSource_v2_Reference_Code.md#reference-sources-deterministic-queries-collection-quality-policy).

### Reference: SQL Migration 003 — Domain Policy Rules

Reference code moved to [docs/ScholarSource_v2_Reference_Code.md](ScholarSource_v2_Reference_Code.md#reference-sql-migration-003-domain-policy-rules).

### 1.3 Text Extraction

- [X] 1.3.1 Extract readable text from collected sources.
- [X] 1.3.2 Preserve source title, URL, and extraction timestamp.
- [X] 1.3.3 Handle pages with no usable text.
- [X] 1.3.4 Handle fetch failures without crashing the entire run.
- [X] 1.3.5 Store or log enough information to debug extraction failures.
- [X] 1.3.6 Verify the same source produces the same extracted content when cached.

### Reference: Extraction (`backend/rag/extraction/extractor.py`)

Reference code moved to [docs/ScholarSource_v2_Reference_Code.md](ScholarSource_v2_Reference_Code.md#reference-extraction-backendragextractionextractorpy).

### 1.4 Chunking

*Reference: Vector Database and Document Retrieval (Manning liveProject, Matteus Tanha).*

- [x] 1.4.1 Decide the initial chunk size and overlap, and be ready to explain why the overlap value is useful.
- [x] 1.4.2 Preserve source metadata on every chunk.
- [x] 1.4.3 Preserve chunk order within the source.
- [x] 1.4.4 Add a way to inspect chunks for a single source.
- [x] 1.4.5 Verify chunks are neither too tiny to be useful nor too large to retrieve precisely.

### Reference: Chunking (`backend/rag/chunking/chunker.py`)

Reference code moved to [docs/ScholarSource_v2_Reference_Code.md](ScholarSource_v2_Reference_Code.md#reference-chunking-backendragchunkingchunkerpy).

### 1.5 Embeddings

*Reference: Vector Database and Document Retrieval (Manning liveProject, Matteus Tanha).*

- [x] 1.5.1 Generate embeddings for extracted chunks.
- [x] 1.5.2 Log the embedding model used.
- [x] 1.5.3 Store the embedding model version or identifier with each embedded chunk.
- [x] 1.5.4 Add a deduplication rule so identical content is not embedded repeatedly.
- [x] 1.5.5 Verify repeated runs do not create duplicate embeddings for unchanged content.
- [x] 1.5.6 Explain what the embedding vector represents in plain English.
  - An embedding vector is a list of numbers that represents the meaning or features of a piece of data, such as text, an image, or a video. Items with similar embedding vectors are likely to be semantically similar or related, though not always exactly the same in meaning.

### Reference: Embeddings (`backend/rag/embeddings/embedder.py`)

Reference code moved to [docs/ScholarSource_v2_Reference_Code.md](ScholarSource_v2_Reference_Code.md#reference-embeddings-backendragembeddingsembedderpy).

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

- [X] 1.6.1 Enable vector search in the database.
- [X] 1.6.2 Create storage for chunk text, vector values, source metadata, content hashes, and timestamps.
  Done in `supabase_schema.sql` and `migrations/001_create_rag_traceability_schema.sql`: `rag_sources` stores source URL/title/quality metadata, `rag_extracted_documents` stores extraction hashes and timestamps, `rag_chunks` stores chunk text/source metadata/content hashes, and `rag_embeddings` stores vector values, embedding model/dimensions, content hash, and `embedded_at`. `migrations/004_deduplicate_rag_embeddings.sql` adds the content-hash/model uniqueness guard for repeated runs.
- [X] 1.6.3 Add indexes required for retrieval performance.
  Done in `migrations/005_add_rag_retrieval_performance_indexes.sql` and `supabase_schema.sql`: source inspection is covered by `(source_id, chunk_index)`, model-filtered semantic retrieval/debug paths are covered by `(embedding_model, embedded_at DESC)`, lexical search remains covered by the `rag_chunks` full-text GIN index, and semantic ordering remains covered by the existing HNSW vector index.
- [X] 1.6.4 Add a way to reset local test data safely.
  Done in `backend/rag/vector_store/client.py`: `SupabaseVectorStore.delete_source()` removes one source by `normalized_url`, relying on the reviewed cascade constraints to clear that source's extracted documents, chunks, and embeddings without wiping unrelated local RAG data.
- [X] 1.6.5 Verify inserted chunks can be retrieved by source and by semantic similarity.
  Done in `tests/rag/test_vector_store.py`: the vector-store test inserts a source, extracted document, chunks, and embeddings, then verifies source-ordered chunk inspection through `chunks_for_source()` and similarity-ranked retrieval through `semantic_search()`.

### Reference: SQL Migration 002 — Search Functions

Reference code moved to [docs/ScholarSource_v2_Reference_Code.md](ScholarSource_v2_Reference_Code.md#reference-sql-migration-002-search-functions).

### Reference: Vector Store (`backend/rag/vector_store/client.py`)

Reference code moved to [docs/ScholarSource_v2_Reference_Code.md](ScholarSource_v2_Reference_Code.md#reference-vector-store-backendragvectorstoreclientpy).

### 1.7 Semantic Retrieval

*Reference: Vector Database and Document Retrieval (Manning liveProject, Matteus Tanha).*

- [x] 1.7.1 Convert the user query into the same embedding space as stored chunks.
  Done in `backend/rag/embeddings/embedder.py`: `RagEmbedder.embed_query()`
  uses the same configured provider, embedding model, and dimension contract
  as stored chunk embeddings, while rejecting blank queries and
  wrong-dimension provider responses.
- [x] 1.7.2 Retrieve the top matching chunks.
  Done in `backend/rag/vector_store/client.py`:
  `SupabaseVectorStore.semantic_search()` calls the `match_rag_chunks`
  pgvector RPC with the configured embedding model and top-k limit.
  `tests/rag/test_vector_store.py` verifies similarity ordering and result
  truncation.
- [x] 1.7.3 Return similarity scores with retrieved chunks.
  Done in `backend/rag/vector_store/client.py`: every semantic-search row is
  converted to a `RetrievalHit` whose `semantic_score` preserves the cosine
  similarity returned by `match_rag_chunks`. `tests/rag/test_vector_store.py`
  verifies that every returned chunk carries its corresponding score.
- [x] 1.7.4 Preserve enough metadata to cite every retrieved chunk.
  Done through the search RPCs and `RetrievalHit`: semantic and lexical hits
  retain the stored chunk ID, source ID, URL, title, chunk index, content, and
  content hash. Required citation strings reject empty values, and
  `tests/rag/test_vector_store.py` verifies both search paths preserve the
  stored citation metadata unchanged.
- [x] 1.7.5 Verify known queries retrieve expected source chunks.
  Done in `tests/rag/test_vector_store.py`: parameterized known-query cases
  pass through `RagEmbedder.embed_query()` and semantic search, then verify
  gradient, curl, and divergence queries return the expected stored chunk ID,
  source ID, chunk index, content, and a strong similarity score.
- [x] 1.7.6 Verify irrelevant queries do not return confident looking weak results.
  Done in `tests/rag/test_vector_store.py`: an irrelevant gardening query is
  embedded orthogonally to the stored vector-calculus chunks, and the test
  verifies every returned top-k result retains a semantic score below the
  configured minimum-evidence threshold rather than appearing confident.

### Reference: Retrieval (`backend/rag/retrieval/service.py`)

Reference code moved to [docs/ScholarSource_v2_Reference_Code.md](ScholarSource_v2_Reference_Code.md#reference-retrieval-backendragretrievalservicepy).

### 1.8 Reranking

*Reference: Hybrid Search and Retrieval Evaluation (Manning liveProject, Matteus Tanha). The course uses BM25 fused with reciprocal rank fusion rather than a cross encoder, but it satisfies the same requirement below.*

- [x] 1.8.1 Score retrieved chunks against the original user need.
  Done in `backend/rag/reranking/reranker.py`: `rerank_evidence()` applies
  reciprocal rank fusion to semantic and lexical rankings produced for the
  same original user need, yielding a deterministic relevance score for each
  selected chunk. `tests/rag/test_reranker.py` verifies the exact fused scores,
  ordering, evidence limit, citation metadata, and preservation of zero-valued
  raw retrieval scores.
- [x] 1.8.2 Separate retrieval similarity from final relevance ranking.
  Done in `backend/rag/models.py` and
  `backend/rag/reranking/reranker.py`: `RetrievalHit` carries raw,
  retrieval-path-specific `semantic_score` and `lexical_score` values, while
  `SelectedEvidence` adds the independent RRF `rerank_score` and final
  one-based `evidence_rank`. `tests/rag/test_reranker.py` verifies that the
  chunk with the highest semantic similarity can have a lower final relevance
  rank when another chunk is supported by both retrieval paths.
- [x] 1.8.3 Keep the original retrieval score for debugging.
  Done in `backend/rag/models.py` and
  `backend/rag/reranking/reranker.py`: each selected evidence record retains
  the original semantic and lexical retrieval-path scores alongside its
  independent rerank score. `tests/rag/test_reranker.py` verifies both raw
  scores survive score merging and serialized debug output, including
  zero-valued scores.
- [x] 1.8.4 Keep the rerank score for debugging.
  Done in `backend/rag/models.py` and
  `backend/rag/reranking/reranker.py`: every selected evidence record retains
  its final RRF score and one-based evidence rank in serialized debug output.
  `tests/rag/test_reranker.py` verifies the serialized score equals the exact
  contribution from both retrieval paths.
- [x] 1.8.5 Verify reranking changes order when the nearest chunk is not the most useful chunk.
  Done in `tests/rag/test_reranker.py`: a focused usefulness scenario gives
  the semantically nearest definition chunk the highest raw similarity, while
  a worked-example chunk appears in both semantic and lexical retrieval.
  RRF promotes the worked example and the test verifies its final score and
  rank exceed the nearest-only chunk without losing either raw score.
- [x] 1.8.6 Define what score is too weak to include.
  Done in `backend/rag/config.py` and
  `backend/rag/reranking/reranker.py`: a semantic-only hit below cosine
  similarity `0.25` is excluded as noise, while lexical hits remain eligible
  because full-text scores are query-dependent and cannot share that cutoff.
  Evidence is strong only when at least three selected chunks meet semantic
  similarity `0.35`; fewer strong chunks produce a weak-evidence status, and
  no usable chunks produce an insufficient-evidence status. These are initial
  policy values to tune against the Phase 3 eval set, not universal constants.
  `tests/rag/test_reranker.py` verifies both threshold boundaries, lexical
  eligibility, rank compaction after filtering, and all evidence statuses.

### Reference: Reranking (`backend/rag/reranking/reranker.py`)

Reference code moved to [docs/ScholarSource_v2_Reference_Code.md](ScholarSource_v2_Reference_Code.md#reference-reranking-backendragrerankingrerankerpy).

### 1.9 Cited Synthesis

*Reference: Prompt Engineering for Context-Aware Q&A (Manning liveProject, Matteus Tanha).*

- [x] 1.9.1 Generate a final study guide from only the selected evidence.
  Implemented in `backend/rag/synthesis/prompt.py` and
  `backend/rag/synthesis/synthesizer.py`: the structured synthesis call receives
  only the student topic and ordered `SelectedEvidence` context blocks. The
  prompt explicitly prohibits external knowledge, excludes stored URLs from
  model context, and rejects empty evidence before any LLM call.
  `tests/rag/test_synthesizer.py` verifies structured output, selected-only
  context, stable evidence order, URL exclusion, and the empty-evidence guard.
- [x] 1.9.2 Require every recommendation to include a source citation.
  Done in `backend/rag/models.py`,
  `backend/rag/synthesis/prompt.py`, and
  `backend/rag/synthesis/synthesizer.py`: every model-facing recommendation
  must contain at least one supporting chunk ID, the synthesis prompt states
  the same requirement explicitly, and the synthesizer rejects any chunk ID
  that was not present in the selected evidence. This keeps citation
  enforcement structural rather than relying on prompt compliance alone.
  `tests/rag/test_synthesizer.py` verifies both uncited recommendations and
  citations outside the selected evidence are rejected.
- [x] 1.9.3 Refuse or soften the answer when retrieved evidence is insufficient.
  Done in `backend/rag/synthesis/synthesizer.py`: insufficient evidence returns
  a transparent limitation without invoking the LLM, weak evidence receives a
  deterministic caution plus the reranker's reason, and unevaluated evidence
  is rejected before synthesis. `tests/rag/test_synthesizer.py` verifies empty
  and below-threshold refusal paths, weak-answer softening, and the no-call
  guarantees.
- [ ] 1.9.4 Include source titles and URLs in the final response.
- [ ] 1.9.5 Avoid presenting unsupported claims as facts.
- [ ] 1.9.6 Verify the answer can be traced back to stored chunks.

### Reference: Synthesis — Prompt and Cited Generation

Reference code moved to [docs/ScholarSource_v2_Reference_Code.md](ScholarSource_v2_Reference_Code.md#reference-synthesis-prompt-and-cited-generation).

### Reference: The Linear Pipeline (`backend/rag/pipeline.py`)

Reference code moved to [docs/ScholarSource_v2_Reference_Code.md](ScholarSource_v2_Reference_Code.md#reference-the-linear-pipeline-backendragpipelinepy).

### Reference: Tests to Write First (`tests/rag/`)

Reference code moved to [docs/ScholarSource_v2_Reference_Code.md](ScholarSource_v2_Reference_Code.md#reference-tests-to-write-first-testsrag).

### 1.10 Unified Input Normalization

- [ ] 1.10.1 Define a typed normalized learning request and per-field
  provenance model shared by every input adapter.
- [ ] 1.10.2 Add an adapter dispatcher that selects the input path from
  validated request fields and rejects ambiguous conflicting primary inputs.
- [ ] 1.10.3 Add a direct adapter for topic lists and optional course, subject,
  chapter, section, and preference context.
- [ ] 1.10.4 Add a URL adapter for course pages and general educational pages
  that detects HTML versus PDF content, reuses v2 extraction, and derives a
  structured learning outline.
- [ ] 1.10.5 Add a book URL adapter that handles catalog or publisher pages,
  readable book pages, and direct PDF URLs without treating the submitted book
  as an automatically approved recommendation.
- [ ] 1.10.6 Add an uploaded-PDF adapter that preserves upload ownership,
  validates file type and size, extracts text with page provenance, and returns
  a structured error for encrypted, corrupt, or image-only files when OCR is
  unavailable.
- [ ] 1.10.7 Decide whether OCR is required for the v2 launch based on
  representative uploaded-book fixtures; if required, document the provider or
  local library, limits, cost, privacy behavior, and fallback policy before
  implementation.
- [ ] 1.10.8 Add an ISBN adapter that validates and canonicalizes ISBN-10 and
  ISBN-13, resolves cached bibliographic and available table-of-contents or
  subject metadata behind a provider interface, records provider provenance,
  and fails transparently when the ISBN does not provide enough learning
  context.
- [ ] 1.10.9 Add a book-metadata adapter for title and optional author,
  edition, chapter, and section fields.
- [ ] 1.10.10 Use schema-constrained, deterministic extraction for unstructured
  HTML, PDF, and ISBN metadata, and validate that every derived topic is
  supported by the adapter's extracted input evidence.
- [ ] 1.10.11 Hash and cache normalization results using the canonical primary
  input, relevant context fields, adapter version, extraction prompt version,
  and provider or OCR version.
- [ ] 1.10.12 Store normalized input, adapter kind, derived-field provenance,
  warnings, confidence, and structured failure state in the run log without
  retaining unnecessary raw user-provided book content.
- [ ] 1.10.13 Add unit, integration, and end-to-end fixtures for a topic list,
  course page, general page, book page, direct book PDF URL, uploaded text PDF,
  ISBN-10, ISBN-13, and book title/author input, plus scanned, encrypted,
  corrupt, inaccessible, ambiguous, and insufficient-metadata failures.
- [ ] 1.10.14 Verify all successful adapters produce the same normalized model
  and enter the same query generation, retrieval, reranking, and synthesis
  functions.

### 1.11 Phase Completion Criteria

- [ ] 1.11.1 Every accepted input type can complete the full v2 path from
  normalization to cited answer without CrewAI.
- [ ] 1.11.2 The answer is based on stored chunks, not live only search output.
- [ ] 1.11.3 Every cited recommendation maps back to source metadata.
- [ ] 1.11.4 You can explain each pipeline step from memory.
- [ ] 1.11.5 You have at least one manual test case per accepted input type
  proving the shared pipeline works end to end.
- [ ] 1.11.6 You can articulate the retrieval evaluation metrics from *Hybrid
  Search and Retrieval Evaluation* (precision, recall, MRR, NDCG,
  groundedness) for your own pipeline's results, even informally.
- [ ] 1.11.7 Adapter failures are visible and structured, and no failed or
  unsupported input silently routes through v1.

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
- [ ] 2.1.6 Version input adapters and structured extraction prompts so the
  same cached source input produces the same normalized learning request.

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
- [ ] 2.4.11 Log input kind, adapter version, canonical input identifier,
  normalization provenance, warnings, and confidence.

### Reference: Run Logging (`backend/rag/runs/logger.py`)

Reference code moved to [docs/ScholarSource_v2_Reference_Code.md](ScholarSource_v2_Reference_Code.md#reference-run-logging-backendragrunsloggerpy).

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
- [ ] 3.1.8 Include successful golden cases for every accepted input type:
  topics, course page, general page, book page, direct PDF URL, uploaded PDF,
  ISBN, and book metadata.
- [ ] 3.1.9 Include normalization failure cases for scanned or invalid PDFs,
  inaccessible URLs, unknown ISBNs, insufficient ISBN metadata, and ambiguous
  multi-input submissions.

### 3.2 Retrieval Evaluation

- [ ] 3.2.1 Measure whether retrieved chunks are relevant to the query.
- [ ] 3.2.2 Measure whether expected source domains appear.
- [ ] 3.2.3 Measure whether forbidden source types are excluded.
- [ ] 3.2.4 Measure whether top results are better than lower-ranked results.
- [ ] 3.2.5 Set an initial threshold for acceptable retrieval quality.
- [ ] 3.2.6 Save baseline retrieval scores.

### Reference: Metric Functions for `evals/`

Reference code moved to [docs/ScholarSource_v2_Reference_Code.md](ScholarSource_v2_Reference_Code.md#reference-metric-functions-for-evals).

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

Reference code moved to [docs/ScholarSource_v2_Reference_Code.md](ScholarSource_v2_Reference_Code.md#reference-langgraph-orchestration-preview-do-not-build-yet).

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

- [ ] 5.1.1 Route the existing job submission contract through the v2 input
  adapter dispatcher and linear pipeline while preserving the public request
  and response envelopes.
- [ ] 5.1.2 Preserve authentication requirements.
- [ ] 5.1.3 Preserve rate limiting requirements.
- [ ] 5.1.4 Preserve job ownership checks.
- [ ] 5.1.5 Return structured failure messages to the frontend.
- [ ] 5.1.6 Keep any temporary v1 rollback switch explicit and global; never
  use CrewAI as a silent per-input fallback.
- [ ] 5.1.7 Run contract and eval gates for every accepted input type, switch
  production submission fully to v2, and verify production run logs identify
  only v2 adapter and pipeline steps.
- [ ] 5.1.8 Remove CrewAI dispatch, agents, tasks, dependencies, environment
  variables, and obsolete tests after full v2 cutover.

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

- [ ] 5.5.1 A signed-in user can submit every supported input type through v2
  from the frontend.
- [ ] 5.5.2 The user can watch progress without refreshing.
- [ ] 5.5.3 The final response includes usable citations.
- [ ] 5.5.4 Expected error states are visible and understandable.
- [ ] 5.5.5 The flow works on desktop and mobile.
- [ ] 5.5.6 No production request imports, dispatches, or executes CrewAI code.

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
- [ ] 6.1.9 Run at least one production smoke test for every accepted input
  type and confirm each run uses the v2 adapter and pipeline.

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
- [ ] Build the canonical normalized learning request.
- [ ] Build and test topic, URL, book URL, PDF, ISBN, and book metadata input adapters.
- [ ] Add run logging.
- [ ] Add run comparison.
- [ ] Build the golden eval set.
- [ ] Add retrieval evals.
- [ ] Add generation evals.
- [ ] Add CI thresholds.
- [ ] Add stateful orchestration and fallback routing.
- [ ] Connect the v2 flow to the backend job system.
- [ ] Connect the v2 flow to the frontend.
- [ ] Cut every accepted input type over to v2 and remove CrewAI.
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
| 10 | `input_adapters/` + normalized learning request; verify topics, course/page URL, book URL, uploaded/direct PDF, ISBN, and book metadata produce the same downstream contract | 1.10 | — |
| 11 | `runs/logger.py`, `pipeline.py`; run every accepted input type end to end and one cached input five times | 1.11, 2.4 | — |
| 12 | `evals/metrics.py` + golden case scoring across all input adapters | 3.1–3.4 | DeepLearning.AI evals course |
| 13 | Backend cutover to v2 and removal of CrewAI | 5.1 | — |
| 14 | LangGraph orchestration, only if evals justify it | 4.x | Book 4 (4.0.3) |

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

Use these checkpoints to review implementation quality and understanding.

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

- [ ] The system can return cited study resources from topic lists, course
  pages, general educational page URLs, book URLs, uploaded book PDFs, ISBNs,
  and book metadata.
- [ ] Every accepted input normalizes into the same typed learning request and
  traverses the same v2 retrieval, reranking, and synthesis pipeline.
- [ ] Retrieved evidence is stored and traceable.
- [ ] Repeated cached runs produce stable top evidence.
- [ ] The eval suite runs locally.
- [ ] The eval suite protects against obvious retrieval regressions.
- [ ] The frontend displays progress, success, empty, and failure states.
- [ ] The production deployment has required environment values.
- [ ] The README explains the rewrite and current metrics.
- [ ] At least one real user feedback cycle has produced a shipped improvement.
- [ ] You can explain and debug every major part of the pipeline.
- [ ] CrewAI code, dependencies, configuration, and runtime paths have been
  removed from the production application.

---

## Appendix: How This Differs From the Codex Guide

Codex's guide (`docs/ScholarSource_RAG_Backend_Implementation_Guide.docx`)
ships typed contracts, hashing, citation utilities, RRF, and `Protocol`
interfaces that raise `NotImplementedError`. Its foundational files (errors,
hashing, model shapes) are deliberately kept compatible here.

The companion reference-code file makes the opposite bet: show the whole thing,
plus several substantive decisions Codex left open:

| Area | Codex guide | Companion reference code |
| --- | --- | --- |
| Core modules | Interfaces only, `NotImplementedError` | Full reference implementations |
| Query generation | Not addressed | Deterministic templates — the direct fix for your Phase 0 root cause |
| pgvector search | Interface only | SQL RPC functions written (`match_rag_chunks`, lexical FTS) |
| Lexical path | "later experiment" | Postgres full-text search now, fused with RRF as the reranker |
| Hallucinated URLs | Citation filtering after the fact | Structural: the LLM only outputs chunk_ids; URLs are joined from storage |
| Sync vs async | Async interfaces | Sync, matching supabase-py and the Celery worker where this runs |
| Weak evidence | Policy deferred | Concrete thresholds in `RagSettings`, marked as Phase 3 tuning targets |

Where the two agree — module boundaries, the `rag_*` schema as the
source of truth, evals before orchestration, LangGraph last — treat that
agreement as strong signal: two independent reviews of the same material
landed on the same architecture.
