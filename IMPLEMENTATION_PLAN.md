# ScholarSource Implementation Plan

Complete implementation guide and roadmap for the ScholarSource web application.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Implementation Status](#implementation-status)
4. [Setup & Installation](#setup--installation)
5. [Testing Guide](#testing-guide)
6. [Future Enhancements](#future-enhancements)
7. [Deployment](#deployment)
8. [Troubleshooting](#troubleshooting)

---

## Project Overview

**ScholarSource** helps students discover high-quality educational resources aligned with their course textbooks for use with Google NotebookLM.

### Key Features
- ✅ Two-column layout (form + results)
- ✅ Light, professional design
- ✅ Easy copy/paste functionality
- ✅ Background job processing
- ✅ Persistent storage (Supabase)

### Tech Stack
- **Frontend:** React + Vite
- **Backend:** FastAPI + Python
- **Database:** Supabase PostgreSQL
- **AI:** CrewAI with GPT-4o/GPT-4o-mini
- **Deployment:** Railway (backend) + Cloudflare Pages (frontend)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND (React/Vite)                                      │
│  http://localhost:5173                                      │
│                                                             │
│  - HomePage (form + results)                                │
│  - CourseForm, LoadingStatus, ResultsTable                  │
└─────────────────┬───────────────────────────────────────────┘
                  │ HTTP Requests (POST /api/submit, GET /api/status/*)
┌─────────────────▼───────────────────────────────────────────┐
│  BACKEND (FastAPI)                                          │
│  http://localhost:8000                                      │
│                                                             │
│  - Job submission & validation                              │
│  - Background crew execution                                │
│  - Status polling                                           │
│  - Markdown parsing                                         │
└─────────────────┬───────────────────────────────────────────┘
                  │ Database Operations (Supabase Python Client)
┌─────────────────▼───────────────────────────────────────────┐
│  SUPABASE PostgreSQL                                        │
│  (Cloud Database)                                           │
│                                                             │
│  - jobs table (UUID, status, inputs, results, timestamps)  │
│  - Persistent storage (survives restarts)                  │
│  - RLS policies for security                               │
└─────────────────────────────────────────────────────────────┘
```

### File Structure

```
scholar_source/
├── backend/                      # FastAPI backend
│   ├── __init__.py
│   ├── database.py               # Supabase client
│   ├── models.py                 # Pydantic models
│   ├── jobs.py                   # Job management
│   ├── crew_runner.py            # CrewAI execution
│   ├── markdown_parser.py        # Output parsing
│   └── main.py                   # FastAPI app (3 endpoints)
│
├── web/                          # React/Vite frontend
│   ├── src/
│   │   ├── api/client.js         # API communication
│   │   ├── components/           # CourseForm, LoadingStatus, ResultsTable
│   │   ├── pages/                # HomePage
│   │   ├── App.jsx               # Main component
│   │   └── index.css             # Global styles
│   ├── .env.example              # Frontend config template
│   └── vite.config.js
│
├── src/scholar_source/           # CrewAI implementation (existing)
│   ├── crew.py
│   ├── main.py
│   └── config/
│
├── .env.example                  # Backend config template
├── .env.local                    # Backend secrets (not committed)
├── pyproject.toml                # Python dependencies
└── supabase_schema.sql           # Database schema
```

---

## Implementation Status

### ✅ Part 0: Supabase Setup (Complete)
- [x] Create Supabase project
- [x] Create jobs table in database
- [x] Set up Row Level Security policies
- [x] Get API credentials (URL and anon key)
- [x] Add credentials to .env.local file

### ✅ Part 1: Backend (FastAPI) Implementation (Complete)
- [x] Update pyproject.toml with FastAPI dependencies
- [x] Create backend directory structure
- [x] Implement backend/database.py (Supabase client)
- [x] Implement backend/models.py (Pydantic models)
- [x] Implement backend/jobs.py (job management with Supabase)
- [x] Implement backend/crew_runner.py (CrewAI integration)
- [x] Implement backend/markdown_parser.py (parse markdown to JSON)
- [x] Implement backend/main.py (FastAPI app with 3 endpoints)
- [ ] Test backend API locally

### ✅ Part 2: Frontend (React/Vite) Implementation (Complete)
- [x] Initialize React/Vite project
- [x] Implement web/src/api/client.js (API client)
- [x] Implement web/src/components/CourseForm.jsx
- [x] Implement web/src/components/LoadingStatus.jsx
- [x] Implement web/src/components/ResultsTable.jsx
- [x] Implement web/src/pages/HomePage.jsx
- [x] Implement web/src/App.jsx (main component)
- [x] Create all CSS files with clean design
- [x] Create web/.env.local configuration
- [x] Create web/vite.config.js
- [✅] Test frontend locally

### Part 3: Integration & Testing (Next)
- [✅] Test full workflow (form submission → job polling → results display)
- [ ] Test error handling (network errors, invalid inputs, etc.)
- [ ] Test persistence (jobs survive server restarts)
- [✅] Validate CORS configuration
- [✅] Test copy buttons and "Copy All URLs" functionality

### Part 4: Documentation
- [x] Update README.md with web app setup instructions
- [ ] Create backend/README.md (API documentation)
- [ ] Create web/README.md (frontend documentation)

### Part 5: Deployment (Future)
- [✅] Deploy backend to Railway
- [✅] Deploy frontend to Cloudflare Pages
- [✅] Configure production environment variables
- [✅] Test production deployment

---

## Setup & Installation

### Prerequisites
- Python 3.10+ with virtual environment
- Node.js 18+ and npm
- Supabase account and project
- OpenAI API key
- Serper API key

### 1. Clone and Setup Environment

```bash
# Clone repository
cd /Users/teial/Tutorials/AI/scholar_source

# Copy environment templates
cp .env.example .env.local
cd web && cp .env.example .env.local && cd ..

# Edit .env.local with your actual API keys
```

**Root `.env.local`:**
```bash
OPENAI_API_KEY=sk-proj-your_key_here
SERPER_API_KEY=your_serper_key_here
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
DATABASE_URL=postgresql://postgres:password@db.your-project-id.supabase.co:5432/postgres
```

**`web/.env.local`:**
```bash
VITE_API_URL=http://localhost:8000
```

### 2. Setup Supabase Database

1. Go to Supabase Dashboard → SQL Editor
2. Run the schema from `supabase_schema.sql`:

```sql
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    inputs JSONB NOT NULL,
    results JSONB,
    raw_output TEXT,
    error TEXT,
    status_message TEXT,
    search_title TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created_at ON jobs(created_at DESC);

ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable all access for jobs" ON jobs FOR ALL USING (true);
```

### 3. Install Dependencies

**Backend:**
```bash
source .venv/bin/activate
pip install -e .
```

Installs: FastAPI, Uvicorn, Supabase, Pydantic, python-dotenv, etc.

**Frontend:**
```bash
cd web
npm install
```

Installs: React, Vite, etc.

### 4. Run the Application

**Terminal 1 - Backend:**
```bash
source .venv/bin/activate
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd web
npm run dev
```

**Access:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Testing Guide

### Backend Testing

#### 1. Health Check
```bash
curl http://localhost:8000/api/health
```

Expected:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "database": "connected"
}
```

#### 2. Submit a Job
```bash
curl -X POST http://localhost:8000/api/submit \
  -H "Content-Type: application/json" \
  -d '{
    "university_name": "MIT",
    "course_name": "Introduction to Algorithms",
    "book_title": "Introduction to Algorithms",
    "book_author": "Cormen, Leiserson, Rivest, Stein"
  }'
```

Save the returned `job_id`!

#### 3. Check Job Status
```bash
curl http://localhost:8000/api/status/{job_id}
```

Statuses: `pending` → `running` → `completed` or `failed`


### Frontend Testing

#### Test 1: Basic Form Submission
1. Open http://localhost:5173
2. Fill in at least one field
3. Click "Find Resources"
4. **Expected:** Loading screen with progress
5. **Wait:** 1-5 minutes
6. **Expected:** Results displayed

#### Test 2: Form Validation
1. Leave all fields blank
2. Click "Find Resources"
3. **Expected:** Error message

#### Test 3: Copy Functionality
1. Click 📋 button next to any URL
2. **Expected:** Button shows ✓
3. Paste to verify

#### Test 4: Copy All URLs
1. Click "📋 Copy All URLs"
2. **Expected:** Plain text, one URL per line
3. Ready for NotebookLM import

#### Test 5: Form Persists
1. After results load, form still visible
2. Modify a field and resubmit
3. **Expected:** New job starts

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information |
| GET | `/api/health` | Health check |
| POST | `/api/submit` | Submit new job |
| GET | `/api/status/{job_id}` | Get job status |

---

## Future Enhancements

### Phase 2: Post-MVP Features

#### Resource Management
- [ ] Job deletion/cleanup (automatic or manual)
- [ ] Job expiration policies (auto-delete after 30/60/90 days)



---

## Improvements & Enhancements

Prioritized list of improvements organized by area and effort level.

### Error Handling & User Feedback (High Priority)

#### Quick Wins (30 minutes - 1 hour each)
- [ ] Add network error detection and user-friendly messages (30 min)
  - Distinguish network timeout vs server error

- [ ] Improve backend error messages with specific suggestions (45 min)
  - Add actionable suggestions to HTTPException details
  - Include "what went wrong" and "how to fix it"
  - Better error messages and user feedback throughout application

- [ ] Add empty results handling with helpful suggestions (30 min)
  - Explain why no resources found
  - Suggest how to improve search (broaden inputs, try different keywords)

#### Medium Effort (2-3 hours each)
- [ ] Implement retry logic with exponential backoff (2 hours)
  - Auto-retry transient network errors (503, 502, timeouts)
  - Show retry countdown to user
  - Manual "Try Again" for non-retryable errors

- [ ] Add specific input validation error messages (2 hours)
  - Field-level validation with specific error messages
  - Suggestions for invalid formats (ISBN, URL, etc.)
  - Real-time validation feedback in form

- [ ] Categorize and improve job failure error messages (3 hours)
  - Detect OpenAI API errors vs network vs validation
  - Show specific next steps based on error type
  - Add "Show Details" option for debugging

#### Larger Projects (4+ hours)
- [ ] Add rate limiting detection and handling (4 hours)
  - Detect 429 responses from backend/OpenAI
  - Show wait time and auto-retry after delay
  - Queue job if rate limited

- [ ] Implement real-time form validation (6 hours)
  - Validate fields as user types
  - Show character counts for text fields
  - Format hints (ISBN: 978-0-xxx-xxxxx-x)

### Code Quality & Testing

#### Quick Wins (1-2 hours each)
- [ ] Standardize code formatting with Black and Prettier (1 hour)
  - Configure Black for Python files
  - Configure Prettier for JavaScript/CSS files
  - Add .prettierrc and pyproject.toml formatting config
  - Run formatters on existing code

- [ ] Fix mypy type errors in backend (2 hours)
  - Add proper type annotations for Supabase responses
  - Use Optional[str] for nullable fields
  - Add type stubs for third-party libraries

#### Medium Effort (4-6 hours each)
- [ ] Set up pre-commit hooks for linting and formatting (3 hours)
  - Configure Black for Python formatting
  - Configure Prettier for JS/CSS formatting
  - Add ESLint for frontend
  - Add mypy for type checking
  - Auto-format on commit

- [ ] Set up pytest and write unit tests (6 hours)
  - Test markdown parser functions
  - Test job validation logic
  - Test API client error handling
  - Create comprehensive test suite

- [ ] Add integration tests for API endpoints (4 hours)
  - Test /api/submit with various inputs
  - Test /api/status polling
  - Test error responses

#### Larger Projects (8+ hours)
- [ ] Refactor markdown parser for better accuracy (8 hours)
  - Improve pattern matching algorithms
  - Add more fallback strategies
  - Better handling of edge cases
  - Test against various markdown formats

- [ ] Achieve 80% test coverage (10 hours)
  - Backend unit tests
  - Frontend component tests (React Testing Library)
  - API integration tests
  - End-to-end tests (Playwright/Cypress)

### Performance & Optimization

#### Quick Wins (1-2 hours each)
- [ ] Add response caching headers (1 hour)
  - Cache static resources (CSS, JS)
  - Set appropriate cache headers for API responses

- [ ] Optimize frontend bundle size (2 hours)
  - Code splitting for large components
  - Lazy load ResultsTable component
  - Remove unused dependencies

#### Medium Effort (3-5 hours each)
- [ ] Implement database query optimization (3 hours)
  - Add indexes for frequently queried fields
  - Optimize job status queries
  - Cache frequently accessed data

- [ ] Add pagination for large result sets (4 hours)
  - Paginate resources table for 50+ results
  - Add "Load More" or page navigation
  - Improve performance for large datasets

#### Larger Projects (6+ hours)
- [ ] Implement streaming progress updates (8 hours)
  - Show which CrewAI agent is currently running
  - Display partial results as they arrive
  - Add WebSocket support for real-time updates

- [ ] Add job queue system (12 hours)
  - Queue jobs when system is busy
  - Show queue position to users
  - Implement priority queue for paid users

### User Experience Enhancements

#### Quick Wins (1-2 hours each)
- [ ] Add "Copy All URLs" button improvements (1 hour)
  - Add format options (plain text, markdown, JSON)
  - Copy with titles and descriptions

- [ ] Add keyboard shortcuts (2 hours)
  - Ctrl+Enter to submit form
  - Escape to close modals
  - Tab navigation improvements

- [ ] Improve loading state animations (1 hour)
  - Smoother transitions
  - Better visual feedback during long operations

#### Medium Effort (3-5 hours each)
- [ ] Add search/filter to results table (4 hours)
  - Filter by resource type
  - Search by title or description
  - Sort by relevance, type, or source

- [ ] Add export options for results (3 hours)
  - Export to CSV
  - Export to Markdown
  - Export to JSON
  - Direct NotebookLM import format

- [ ] Implement "Save Search" feature (5 hours)
  - Save search parameters for later
  - Quick re-run of previous searches
  - Browser localStorage for persistence

#### Larger Projects (6+ hours)
- [ ] Add user dashboard (10 hours)
  - View past searches and results
  - Re-run previous jobs
  - Delete old jobs
  - Usage statistics

- [ ] Implement progressive web app (PWA) features (8 hours)
  - Offline support
  - Install as app
  - Push notifications for job completion

### Documentation & Developer Experience

#### Quick Wins (1-2 hours each)
- [x] Add comprehensive docstrings (✅ Complete)

- [ ] Create backend/README.md with API docs (2 hours)
  - Document all endpoints
  - Include request/response examples
  - Add authentication info when implemented

- [ ] Create web/README.md with frontend docs (1 hour)
  - Component documentation
  - State management overview
  - Build and deployment instructions

#### Medium Effort (3-5 hours each)
- [ ] Generate OpenAPI/Swagger documentation (4 hours)
  - Auto-generate from FastAPI annotations
  - Host interactive API docs
  - Include examples and authentication
  - Document API comprehensively

- [ ] Add architecture diagrams (3 hours)
  - System architecture diagram
  - Data flow diagram
  - Component relationship diagram

- [ ] Create contributing guide (2 hours)
  - Code style guidelines
  - PR template
  - Issue templates
  - Development setup guide

#### Larger Projects (6+ hours)
- [ ] Record video tutorials (8 hours)
  - Getting started guide
  - Deployment walkthrough
  - Feature demonstrations
  - Troubleshooting common issues

### Security & Compliance

#### Quick Wins (1-2 hours each)
- [ ] Add security headers (1 hour)
  - Content-Security-Policy
  - X-Frame-Options
  - X-Content-Type-Options

- [ ] Implement request size limits (1 hour)
  - Limit payload size to prevent abuse
  - Add file upload size limits

#### Medium Effort (3-5 hours each)
- [ ] Add rate limiting middleware (4 hours)
  - Per-IP rate limits
  - Per-user rate limits (when auth added)
  - Configurable limits via environment

- [ ] Implement API key rotation (3 hours)
  - Support multiple API keys
  - Graceful key rotation
  - Key expiration warnings

- [ ] Add request logging and monitoring (5 hours)
  - Log all API requests
  - Track error rates
  - Monitor performance metrics

#### Larger Projects (8+ hours)
- [ ] Implement user authentication (16 hours)
  - User registration and login
  - JWT token management
  - Password reset flow
  - OAuth integration (Google, GitHub)

- [ ] Add role-based access control (8 hours)
  - Admin vs regular user roles
  - Per-resource permissions
  - API key scoping

### Monitoring & Observability

#### Quick Wins (1-2 hours each)
- [x] Add structured logging (✅ Implemented in logging_config.py)

- [ ] Add health check improvements (1 hour)
  - Check database connectivity
  - Check external API availability
  - Return detailed health status

#### Medium Effort (3-5 hours each)
- [ ] Implement application metrics (5 hours)
  - Track job completion rates
  - Monitor API response times
  - Count errors by type
  - Export metrics to Prometheus/Grafana

- [ ] Add error tracking (4 hours)
  - Integrate Sentry or similar
  - Capture unhandled exceptions
  - Track error trends
  - Alert on error rate spikes

#### Larger Projects (6+ hours)
- [ ] Set up comprehensive monitoring dashboard (8 hours)
  - System health dashboard
  - User activity metrics
  - Cost tracking (OpenAI, infrastructure)
  - Performance analytics

---

## Summary of Improvement Effort

**Quick Wins (< 2 hours):** 21 items - Start here for immediate impact
**Medium Effort (2-6 hours):** 24 items - Moderate investment, significant value
**Larger Projects (6+ hours):** 15 items - Strategic improvements, plan carefully

**Total estimated effort:** ~260-310 hours

**Recommended Priority Order:**
1. **Error handling & user feedback** - Better UX for failures, clearer messages
2. **Code formatting & linting** - Standardize style, enforce consistency
3. **Type checking fixes** - Improve code quality and catch bugs early
4. **Basic testing** - Prevent regressions, ensure reliability
5. **API documentation** - Help future developers and API consumers
6. **Markdown parser improvements** - Better accuracy for resource extraction
7. **Performance optimizations** - As needed based on usage patterns
8. **Advanced features** - Based on user feedback and demand

---

## Deployment

See [Deployment_Plan.md](Deployment_Plan.md) for detailed production deployment instructions.

### Quick Deployment Overview

**Backend (Railway):**
- Cost: $5/month
- No request timeouts
- Always-on service
- WebSocket support

**Frontend (Cloudflare Pages):**
- Cost: Free
- Unlimited bandwidth
- Auto-deploy from git

**Database (Supabase):**
- Cost: Free tier / $25/month Pro
- Standalone (not Railway's database)
- Better pricing and tooling

**Total Monthly Cost:** $5-30

---

## Troubleshooting

### Backend Issues

**"SUPABASE_URL and SUPABASE_ANON_KEY must be set"**
- Check `.env.local` exists in project root
- Verify it contains `SUPABASE_URL` and `SUPABASE_ANON_KEY`

**"Module not found" errors**
- Run `pip install -e .`
- Activate virtual environment: `source .venv/bin/activate`

**Database connection errors**
- Verify Supabase project is running
- Check `jobs` table exists
- Verify API keys are correct

**Import errors for ScholarSource**
- Ensure `src/scholar_source/crew.py` exists
- Check Python path includes project root

### Frontend Issues

**"Failed to submit job"**
- Ensure backend is running on port 8000
- Check `curl http://localhost:8000/api/health`

**CORS errors**
- Verify `backend/main.py` includes `http://localhost:5173` in CORS origins
- Check browser console for specific error

**Polling doesn't work**
- Check browser console for errors
- Verify `LoadingStatus` component is polling every 2 seconds

### Common Issues

**Rate limit errors (OpenAI)**
- You hit 30k TPM limit with GPT-4o
- Solution: Use GPT-4o-mini for more agents
- Or: Upgrade to Tier 2 ($5 spent = 450k TPM)

**Crew execution too slow**
- Normal: 1-5 minutes per job
- CrewAI runs 4 sequential agents
- Check status messages for progress

**Results not parsing correctly**
- Check `report.md` file format
- Markdown parser has multiple fallback strategies
- May need to adjust based on actual crew output

---

## Development Workflow

### Daily Development
```bash
# Terminal 1: Backend
source .venv/bin/activate
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd web
npm run dev
```

Both servers auto-reload on file changes.

### Making Changes
1. Edit code
2. Save file
3. Server auto-reloads
4. Refresh browser to see changes

### Git Workflow
```bash
# Check status
git status

# Add files (excluding secrets)
git add .

# Commit
git commit -m "Description of changes"

# Push to remote
git push origin main
```

**Never commit:**
- `.env.local` (root and web/)
- `__pycache__/`
- `node_modules/`
- `report.md`

---

## Quick Reference

### Start Everything
```bash
# Backend
source .venv/bin/activate && uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (new terminal)
cd web && npm run dev
```

### Environment Files
- `.env.example` - Template (commit to git)
- `.env.local` - Secrets (never commit)
- `web/.env.example` - Frontend template
- `web/.env.local` - Frontend config

### Key URLs
- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Supabase: https://supabase.com/dashboard

### File Counts
- Backend: 7 files
- Frontend: 18 files
- Documentation: 5 files
- **Total: 30+ new files created**

---

## Success Criteria

### MVP Complete When:
- [x] Supabase database configured with jobs table
- [x] Jobs persisted to Supabase (survive restarts)
- [ ] Backend API running and tested
- [ ] Frontend running and tested
- [ ] Form accepts inputs and validates
- [ ] API creates background jobs
- [ ] Frontend polls job status
- [ ] Crew executes and generates resources
- [ ] Markdown parsed into structured JSON
- [ ] Results displayed in clean table
- [ ] Copy buttons functional
- [ ] Copy All URLs functional (for NotebookLM)
- [ ] Error states handled gracefully

---

**Last Updated:** December 21, 2024

**Status:** Part 0-2 Complete ✅ | Part 3 In Progress 🔄
