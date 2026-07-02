# ScholarSource — Agent Contract

## Stack

Backend: Python 3.12, FastAPI, Pydantic v2, Supabase (PostgreSQL + pgvector), Celery + Redis, OpenAI/Anthropic embeddings and LLMs.
RAG tooling: LangChain for loading, splitting, and retrieval chains; LangGraph for workflow orchestration; Ragas + LangSmith for evals and tracing.
Frontend: React 19, Vite, Tailwind CSS 3, TypeScript/TSX.
Infrastructure: Railway (backend), Cloudflare Pages (frontend), Supabase (db + auth), GitHub Actions (CI/CD).
Quality gates: Ruff for Python linting, import sorting, and formatting; ESLint/Vitest for frontend validation.

## Authorship Rules

The human writes the first version of every core pipeline module: chunker, embedder, vector store client, retriever, reranker, and synthesis prompt.

AI may generate: boilerplate (Pydantic schemas, route stubs, test fixtures, SQL migrations), utility helpers with no retrieval logic, and frontend UI components.

AI may not generate the initial production implementation of any module the human intends to explain or defend in an interview.

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

Database schema and migration files for the RAG pipeline should live under `db/` or `supabase/` if a Supabase migrations directory is introduced. SQL must be reviewed like application code because it defines citation traceability.

## AI Authorship Boundaries

AI must not first-draft the production implementation of these core modules:

- chunker
- embedder
- vector store client
- retriever
- reranker
- synthesis prompt
- source quality policy
- weak-evidence policy
- run logging contract
- LangGraph state schema

AI may first-draft supporting code only when it does not contain core retrieval judgment:

- Pydantic request/response schemas after the human defines the fields.
- FastAPI route stubs after the human defines the behavior.
- Test fixtures, test factories, and mocks.
- SQL migration boilerplate after the human defines table fields and constraints.
- CLI wrappers and inspection scripts.
- Frontend UI components.
- Documentation, checklists, and review prompts.

AI may review, explain, debug, or refactor core modules after the human has written the first working version and can explain the design.

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

Before merging any RAG retrieval, reranking, synthesis, or prompt change, also run the eval suite once it exists:

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
