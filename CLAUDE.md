# Claude Development Guidelines

@AGENTS.md

## Project Reference

### What This Project Is

**ScholarSource** - an AI-powered study resource finder. Users submit course
info (URL, textbook, ISBN, PDF, or topic list) and the backend searches,
validates, and formats supplementary learning resources into a markdown study
guide optimized for import into NotebookLM.

Two generations coexist in this repo:

- **v1 (production):** a CrewAI multi-agent pipeline in `src/scholar_source/`.
- **v2 (in progress, `rag-v2` branch):** a deterministic RAG pipeline in
  `backend/rag/` that replaces the CrewAI search flow. The v2 system
  contract — module boundaries, required metadata, hard rules, and
  validation gates — lives in `AGENTS.md` (imported above); it is the
  authority on all RAG pipeline work.

---

### Directory Structure

```text
scholar_source/
|-- backend/                  # FastAPI REST API + Celery worker
|   `-- rag/                  # v2 RAG pipeline (module layout in AGENTS.md)
|-- src/scholar_source/       # v1 CrewAI multi-agent system
|   |-- config/               # agents.yaml, tasks.yaml
|   `-- tools/                # Custom CrewAI tools
|-- web/                      # React + Vite frontend
|   `-- src/
|       |-- pages/            # HomePage.jsx
|       |-- components/       # Auth/, ui/, feature components
|       |-- api/client.js     # Supabase + API client
|       `-- contexts/         # AuthContext.jsx
|-- tests/                    # unit/, integration/, e2e/, rag/
|-- evals/                    # RAG eval suite: golden cases, runner, results
|-- migrations/               # Incremental SQL migrations for RAG schema
|-- scripts/                  # Utility + test scripts
|-- docs/                     # SDD, TDD, Deployment, Testing docs
|-- supabase_schema.sql       # Fresh-database bootstrap schema + RLS policies
|-- Procfile.railway          # Railway process definitions
|-- nixpacks.toml             # Railway build config (libmagic1)
`-- pyproject.toml            # Python project config (version source of truth)
```

---

### Entry Points

- Backend API: `backend/main.py`
  Command: `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`
- Celery worker: `scripts/start_worker.sh`
  Command: `./scripts/start_worker.sh`
- Frontend: `web/src/main.jsx`
  Command: `cd web && npm run dev` (port 5173)
- CrewAI CLI (v1): `src/scholar_source/main.py`
  Command: `crewai run`

---

### Build & Run Commands

```bash
# Backend
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
./scripts/start_worker.sh             # Celery worker (requires Redis)
# Set SYNC_MODE=true in .env to skip Redis for local dev

# Frontend (from web/)
npm install
npm run dev           # dev server
npm run build         # production build to web/dist
npm run lint          # ESLint
npm test              # Vitest (watch)
npm run test:run      # Vitest (single run)

# Python lint, format, tests (via uv)
uv run --extra dev ruff check .
uv run --extra dev ruff format --check .
uv run --extra dev pytest tests/ -x
uv run --extra dev pytest tests/rag        # RAG pipeline tests only

# RAG evals
uv run --extra dev python evals/run_evals.py

