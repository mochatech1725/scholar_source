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
- [ ] Test frontend locally

### Part 3: Integration & Testing (Next)
- [ ] Test full workflow (form submission → job polling → results display)
- [ ] Test error handling (network errors, invalid inputs, etc.)
- [ ] Test persistence (jobs survive server restarts)
- [ ] Validate CORS configuration
- [ ] Test copy buttons and "Copy All URLs" functionality

### Part 4: Documentation
- [x] Update README.md with web app setup instructions
- [ ] Create backend/README.md (API documentation)
- [ ] Create web/README.md (frontend documentation)

### Part 5: Deployment (Future)
- [ ] Deploy backend to Railway
- [ ] Deploy frontend to Cloudflare Pages
- [ ] Configure production environment variables
- [ ] Test production deployment

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

#### Advanced Features
- [ ] Direct NotebookLM API integration (auto-import resources)
- [ ] User-specific job history
- [ ] Personal dashboard with past searches

#### Sharing & Collaboration
- [ ] Share results via email

#### Resource Management
- [ ] Job deletion/cleanup (automatic or manual)
- [ ] Job expiration policies (auto-delete after 30/60/90 days)

#### Communication
- [x] **Email notifications when job completes** (✅ Implemented - see Email Notifications section)
- [ ] SMS notifications


### Technical Debt & Improvements
- [ ] Refactor markdown parser for better accuracy
- [ ] Add TypeScript to frontend
- [ ] Add type hints to all Python code
- [ ] Improve error messages and user feedback
- [ ] Add logging throughout backend
- [ ] Create comprehensive test suite
- [ ] Document API with OpenAPI/Swagger
- [ ] Add code comments and docstrings
- [ ] Set up pre-commit hooks (linting, formatting)
- [ ] Standardize code formatting (Black, Prettier)

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
