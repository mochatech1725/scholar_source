# ScholarSource

**Find high-quality study resources aligned with your textbook for Google NotebookLM**

ScholarSource is a web application that helps students discover curated educational resources that complement their course textbooks. By analyzing your book's structure and topics, ScholarSource finds open textbooks, course materials, and learning resources you can add to Google NotebookLM to create comprehensive study materials like flashcards and quizzes.

---

## 🎯 Purpose

Students often struggle to find supplementary learning materials that align with their specific textbook. ScholarSource solves this by:

1. **Analyzing your book's structure** - Extracts table of contents, topics, and key concepts from book metadata, PDFs, or course pages
2. **Finding aligned resources** - Searches for 5-7 high-quality, legally accessible resources that follow similar structure to your textbook
3. **Validating quality** - Ensures resources are free, legal, NotebookLM-compatible, and from reputable sources
4. **Presenting actionable results** - Provides a student-friendly guide with direct links ready to import into NotebookLM

**Key Feature:** Prioritizes text-based resources (PDFs, web pages) that NotebookLM processes best, with YouTube videos as supplementary materials.

---

## 🏗️ Architecture

ScholarSource is a full-stack application with a modern, scalable architecture:

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                           │
│                                                                   │
│  React + Vite Frontend (Cloudflare Pages - Free)                │
│  - Course/Book input form (9 optional fields)                    │
│  - Real-time job status polling                                  │
│  - Results table with shareable links                            │
│  - Export to NotebookLM functionality                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ HTTPS API Calls
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                      BACKEND API                                 │
│                                                                   │
│  FastAPI (Railway - $5/month)                                   │
│  - POST /api/submit - Create background jobs                    │
│  - GET /api/status/{job_id} - Poll job status                   │
│  - GET /api/results/{job_id} - Shareable results                │
│  - GET /api/health - Health check                               │
│                                                                   │
│  Background Job Processing:                                      │
│  - Async crew execution in threads (2-5 min runtime)            │
│  - Markdown parsing to structured JSON                           │
│  - No timeouts (critical for long-running AI tasks)             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Database Operations
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                      DATABASE                                    │
│                                                                   │
│  Supabase PostgreSQL (Free tier / $25/mo Pro)                   │
│  - Jobs table (UUID-based, persistent storage)                  │
│  - Job states: pending → running → completed/failed             │
│  - Shareable links that survive server restarts                 │
│  - JSONB fields for flexible data storage                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Crew Execution
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                    AI AGENT SYSTEM                               │
│                                                                   │
│  CrewAI Multi-Agent Framework                                   │
│  - Book Structure Analyst (GPT-4o + FileReadTool)              │
│  - Resource Discovery Agent (GPT-4o-mini + SerperDevTool)       │
│  - Resource Validator (GPT-4o-mini + Web/YouTube tools)         │
│  - Output Formatter (GPT-4o)                                    │
│                                                                   │
│  External APIs:                                                  │
│  - OpenAI API (GPT-4o, GPT-4o-mini)                            │
│  - Serper API (web search)                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Technology Stack

### Frontend
- **React + Vite** - Modern, fast frontend framework
- **Deployment**: Cloudflare Pages (Free tier)
  - Unlimited bandwidth
  - Global CDN
  - Automatic HTTPS

### Backend
- **FastAPI** - Python web framework for REST API
- **Deployment**: Railway ($5/month)
  - **Why Railway?**
    1. ✅ **No request timeouts** - CrewAI jobs run 2-5 minutes without interruption
    2. ✅ **Always-on service** - No cold starts when students are waiting
    3. ✅ **WebSocket support** - Critical for streaming real-time progress updates
    4. ✅ **Simpler than alternatives** - Less complexity than Fly.io, better reliability than Render free tier
  - **Why NOT alternatives?**
    - Render free tier: 30-second timeout (dealbreaker for long AI jobs)
    - Render paid ($7): Works but cold starts hurt UX
    - Fly.io: Unnecessary complexity overhead
    - DigitalOcean: Works but Railway has better integration

