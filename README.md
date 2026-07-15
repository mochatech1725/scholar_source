# ScholarSource

Find high-quality study resources aligned with a course or textbook for use in
Google NotebookLM.

ScholarSource is a full-stack application that accepts course URLs, textbook
details, ISBNs, PDFs, or topic lists and returns relevant educational resources.
The project is currently evolving from a CrewAI search workflow into a
controlled retrieval-augmented generation (RAG) pipeline.

## Version Status

Two versions currently coexist in this repository:

- **v1 is the production application.** It uses four sequential CrewAI agents
  to analyze course material, discover resources, validate them, and format a
  study guide.
- **v2 is under active development on the `rag-v2` branch.** It replaces the
  nondeterministic agent-driven search flow with a testable, traceable RAG
  pipeline under `backend/rag/`.

The v2 rewrite began after five baseline runs showed that identical inputs
could produce different search plans, source sets, and final recommendations.
The goal is not to eliminate all model variation. It is to control retrieval,
preserve citation traceability, measure quality, and make failures explainable.

## V2 Progress

### Completed

- Recorded and compared five v1 baseline runs.
- Defined citation, source-quality, weak-evidence, and run-logging contracts.
- Added LangSmith tracing and verified model-call timing and token visibility.
- Implemented deterministic query generation and source collection.
- Added source-quality policies with explicit rejection reasons.
- Implemented text extraction with metadata preservation, caching, and failure
  handling.
- Implemented metadata-preserving chunking with stable ordering.
- Implemented OpenAI embeddings with content-hash deduplication.
- Added Supabase pgvector storage, HNSW and metadata indexes, source deletion,
  and similarity-query verification.
- Seeded seven golden cases spanning STEM, humanities, and weak-evidence traps.

### Next

1. Build the semantic retrieval service and return traceable similarity scores.
2. Add weak-evidence thresholds and tests for irrelevant queries.
3. Implement hybrid retrieval and reranking while preserving both retrieval
   and rerank scores.
4. Generate evidence-grounded answers with stored titles, URLs, and chunk IDs.
5. Expand the golden set and add scored retrieval and generation regression
   gates.
6. Add LangGraph orchestration only after the linear pipeline is stable,
   repeatable, and evaluated.

The current eval runner validates the golden-case schema. It does not yet score
the RAG pipeline. Ragas and LangGraph are planned work, not current runtime
dependencies.

See the
[v2 implementation plan](docs/ScholarSource_v2_Implementation_Plan.md),
[v2 learning plan](docs/ScholarSourcev2Learning%20Plan.md), and
[project contract](AGENTS.md) for the detailed roadmap and engineering rules.

## V2 Architecture

```text
Student input
    -> deterministic query generation
    -> candidate source collection
    -> source-quality checks
    -> text extraction
    -> metadata-preserving chunking
    -> embedding and deduplication
    -> Supabase pgvector storage
    -> semantic retrieval                 [next]
    -> hybrid retrieval and reranking     [planned]
    -> cited evidence-only synthesis      [planned]
    -> scored regression evals            [planned]
    -> LangGraph orchestration            [deferred]
```

Every final v2 citation must map back to a stored chunk with a source ID, title,
and verified URL. If fewer than three credible sources are retrieved, or the
best chunks are weakly relevant, the pipeline must return a weak-evidence
response instead of a confident recommendation list.

## Local Supabase Development

V2 database work defaults to the Supabase CLI stack running locally in Docker.
This provides local Postgres, pgvector, Auth, PostgREST, Studio, and API keys
without writing experimental sources, chunks, embeddings, or run logs to the
hosted development or production projects.

The local Supabase HTTP API is normally available at
`http://127.0.0.1:54321`. `SUPABASE_URL` must point to that HTTP API, not to a
raw Postgres connection string.

```bash
supabase start
supabase status
supabase db reset
```

Do not use `supabase db reset --linked` for local RAG development. It targets a
linked hosted project.

Follow [the local Supabase setup guide](docs/supabase_rag_local_setup.md) for
initialization, environment values, schema loading, resets, and safety checks.

## Technology

| Area | Technology |
| --- | --- |
| API | FastAPI, Pydantic |
| Current production AI flow | CrewAI |
| V2 RAG | Python, LangChain OpenAI, LangSmith |
| Embeddings | OpenAI `text-embedding-3-small` |
| Database and vector search | Supabase PostgreSQL with pgvector |
| Background jobs | Celery and Redis |
| Authentication | Supabase Auth and JWT |
| Frontend | React, Vite, Tailwind CSS |
| Testing | pytest, Vitest, React Testing Library, MSW |
| Deployment | Railway, Cloudflare Pages, Supabase |

Dependency versions are pinned in `pyproject.toml`, `uv.lock`, and
`web/package-lock.json`.

## Project Structure