# Version sync (web/package.json from pyproject.toml)
python3 scripts/sync_web_package_version.py
```

---

### Tech Stack

#### Backend

| Layer | Technology |
| --- | --- |
| Framework | FastAPI 0.115.0 |
| Server | Uvicorn (ASGI) |
| AI Agents (v1) | CrewAI 0.120.1 |
| RAG (v2) | LangChain (langchain-openai 1.3.3) + LangSmith 0.9.5 |
| LLM | OpenAI GPT-4o / GPT-4o-mini |
| Embeddings (v2) | OpenAI text-embedding-3-small (1536 dims) |
| Search | Serper API + YouTube search tool |
| Database | Supabase (PostgreSQL + pgvector) via supabase-py 2.9.1 |
| Auth | Supabase JWT + PyJWT 2.9.0 |
| Task Queue | Celery 5.4.0 + Redis 5.2.0 |
| Rate Limiting | SlowAPI 0.1.9 |
| Email | Resend 0.8.0 |
| Validation | Pydantic 2.9.2 |
| Lint/Format | Ruff (run via uv) |
| Language | Python 3.12 |

#### Frontend

| Layer | Technology |
| --- | --- |
| Framework | React 19.2.0 |
| Build | Vite 7.2.4 |
| Styling | Tailwind CSS 3.4.19 |
| Auth/DB Client | @supabase/supabase-js 2.90.1 |
| Testing | Vitest 1.0.0 + React Testing Library + MSW |
| Language | JavaScript/JSX (ES2020+, Node >=18) |

#### Infrastructure

| Component | Platform |
| --- | --- |
| Frontend | Cloudflare Pages |
| Backend | Railway |
| Database | Supabase (PostgreSQL) |
| Cache/Queue | Redis (Upstash or Redis Cloud) |

---

### Key Backend Modules

- `backend/main.py`: routes for submit, status, and health.
- `backend/models.py`: Pydantic request/response models and input sanitization.
- `backend/auth.py`: JWT verification and Supabase user auth.
- `backend/jobs.py`: CRUD for job records in Supabase.
- `backend/crew_runner.py`: enqueue with Celery or run in sync mode.
- `backend/celery_app.py`: Celery and Redis broker config.
- `backend/tasks.py`: Celery task definitions.
- `backend/security_utils.py`: URL validation and prompt injection detection.
- `backend/rate_limiter.py`: Redis-backed or in-memory rate limiting.
- `backend/markdown_parser.py`: parse crew JSON output to markdown.
- `backend/email_service.py`: Resend API integration.
- `backend/rag/`: v2 RAG pipeline — sources, extraction, chunking,
  embeddings, vector_store, retrieval, reranking, synthesis, runs,
  orchestration. Module responsibilities are defined in `AGENTS.md`.
- `backend/rag/config.py`: every tunable RAG value (models, chunk sizes,
  retrieval limits, weak-evidence thresholds) in one place.

### CrewAI Agents (v1, 4 Sequential)

1. **Course Intelligence Agent** - extracts topics from URL/book/ISBN/PDF
2. **Resource Discovery Agent** - finds 5-7 resources via Serper + YouTube
3. **Resource Validator Agent** - verifies URLs, copyright, and NotebookLM
   compatibility
4. **Output Formatter Agent** - produces student-friendly markdown study guide

Custom tools: `WebPageFetcherTool`, `TOCExtractorTool`

---

### Environment Variables

**Backend (`.env`)** - key vars:

```dotenv
ENVIRONMENT=local
OPENAI_API_KEY=...
SERPER_API_KEY=...
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_JWT_SECRET=...
REDIS_URL=redis://localhost:6379/0
SYNC_MODE=false          # true = no Redis needed
ALLOW_IN_MEMORY_RATE_LIMIT=false
LOG_LEVEL=INFO
```

**Frontend (`web/.env.local`)**:

```dotenv
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=...
VITE_SUPABASE_ANON_KEY=...
VITE_SEARCH_TIMEOUT_MINUTES=5
```

---

### Job Processing Flow (v1)

```text
Frontend -> POST /api/submit
         -> job created in Supabase (UUID, "pending")
         -> enqueued to Celery/Redis (or runs sync if SYNC_MODE=true)
         -> polls GET /api/status/{job_id} every 2s

Celery Worker:
  1. Course Intelligence Agent   (analyze course input)
  2. Resource Discovery Agent    (Serper + YouTube search)
  3. Resource Validator Agent    (verify quality/legality)
  4. Output Formatter Agent      (generate markdown)
  -> updates job to "completed" with results JSON + raw_output markdown
```

---

### Key Files Quick Reference

- API routes and middleware: `backend/main.py`
- Request/response shapes: `backend/models.py`
- Auth flow: `backend/auth.py`, `web/src/contexts/AuthContext.jsx`
- v1 agent definitions:
  `src/scholar_source/crew.py`, `src/scholar_source/config/agents.yaml`
- v1 task definitions: `src/scholar_source/config/tasks.yaml`
- v2 RAG config and tunables: `backend/rag/config.py`
- v2 shared RAG models: `backend/rag/models.py`
- v2 system contract: `AGENTS.md`
- DB schema and RLS: `supabase_schema.sql`
- Incremental migrations: `migrations/`
- RAG eval suite: `evals/golden_cases.json`, `evals/run_evals.py`
- Deployment: `Procfile.railway`, `docs/Deployment_Plan.md`
- Architecture: `docs/scholar_source_SDD.md`
- Frontend main UI: `web/src/pages/HomePage.jsx`