### Database
- **Supabase PostgreSQL**
- **Deployment**: **Standalone Supabase** (not Railway's database add-on)
  - Free tier: 500MB database, 50,000 monthly active users
  - Pro tier: $25/month when scaling is needed
  - **Why standalone Supabase?**
    1. ✅ **Better pricing** - Free tier vs Railway's $10+/month database add-on
    2. ✅ **Superior tooling** - Dashboard, SQL Editor, real-time subscriptions
    3. ✅ **Auth ready** - Built-in authentication for future user accounts feature
    4. ✅ **Independent scaling** - Database and backend scale separately
    5. ✅ **Portable** - Easy to switch backend providers without data migration

### AI Agent System
- **CrewAI** - Multi-agent orchestration framework
- **OpenAI API** - GPT-4o and GPT-4o-mini models
- **Serper API** - Web search capabilities
- **CrewAI Tools**:
  - `FileReadTool` - Extract table of contents from PDF textbooks
  - `SerperDevTool` - Search for educational resources
  - `WebsiteSearchTool` - Validate web page quality
  - `YoutubeVideoSearchTool` - Validate YouTube video content

---

## 📦 Installation

### Prerequisites
- Python >=3.10 <3.13
- Node.js >=18 (for frontend)
- [UV](https://docs.astral.sh/uv/) for Python dependency management

### Backend Setup

1. **Install UV** (if not already installed):
```bash
pip install uv
```

2. **Install Python dependencies**:
```bash
crewai install
```

3. **Set up environment variables** (`.env` file):
```bash
# OpenAI API
OPENAI_API_KEY=your_openai_api_key

# Serper API (web search)
SERPER_API_KEY=your_serper_api_key

# Supabase Database
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your_anon_or_service_role_key
```

4. **Create Supabase database table**:

Go to Supabase Dashboard → SQL Editor and run:

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

CREATE POLICY "Enable all access for jobs" ON jobs
    FOR ALL USING (true);
```

### Frontend Setup

1. **Navigate to web directory**:
```bash
cd web
```

2. **Install Node dependencies**:
```bash
npm install
```

3. **Create environment file** (`web/.env.local`):
```bash
VITE_API_URL=http://localhost:8000
```

---

## 🎮 Running the Application

### Development Mode

**Terminal 1 - Start Backend API:**
```bash
# From project root
source .venv/bin/activate
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Start Frontend Dev Server:**
```bash
# From web/ directory
cd web
npm run dev
```

**Access the app:** http://localhost:5173

### CLI Testing (Without Web UI)

Test the CrewAI agents directly from command line:

```bash
# Example 1: By book title and author
python src/scholar_source/main.py \
  --book-title "Introduction to Algorithms" \
  --book-author "Cormen, Leiserson, Rivest, Stein"

# Example 2: By ISBN
python src/scholar_source/main.py --isbn "978-0262046305"

# Example 3: By PDF file
python src/scholar_source/main.py --book-pdf-path "/path/to/textbook.pdf"

# Example 4: By book URL
python src/scholar_source/main.py \
  --book-url "https://mitpress.mit.edu/9780262046305/introduction-to-algorithms/"

# Example 5: By course information (shorthand)
python src/scholar_source/main.py \
  -u "Northwestern University" \
  -c "GEN_ENG 205-2"

# Test with verbose output
python test_crew.py
```

**Available CLI Arguments:**
- `-u, --university-name` - University name (e.g., "MIT")
- `-c, --course-name` - Course name (e.g., "Introduction to Algorithms")
- `-url, --course-url` - Course webpage URL
- `-b, --textbook` - Textbook information (legacy)
- `-t, --topics-list` - Comma-separated topics
- `--book-title` - Book title
- `--book-author` - Book author(s)
- `--isbn` - ISBN of the book
- `--book-pdf-path` - Local path to PDF
- `--book-url` - Online link to book

**Note:** At least one argument must be provided.

---

## 🔧 Configuration

### Agent Configuration

Edit [src/scholar_source/config/agents.yaml](src/scholar_source/config/agents.yaml) to customize:
- Agent roles and goals
- LLM models (GPT-4o, GPT-4o-mini)
- Agent backstories and expertise

### Task Configuration

Edit [src/scholar_source/config/tasks.yaml](src/scholar_source/config/tasks.yaml) to customize:
- Task descriptions and priorities
- Expected outputs
- Resource quality criteria

### Crew Logic

Edit [src/scholar_source/crew.py](src/scholar_source/crew.py) to:
- Add/remove agents
- Configure agent tools
- Change task execution order (sequential/hierarchical)

---

## 📊 How It Works

### 1. User Submits Book Information
Students provide one or more of:
- Book metadata (title, author, ISBN)
- PDF file of the textbook
- Book URL (publisher website, Amazon, etc.)
- Course information (university, course name, URL)

### 2. Background Job Created
- FastAPI creates a job in Supabase database
- Job ID returned to frontend
- CrewAI execution starts in background thread

### 3. AI Agent Workflow (2-5 minutes)

**Agent 1: Book Structure Analyst (GPT-4o)**
- Reads PDF to extract table of contents (if provided)
- Analyzes book metadata to infer topics
- Identifies course level and discipline area
- Outputs: course_title, topics list, key_concepts, course_level

**Agent 2: Resource Discovery Agent (GPT-4o-mini)**
- Searches for 5-7 resources using Serper API
- Prioritizes open textbooks, PDFs, course notes
- Matches resources to book's table of contents
- Ensures legal, free, publicly accessible content

**Agent 3: Resource Validator (GPT-4o-mini)**
- Verifies URLs are functional (no 404s, paywalls)
- Checks NotebookLM compatibility (PDF, YouTube, web page)
- Validates licensing (Creative Commons, Open Access)
- Scores resources on usefulness (1-10)
- Filters out low-quality/illegal resources

**Agent 4: Output Formatter (GPT-4o)**
- Creates student-friendly markdown guide
- Organizes resources by topic/type
- Adds NotebookLM import instructions
- Includes study tips and workflow suggestions

### 4. Results Returned
- Frontend polls `/api/status/{job_id}` every 2 seconds
- When complete, displays results in table
- Student can copy URLs, share results link, or export to NotebookLM

---

## 🌐 API Endpoints

### `POST /api/submit`
Submit a new resource discovery job.

**Request Body:**
```json
{
  "university_name": "MIT",
  "course_name": "Introduction to Algorithms",
  "book_title": "Introduction to Algorithms",
  "book_author": "Cormen, Leiserson, Rivest, Stein",
  "isbn": "978-0262046305",
  "book_pdf_path": "",
  "book_url": "",
  "course_url": "",
  "textbook": "",
  "topics_list": ""
}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Job submitted successfully"
}
```

### `GET /api/status/{job_id}`
Get job status and results (for polling).

**Response (pending/running):**
```json
{
  "job_id": "550e8400-...",
  "status": "running",
  "status_message": "Analyzing book structure...",
  "search_title": "MIT Introduction to Algorithms",
  "created_at": "2025-12-20T10:30:00Z"
}
```

**Response (completed):**
```json
{
  "job_id": "550e8400-...",
  "status": "completed",
  "results": [
    {
      "type": "PDF",
      "title": "MIT 6.006 Course Notes",
      "source": "MIT OpenCourseWare",
      "url": "https://...",
      "description": "Comprehensive lecture notes..."
    }
  ],
  "raw_output": "# Study Resources for Introduction to Algorithms...",
  "created_at": "2025-12-20T10:30:00Z",
  "completed_at": "2025-12-20T10:33:45Z"
}
```

### `GET /api/results/{job_id}`
Get completed job results (for shareable links).

Returns 404 if job doesn't exist or isn't completed yet.

### `GET /api/health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

---

## 🚢 Deployment

### Frontend Deployment (Cloudflare Pages)

1. **Connect GitHub repository** to Cloudflare Pages
2. **Build settings**:
   - Build command: `npm run build`
   - Build output directory: `web/dist`
   - Root directory: `web`
3. **Environment variables**:
   - `VITE_API_URL` = `https://your-backend.railway.app`

### Backend Deployment (Railway)

1. **Connect GitHub repository** to Railway
2. **Add environment variables**:
   - `OPENAI_API_KEY`
   - `SERPER_API_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
3. **Railway auto-detects** FastAPI and runs: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. **Enable persistent storage** if saving files locally (optional)

### Database (Supabase)

Already set up during installation. No additional deployment needed.

**Scaling considerations:**
- Free tier: 500MB database, 50K MAU
- Upgrade to Pro ($25/mo) when hitting limits
- Consider adding indexes for frequently queried fields

---

## 📁 Project Structure

```
/Users/teial/Tutorials/AI/scholar_source/
├── backend/                      # FastAPI backend
│   ├── __init__.py
│   ├── main.py                   # API endpoints
│   ├── models.py                 # Pydantic request/response models
│   ├── database.py               # Supabase client
│   ├── jobs.py                   # Background job management
│   ├── crew_runner.py            # CrewAI integration wrapper
│   └── markdown_parser.py        # Parse crew output to JSON
│
├── web/                          # React/Vite frontend
│   ├── src/
│   │   ├── App.jsx               # Main app with routing
│   │   ├── pages/
│   │   │   ├── HomePage.jsx      # Main form page
│   │   │   └── ResultsPage.jsx   # Shareable results page
│   │   ├── components/
│   │   │   ├── CourseForm.jsx    # Input form
│   │   │   ├── ResultsTable.jsx  # Results display
│   │   │   └── LoadingStatus.jsx # Job status polling
│   │   ├── api/
│   │   │   └── client.js         # API client functions
│   │   └── styles/
│   │       └── App.css           # Styles
│   ├── package.json
│   └── vite.config.js
│
├── src/scholar_source/           # CrewAI implementation
│   ├── crew.py                   # Agent and task definitions
│   ├── main.py                   # CLI entry point
│   └── config/
│       ├── agents.yaml           # Agent configurations
│       └── tasks.yaml            # Task descriptions
│
├── test_crew.py                  # Testing script
├── pyproject.toml                # Python dependencies
├── .env                          # Environment variables
└── README.md                     # This file
```

---

## 🔍 Understanding the Agents

ScholarSource uses a **sequential multi-agent workflow** powered by CrewAI:

### 1. Book Structure Analyst (`course_intelligence_agent`)
- **Role**: Extract table of contents and topics from student's book
- **Tools**: `FileReadTool` (reads PDFs)
- **Model**: GPT-4o (stronger reasoning for structure extraction)
- **Output**: Course title, topics list, key concepts, course level

### 2. Resource Discovery Agent (`resource_discovery_agent`)
- **Role**: Find 5-7 high-quality resources aligned with book structure
- **Tools**: `SerperDevTool` (web search)
- **Model**: GPT-4o-mini (cost-effective for search tasks)
- **Priority**: Open textbooks, PDFs, course notes (text-based for NotebookLM)
- **Output**: List of resources with URLs, descriptions, coverage topics

### 3. Resource Validator (`resource_validator_agent`)
- **Role**: Validate resource quality, legality, and NotebookLM compatibility
- **Tools**: `WebsiteSearchTool`, `YoutubeVideoSearchTool`
- **Model**: GPT-4o-mini (validation is straightforward)
- **Checks**: Accessibility, copyright, format compatibility, usefulness
- **Output**: Filtered list with validation scores (1-10)

### 4. Output Formatter (`output_formatter_agent`)
- **Role**: Create student-friendly markdown guide
- **Tools**: None (pure formatting)
- **Model**: GPT-4o (better at clear, structured writing)
- **Output**: Markdown document with resources organized by topic, import instructions, study tips

---

## 🧪 Testing

### Test CrewAI Locally

```bash
# Run test script with verbose output
python test_crew.py

# Expected: 2-5 minute execution, generates report.md
```

### Test API Locally

```bash
# Terminal 1: Start backend
uvicorn backend.main:app --reload

# Terminal 2: Test endpoints
curl -X POST http://localhost:8000/api/submit \
  -H "Content-Type: application/json" \
  -d '{"book_title": "Introduction to Algorithms", "book_author": "Cormen"}'

# Copy job_id from response, then poll status
curl http://localhost:8000/api/status/{job_id}
```

### Test Frontend Locally

```bash
cd web
npm run dev

# Open http://localhost:5173
# Fill form and submit
# Watch status updates
# Verify results table displays correctly
```

---

## 🛠️ Troubleshooting

### CrewAI Execution Issues

**Problem**: Agents can't find resources
- **Check**: `SERPER_API_KEY` is set in `.env`
- **Check**: SerperDevTool is working (test with `python test_crew.py`)
- **Note**: GPT-4o-mini sometimes struggles with SerperDevTool parameters. Consider upgrading resource_discovery_agent to GPT-4o if issues persist.

**Problem**: FileReadTool can't read PDF
- **Check**: PDF path is absolute, not relative
- **Check**: File exists and is readable
- **Check**: PDF is not encrypted or password-protected

### API Connection Issues

**Problem**: Frontend can't connect to backend
- **Check**: CORS is configured in `backend/main.py` for frontend origin
- **Check**: `VITE_API_URL` in `web/.env.local` matches backend URL
- **Check**: Backend is running on expected port (8000)

**Problem**: 404 on `/api/status/{job_id}`
- **Check**: Job ID is valid UUID
- **Check**: Job exists in Supabase `jobs` table
- **Check**: Database connection is working (check `SUPABASE_URL` and `SUPABASE_KEY`)

### Database Issues

**Problem**: Jobs not persisting
- **Check**: Supabase credentials in `.env`
- **Check**: `jobs` table exists (run SQL schema from Installation section)
- **Check**: Row Level Security policies are set correctly

---

## 📚 Resources

- [CrewAI Documentation](https://docs.crewai.com)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [React Documentation](https://react.dev)
- [Supabase Documentation](https://supabase.com/docs)
- [Railway Documentation](https://docs.railway.app)
- [Cloudflare Pages Documentation](https://developers.cloudflare.com/pages)

---

## 🤝 Support

For questions or issues:
- Check the [troubleshooting section](#-troubleshooting) above
- Review the [CrewAI documentation](https://docs.crewai.com)
- [Join CrewAI Discord](https://discord.com/invite/X4JWnZnxPb)

---

## 📄 License

This project is built with CrewAI. See [CrewAI GitHub](https://github.com/joaomdmoura/crewai) for framework license details.
