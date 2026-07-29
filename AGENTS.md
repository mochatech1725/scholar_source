# ScholarSource — Agent Contract

This file is the system contract for ScholarSource v2 RAG work: implementation
authority, module layout, required metadata, validation gates, and hard rules.
Repo orientation — stack, directory structure, commands, environment
variables — lives in `CLAUDE.md`, which imports this file so both load
together. Do not duplicate orientation content here.

## Implementation Authority

AI may implement, test, review, explain, debug, and refactor every ScholarSource
module, including core RAG modules and retrieval-policy decisions. Follow the
module boundaries, metadata requirements, validation gates, and hard rules in
this contract for all generated changes.

Keep important design decisions explicit in code, tests, and documentation so
the system remains understandable, maintainable, and defensible.

## Implementation Request Source

When the user asks to implement a numbered feature or step (for example,
“implement 1.8.3”), resolve that request against
`docs/ScholarSource_v2_Implementation_Plan.md`. Read the complete plan and the
referenced implementation material before editing, then implement the named
item, its tests, its documentation/checklist update, and the applicable
validation gates. Use a different source only when the user explicitly names
one.

## RAG Repo Layout

RAG pipeline code should live under `backend/rag/`.

Expected module boundaries:

- `backend/rag/sources/`: source collection, URL normalization, source quality checks, and source rejection reasons.
- `backend/rag/extraction/`: page fetching, text extraction, extraction caching, and extraction failure handling.
- `backend/rag/chunking/`: chunk boundary logic, chunk ordering, chunk metadata preservation, and chunk inspection helpers.
- `backend/rag/embeddings/`: embedding provider calls, content hashing, embedding deduplication, and embedding model tracking.
- `backend/rag/vector_store/`: pgvector/Supabase storage client code and similarity query helpers.
- `backend/rag/retrieval/`: query embedding, top-k retrieval, score handling, weak-evidence detection, and retrieval result models.
- `backend/rag/reranking/`: rerank scoring, rerank ordering, and threshold decisions.
- `backend/rag/synthesis/`: cited response generation, evidence-only prompting, weak-evidence responses, and evidence/synthesis separation.
- `backend/rag/runs/`: structured run log creation, run step updates, failure logging, and run comparison helpers.
- `backend/rag/orchestration/`: LangGraph state and graph wiring. Do not add this until the linear pipeline is stable, repeatable, and evaluated.

Shared Pydantic models may live in `backend/rag/models.py` or a `backend/rag/models/` package once splitting is justified. RAG tests should mirror the implementation layout under `tests/rag/`.

RAG evaluation assets should live under `evals/`.

Expected eval layout:

- `evals/golden_cases.json`: representative student queries with expected sources/domains, forbidden sources, and expected concepts.
- `evals/run_evals.py`: repeatable local eval runner.
- `evals/README.md`: eval purpose, required environment variables, scoring thresholds, and local/CI usage.
- `evals/results/`: generated eval outputs. Commit only small baseline summaries; do not commit large traces, raw provider outputs, secrets, or private user content.

Database schema and migration files for the RAG pipeline live in two places:

- `supabase_schema.sql`: complete fresh-database bootstrap schema.
- `migrations/`: incremental SQL migrations for existing databases.

SQL must be reviewed like application code because it defines citation traceability.

## Required RAG Metadata

Every stored source record must include:

- `source_id`
- `url`
- `normalized_url`
- `title`
- `source_type`
- `quality_status`
- `quality_reason`
- `first_seen_at`
- `last_checked_at`

Every rejected source record must include:

- `url`
- `normalized_url`
- `rejection_reason`
- `rejected_at`
- `run_id`

Every extracted document record must include:

- `source_id`
- `url`
- `title`
- `extracted_text_hash`
- `extraction_status`
- `extraction_error`
- `extracted_at`

Every stored chunk must include:

- `chunk_id`
- `source_id`
- `url`
- `title`
- `chunk_index`
- `content`
- `content_hash`
- `embedding_model`
- `created_at`

Every embedding record must include:

- `chunk_id`
- `content_hash`
- `embedding_model`
- `embedding_dimensions`
- `embedded_at`

Every run log must include:

- `run_id`
- `user_id` or an approved non-identifying trace key
- normalized input
- generated queries
- candidate source URLs
- accept/reject reasons
- extraction status
- chunk IDs
- retrieval scores
- rerank order
- final selected evidence
- final cited source IDs
- weak-evidence status and reason
- model name
- prompt version
- major step timings
- token usage and provider cost when available
- structured failure state when the run fails

Do not log raw user-submitted content beyond what is required for job processing and traceability.

## Validation Before Merge

Before merging any backend or pipeline change, run:

```bash
uv run --extra dev ruff check .
uv run --extra dev ruff format --check .
uv run --extra dev pytest tests/ -x
```

Before merging any frontend change, run:

```bash
cd web && npm run lint
cd web && npm run test:run
```

Before merging any RAG retrieval, reranking, synthesis, or prompt change, also run the eval suite:

```bash
uv run --extra dev python evals/run_evals.py
```

If a validation gate is known to fail because of existing unrelated debt, record the failing command, the first failing error, and why it is unrelated to the change. Do not mark new pipeline work complete if it weakens citation traceability, run logging, source quality checks, or weak-evidence handling.

## Hard Rules — Never Break

1. Never return a source to the user without a verified, stored URL.
2. Every cited recommendation must map back to a stored chunk with a source ID, URL, and title.
3. Every generated answer must explicitly separate retrieved evidence from model synthesis.
4. Never embed a chunk without storing its content hash and the embedding model identifier alongside it.
5. Never skip a run log entry — every submitted query must produce a structured run record before the pipeline returns.
6. Never present a low-confidence retrieval result as a confident answer; surface a weak-evidence warning instead.
7. Never store or log raw user-submitted content beyond what is required for job processing and traceability.
8. Never call an LLM for synthesis when retrieved evidence is empty; return a transparent limitation message instead.
9. Never cite a source unless it passed source-quality checks: accessible URL, relevant content, identifiable title, and no obvious copyright or spam risk.
10. Reject pirated textbooks, answer-key sites, low-quality SEO pages, inaccessible pages, and sources with no extractable educational content.
11. Every run log must include generated queries, candidate source URLs, accept/reject reasons, extraction status, chunk IDs, retrieval scores, rerank order, model name, and prompt version.
12. If fewer than three credible sources are retrieved, or the top retrieved chunks are weakly relevant, return a weak-evidence response instead of a normal recommendation list.
13. Never invent titles, URLs, authors, publication dates, chunk IDs, or citation metadata.

## V2 Architecture Goal

ScholarSource v2 replaces the nondeterministic CrewAI search flow with a controlled RAG pipeline: deterministic query generation, source collection, extraction, chunking, embedding, pgvector retrieval, reranking, cited synthesis, and eval-backed release checks. LangGraph may orchestrate the workflow after the pipeline is stable, but retrieval quality, traceability, and grounded citations are the core system contract.
