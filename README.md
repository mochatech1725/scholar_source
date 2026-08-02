# ScholarSource

**Turn a course, book, or topic into a cited set of high-quality study
resources.**

> Status: v1 is the current application. A controlled, traceable v2 RAG
> pipeline is under active development.

---

## What ScholarSource Does

ScholarSource helps students find useful learning material without asking them
to translate their course into perfect search queries. A student can provide a
course page, another educational page, a book URL, an uploaded book PDF, an
ISBN, book details, or a topic list. ScholarSource derives the learning context,
finds relevant resources, rejects weak or unsafe sources, and builds a study
guide whose recommendations link back to verified source evidence.

The v2 design has one load-bearing idea: **every input becomes the same
normalized learning request before retrieval begins**. Input adapters handle
the mechanical differences between HTML, PDFs, ISBN metadata, and explicit
topics. After that boundary, every request follows the same deterministic
collection, retrieval, reranking, and cited-synthesis path.

The intended result is a resource guide that can be inspected directly or used
to assemble a source collection in Google NotebookLM.

---

## The Problem

Finding material for a real course is harder than searching for its title.

1. **Course context arrives in inconsistent forms.** A syllabus page, textbook
   PDF, ISBN, and handwritten topic list may describe the same class in
   completely different ways.
2. **Search results are noisy.** Pirated books, answer-key sites, inaccessible
   pages, SEO content, and weakly related material can look credible at a
   glance.
3. **Generated recommendations are difficult to trust.** A polished answer is
   not useful when its URLs were invented, its evidence cannot be inspected,
   or the system hides uncertainty.
4. **Agent-driven search is difficult to reproduce.** ScholarSource v1
   baseline runs showed that identical inputs could lead to different search
   plans, candidate sources, and final recommendations.

ScholarSource v2 makes input normalization, retrieval policy, source quality,
citations, and weak-evidence behavior explicit and testable.

---

## How a Request Moves Through v2

```text
 Course page       Page or book URL       PDF upload       ISBN       Topics
      |                    |                   |              |           |
      +--------------------+-------------------+--------------+-----------+
                                       |
                           +-----------v-----------+
                           |     Input adapters     |
                           | fetch, parse, validate |
                           +-----------+-----------+
                                       |
                           +-----------v-----------+
                           | Normalized learning    |
                           | request                |
                           | topics + context +     |
                           | provenance + warnings  |
                           +-----------+-----------+
                                       |
                           +-----------v-----------+
                           | Deterministic queries  |
                           +-----------+-----------+
                                       |
                           +-----------v-----------+
                           | Candidate collection   |
                           | + source-quality rules |
                           +-----------+-----------+
                                       |
                           +-----------v-----------+
                           | Extract -> chunk ->    |
                           | embed -> pgvector      |
                           +-----------+-----------+
                                       |
                           +-----------v-----------+
                           | Semantic + lexical     |
                           | retrieval and rerank   |
                           +-----------+-----------+
                                       |
                           +-----------v-----------+
                           | Weak-evidence check    |
                           +-----------+-----------+
                                       |
                           +-----------v-----------+
                           | Evidence-only          |
                           | cited synthesis        |
                           +-----------+-----------+
                                       |
                           +-----------v-----------+
                           | Verified resource      |
                           | guide + source links   |
                           +-----------------------+
```

The adapters are intentionally narrow:

- Topic lists are normalized directly.
- Course and educational pages are fetched and reduced to a structured
  learning outline.
- Book pages and direct PDF URLs use the same extraction contract.
- Uploaded PDFs preserve user ownership and page provenance. V2 launch does
  not perform OCR: image-only files fail explicitly, while mixed files must
  meet deterministic text-coverage thresholds and warn about skipped pages.
- ISBNs resolve bibliographic and available contents or subject metadata
  through a replaceable provider.
- Book title and author fields become structured book context.

Adapters derive context; they do not recommend resources. Once normalization
finishes, input type no longer changes the downstream pipeline.

---

## Trust Guarantees

ScholarSource v2 is designed around guarantees that can be checked in code and
tests:

- Every recommendation must map to a stored chunk, source ID, title, and
  verified URL.
- Source URLs are resolved from stored metadata, not generated by the model.
- Retrieved evidence is kept separate from model synthesis.
- Every candidate source receives an accept or reject reason.
- Every chunk stores its content hash and embedding-model identifier.
- Every submitted request produces a structured run record.
- Empty evidence never triggers an LLM synthesis call.
- Fewer than three credible sources, or weakly relevant top chunks, produce a
  visible weak-evidence response.
- Pirated textbooks, answer-key sites, spam, and sources without extractable
  educational content are rejected.
- Input-adapter failures are explicit and never silently rerouted through v1.

---

## Current Status

### Implemented in the v2 foundation

- Deterministic query generation and candidate source collection
- Source-quality policy with persisted rejection reasons
- HTML and text-based PDF extraction with failure handling
- Uploaded-PDF ownership checks, page-level text coverage, and explicit
  no-OCR failure and mixed-file warning behavior
- Ordered, metadata-preserving chunking
- OpenAI embeddings with content-hash deduplication
- Supabase PostgreSQL and pgvector persistence
- Semantic and lexical retrieval with traceable scores
- Reciprocal-rank-fusion reranking and weak-evidence classification
- Evidence-only structured synthesis with citation-ID validation
- Golden-case and evaluation scaffolding
- LangSmith tracing for model timing and token usage