```text
scholar-source/
|-- backend/                  # FastAPI API and Celery worker
|   `-- rag/                  # v2 RAG pipeline
|       |-- sources/          # query generation and source quality
|       |-- extraction/       # fetching, extraction, and caching
|       |-- chunking/         # chunk boundaries and metadata
|       |-- embeddings/       # provider calls and deduplication
|       |-- vector_store/     # Supabase pgvector persistence
|       |-- retrieval/        # semantic retrieval [next]
|       |-- reranking/        # reranking [planned]
|       |-- synthesis/        # cited synthesis [planned]
|       |-- runs/             # structured run logs [planned]
|       `-- orchestration/    # LangGraph wiring [deferred]
|-- src/scholar_source/       # v1 CrewAI system
|-- web/                      # React and Vite frontend
|-- tests/                    # unit, integration, and RAG tests
|-- evals/                    # golden cases and eval runner
|-- migrations/              # incremental database migrations
|-- docs/                     # architecture, plans, and setup guides
|-- supabase_schema.sql       # fresh-database schema
|-- justfile                  # local task aliases
`-- pyproject.toml            # Python dependencies and app version
```

## Prerequisites

- Python 3.10 through 3.12
- [uv](https://docs.astral.sh/uv/)
- Node.js 18 or newer and npm 9 or newer
- Redis for asynchronous v1 jobs, or synchronous mode for local development
- Docker and the Supabase CLI for local v2 database work
- OpenAI and Serper API keys

## Installation

Install the Python project and development dependencies:

```bash
uv sync --extra dev
```

Install frontend dependencies:

```bash
cd web
npm install
cd ..
```

Create local environment files:

```bash
cp .env.example .env.local
cp web/.env.example web/.env.local
```

The backend loads `.env.local` by default when `ENVIRONMENT=local`. Keep all
real keys out of version control.

For v2 work, replace the placeholder Supabase values with the local values
printed by `supabase status -o env`. The backend and frontend must use keys from
the same Supabase instance so authentication tokens can be verified.

### Important Backend Variables

| Variable | Purpose |
| --- | --- |
| `ENVIRONMENT` | Selects `.env.local`, `.env.dev`, or `.env.prod` |
| `OPENAI_API_KEY` | v1 model calls and v2 embeddings |
| `SERPER_API_KEY` | v1 and v2 source discovery |
| `IN_LOCAL_SUPABASE_MODE` | Allows the local Supabase development path |
| `SUPABASE_URL` | Supabase HTTP API URL |
| `SUPABASE_ANON_KEY` | Browser-safe Supabase key |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-side RAG storage and run logging |
| `SUPABASE_JWT_SECRET` | Backend JWT verification |
| `DATABASE_URL` | Optional direct PostgreSQL access |
| `REDIS_URL` | Celery queue and distributed rate limiting |
| `SYNC_MODE` | Runs v1 jobs in-process when set to `true` |
| `ALLOW_IN_MEMORY_RATE_LIMIT` | Allows local rate limiting without Redis |
| `LANGSMITH_API_KEY` | LangSmith tracing |
| `LANGSMITH_PROJECT` | Trace project name |

See `.env.example` and `web/.env.example` for the complete configuration.

## Running the Current Application

The web application still executes the v1 CrewAI flow. The v2 pipeline is not
yet connected to the public API or frontend.

With Redis running, start the API, worker, and frontend in separate terminals:

```bash
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

```bash
./scripts/start_worker.sh
```

```bash
cd web
npm run dev
```

For simpler local v1 development without Redis, set these values in
`.env.local` and do not start the worker:

```env
SYNC_MODE=true
ALLOW_IN_MEMORY_RATE_LIMIT=true
```

The frontend runs at <http://localhost:5173> and the API runs at
<http://localhost:8000>.

Check API health:

```bash
curl http://localhost:8000/api/health
```

The response includes the canonical application version from `pyproject.toml`:

```json
{
  "status": "healthy",
  "version": "1.2.0",
  "database": "skipped"
}
```

## Current V1 Request Flow

```text
Frontend -> POST /api/submit
         -> create an authenticated Supabase job
         -> enqueue a Celery task, or run synchronously
         -> poll GET /api/status/{job_id}
         -> display the completed resource guide
```

Authenticated users can submit jobs, inspect their status, cancel them, and
upload PDFs. Root and health endpoints are public.

## Validation

Run the full project checks before merging:

```bash
uv run --extra dev ruff check .
uv run --extra dev ruff format --check .
uv run --extra dev pytest tests/ -x
cd web && npm run lint
cd web && npm run test:run
uv run --extra dev run-evals
```

If `just` is installed, `just validate` runs the same sequence. The eval command
currently validates the golden-case contract; scored RAG quality gates are
planned for Phase 3.

## Security and Traceability

- Supabase JWT authentication and per-user job ownership
- Row-level security policies for persisted user data
- CORS and CSRF origin validation
- Input validation, prompt-injection checks, and SSRF-aware URL validation
- Redis-backed rate limiting in distributed environments
- PDF extension, MIME type, magic-byte, and size validation
- V2 source-quality rejection reasons and verified source URLs
- V2 content hashes, embedding-model identifiers, and citation metadata
- No synthesis call when retrieved evidence is empty

## Deployment

The current frontend deploys to Cloudflare Pages. The FastAPI web process and
Celery worker deploy to Railway, with Supabase for authentication and database
storage and Redis for queueing and rate limiting.

See [the deployment plan](docs/Deployment_Plan.md) for environment variables,
process configuration, and deployment checks.

## Documentation

- [V2 implementation plan](docs/ScholarSource_v2_Implementation_Plan.md)
- [V2 learning plan](docs/ScholarSourcev2Learning%20Plan.md)
- [Local Supabase RAG setup](docs/supabase_rag_local_setup.md)
- [RAG eval documentation](evals/README.md)
- [API documentation](docs/api.md)
- [System design document](docs/scholar_source_SDD.md)
- [Technical design document](docs/scholar_source_TDD.md)
- [Testing guide](docs/TESTING_GUIDE.md)
- [Deployment plan](docs/Deployment_Plan.md)

## License

No standalone license file is currently included in this repository. Third-party
dependencies remain subject to their respective licenses.
