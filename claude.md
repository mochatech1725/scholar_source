# Claude Development Guidelines

## Project Reference

### What This Project Is

**ScholarSource** - an AI-powered study resource finder. Users submit course
info (URL, textbook, ISBN, PDF, or topic list) and a CrewAI multi-agent
pipeline searches, validates, and formats supplementary learning resources
into a markdown study guide optimized for import into NotebookLM.

---

### Directory Structure

```text
scholar_source/
|-- backend/                  # FastAPI REST API + Celery worker
|-- src/scholar_source/       # CrewAI multi-agent system
|   |-- config/               # agents.yaml, tasks.yaml
|   `-- tools/                # Custom CrewAI tools
|-- web/                      # React + Vite frontend
|   `-- src/
|       |-- pages/            # HomePage.jsx
|       |-- components/       # Auth/, ui/, feature components
|       |-- api/client.js     # Supabase + API client
|       `-- contexts/         # AuthContext.jsx
|-- tests/                    # unit/, integration/, e2e/
|-- scripts/                  # Utility + test scripts
|-- docs/                     # SDD, TDD, Deployment, Testing docs
|-- supabase_schema.sql       # DB schema + RLS policies
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
- CrewAI CLI: `src/scholar_source/main.py`
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

# Python tests
pytest
pytest tests/unit
pytest tests/integration

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
| AI Agents | CrewAI 0.120.1 |
| LLM | OpenAI GPT-4o / GPT-4o-mini |
| Search | Serper API + YouTube search tool |
| Database | Supabase (PostgreSQL) via supabase-py 2.9.1 |
| Auth | Supabase JWT + PyJWT 2.9.0 |
| Task Queue | Celery 5.4.0 + Redis 5.2.0 |
| Rate Limiting | SlowAPI 0.1.9 |
| Email | Resend 0.8.0 |
| Validation | Pydantic 2.9.2 |
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

### CrewAI Agents (4 Sequential)

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

### Job Processing Flow

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
- Agent definitions:
  `src/scholar_source/crew.py`, `src/scholar_source/config/agents.yaml`
- Task definitions: `src/scholar_source/config/tasks.yaml`
- DB schema and RLS: `supabase_schema.sql`
- Deployment: `Procfile.railway`, `docs/Deployment_Plan.md`
- Architecture: `docs/scholar_source_SDD.md`
- Frontend main UI: `web/src/pages/HomePage.jsx`