### Required before v2 replaces v1

- Complete the shared linear pipeline and citation resolution
- Implement every input adapter and its normalization cache
- Add structured run logging and same-input comparison
- Expand and score retrieval and generation evals
- Connect the v2 pipeline to authenticated background jobs and the frontend
- Verify every supported input through end-to-end and production smoke tests
- Remove CrewAI runtime paths and dependencies after the v2 cutover

CrewAI may remain temporarily as a global rollback option during migration. It
is not the final implementation for any input type, and ScholarSource v2 is not
complete until production requests no longer invoke it.

See the [v2 implementation plan](docs/ScholarSource_v2_Implementation_Plan.md)
for the numbered execution checklist.

---

## Technology

| Area | Technology |
| --- | --- |
| API | FastAPI, Pydantic |
| V2 retrieval pipeline | Python, LangChain OpenAI, LangSmith |
| Embeddings | OpenAI `text-embedding-3-small` |
| Database and vector search | Supabase PostgreSQL, pgvector |
| Background jobs | Celery, Redis |
| Authentication | Supabase Auth, JWT |
| Frontend | React, Vite, Tailwind CSS |
| Testing | pytest, Vitest, React Testing Library, MSW |
| Deployment | Railway, Cloudflare Pages, Supabase |

Dependency versions are pinned in `pyproject.toml`, `uv.lock`, and
`web/package-lock.json`.

---

## Repository Layout

```text
scholar-source/
|-- backend/
|   |-- main.py                 # FastAPI application
|   `-- rag/                    # controlled v2 pipeline
|       |-- sources/            # queries, collection, quality policy
|       |-- extraction/         # HTML and PDF extraction
|       |-- chunking/           # stable chunk boundaries and metadata
|       |-- embeddings/         # embedding calls and deduplication
|       |-- vector_store/       # Supabase and pgvector persistence
|       |-- retrieval/          # semantic and lexical retrieval
|       |-- reranking/          # result fusion and evidence thresholds
|       |-- synthesis/          # evidence-only cited generation
|       |-- runs/               # structured run logs
|       `-- orchestration/      # deferred until the linear path is stable
|-- src/scholar_source/         # current v1 CrewAI implementation
|-- web/                        # React frontend
|-- tests/                      # unit, integration, and RAG tests
|-- evals/                      # golden cases and eval runner
|-- migrations/                # incremental database migrations
|-- docs/                       # plans, architecture, and setup guides
|-- supabase_schema.sql         # fresh-database schema
|-- justfile                    # development task aliases
`-- pyproject.toml              # Python dependencies and app version
```

---

## Run Locally

### Prerequisites

- Python 3.10 through 3.12
- [uv](https://docs.astral.sh/uv/)
- Node.js 18 or newer and npm 9 or newer
- Docker and the Supabase CLI
- Redis for queued jobs, or synchronous mode for local v1 development
- OpenAI and Serper API keys

### Install

```bash
uv sync --extra dev
cd web
npm install
cd ..
cp .env.example .env.local
cp web/.env.example web/.env.local
```

The backend loads `.env.local` when `ENVIRONMENT=local`. Keep real credentials
out of version control.

### Start local Supabase

```bash
supabase start
supabase status
supabase db reset
```

Use the values printed by `supabase status -o env` in `.env.local`.
`SUPABASE_URL` must be the local HTTP API, normally
`http://127.0.0.1:54321`, rather than a raw PostgreSQL connection string.

Do not run `supabase db reset --linked` for local RAG development because it
targets a linked hosted project. Follow the
[local Supabase setup guide](docs/supabase_rag_local_setup.md) for the complete
workflow.

### Start the application

Run the API, worker, and frontend in separate terminals:

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

The frontend runs at <http://localhost:5173> and the API at
<http://localhost:8000>.

For local v1 development without Redis, set:

```env
SYNC_MODE=true
ALLOW_IN_MEMORY_RATE_LIMIT=true
```

Then start only the API and frontend.

---

## Validation

Run the project gates before merging:

```bash
uv run --extra dev ruff check .
uv run --extra dev ruff format --check .
uv run --extra dev pytest tests/ -x
cd web && npm run lint
cd web && npm run test:run
uv run --extra dev python evals/run_evals.py
```

If `just` is installed, `just validate` runs the combined validation workflow.
The eval runner currently validates the golden-case contract; scored RAG
quality gates are planned.

---

## Documentation

- [V2 implementation plan](docs/ScholarSource_v2_Implementation_Plan.md)
- [V2 learning plan](docs/ScholarSourcev2Learning%20Plan.md)
- [Local Supabase RAG setup](docs/supabase_rag_local_setup.md)
- [RAG evaluation guide](evals/README.md)
- [API reference](docs/api.md)
- [System design](docs/scholar_source_SDD.md)
- [Technical design](docs/scholar_source_TDD.md)
- [Testing guide](docs/TESTING_GUIDE.md)
- [Deployment plan](docs/Deployment_Plan.md)

## License

No standalone license file is currently included. Third-party dependencies
remain subject to their respective licenses.
