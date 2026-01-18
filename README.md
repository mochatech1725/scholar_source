# ScholarSource

**Find high-quality study resources aligned with your textbook for Google NotebookLM**

ScholarSource is a web application that helps students discover curated educational resources that complement their course textbooks. By analyzing your book's structure and topics, ScholarSource finds open textbooks, course materials, and learning resources you can add to Google NotebookLM to create comprehensive study materials.

---

## Purpose

Students often struggle to find supplementary learning materials that align with their specific textbook. ScholarSource automates this process by:

1. **Analyzing textbook structure** - Extracts topics, concepts, and organization from course materials or book metadata
2. **Discovering aligned resources** - Searches for 5-7 high-quality, legally accessible resources that match the textbook's content structure
3. **Validating quality** - Ensures resources are free, legal, NotebookLM-compatible, and from reputable sources
4. **Presenting actionable results** - Provides resources ready to import into Google NotebookLM

---

## Project Structure

```
scholar_source/
├── backend/                 # FastAPI backend API
│   ├── main.py             # API endpoints
│   ├── models.py           # Pydantic request/response models
│   ├── jobs.py             # Job management
│   ├── crew_runner.py      # CrewAI execution wrapper
│   ├── cache.py            # Caching system
│   ├── rate_limiter.py     # Rate limiting
│   └── markdown_parser.py  # Parse crew output to JSON
│
├── web/                    # React + Vite frontend
│   ├── src/
│   │   ├── pages/
│   │   │   └── HomePage.jsx
│   │   ├── components/
│   │   │   └── ResultsTable.jsx
│   │   └── api/
│   │       └── client.js
│   └── package.json
│
├── src/scholar_source/     # CrewAI multi-agent system
│   ├── crew.py            # Agent and task definitions
│   └── config/
│       ├── agents.yaml     # Agent configurations
│       └── tasks.yaml      # Task descriptions
│
├── tests/                  # Test suite
├── docs/                   # Documentation
│   ├── scholar_source_SDD.md
│   └── scholar_source_TDD.md
└── supabase_schema.sql     # Database schema
```

---

## Security Features

ScholarSource implements enterprise-grade security measures:

- **🔐 Authentication Required** - All API endpoints require valid Supabase JWT tokens
- **🛡️ Input Validation** - Comprehensive validation and sanitization of all user inputs
- **🚫 Prompt Injection Protection** - Multi-layer detection of malicious prompt patterns
- **🔒 Row-Level Security (RLS)** - Users can only access their own jobs and data
- **✉️ XSS Prevention** - HTML escaping in email notifications
- **📦 Dependency Pinning** - All dependencies pinned to specific versions
- **⚡ Rate Limiting** - Protection against abuse and DoS attacks

---

## Installation

### Prerequisites

- **Python** >=3.10 <3.13
- **Node.js** >=18 and npm
- **Supabase** account (free tier available)

### Backend Setup

1. **Create and activate a Python virtual environment** (recommended):
   ```bash
   # Create virtual environment
   python3 -m venv .venv

   # Activate virtual environment
   # On macOS/Linux:
   source .venv/bin/activate
   # On Windows:
   # .venv\Scripts\activate
   ```

2. **Install Python dependencies:**
   ```bash
   # Make sure virtual environment is activated
   # Upgrade pip to latest version
   pip install --upgrade pip

   # Install all backend dependencies from requirements.txt
   pip install -r requirements.txt
   ```

   **Backend dependencies installed:**
   - `crewai[tools]>=0.120.1` - Multi-agent orchestration framework with tools
   - `fastapi>=0.115.0` - Modern web framework for building APIs
   - `uvicorn[standard]>=0.30.0` - ASGI server for running FastAPI
   - `supabase>=2.0.0` - Supabase Python client for database operations
   - `pydantic[email]>=2.0.0` - Data validation using Python type annotations
   - `slowapi>=0.1.9` - Rate limiting middleware for FastAPI
   - `python-multipart>=0.0.9` - Support for form data parsing
   - `python-dotenv>=1.0.0` - Load environment variables from .env file
   - `resend>=0.8.0` - Email service integration
   - `lancedb<0.26` - Vector database (used by CrewAI)

   **Verify installation:**
   ```bash
   # Check that key packages are installed
   python -c "import fastapi, crewai, supabase; print('✅ All dependencies installed')"
   ```

3. **Set up environment variables**:

   Copy the example file and fill in your credentials:
   ```bash
   cp .env.example .env
   ```

   **Required variables:**
   ```bash
   # OpenAI API (required)
   OPENAI_API_KEY=your_openai_api_key_here

   # Serper API (required for web search)
   SERPER_API_KEY=your_serper_api_key_here

   # Supabase Database (required)
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_ANON_KEY=your_supabase_anon_key_here

   # Supabase JWT Secret (required for authentication)
   # Get from: Supabase Dashboard > Settings > API > JWT Secret
   SUPABASE_JWT_SECRET=your_supabase_jwt_secret_here

   # Optional: Cache TTL configuration
   COURSE_ANALYSIS_TTL_DAYS=30
   RESOURCE_RESULTS_TTL_DAYS=7

   # Optional: Redis for multi-instance rate limiting
   REDIS_URL=redis://...  # Only needed if scaling to 2+ instances

   # Optional: CORS allowed origins (comma-separated)
   ALLOWED_ORIGINS=http://localhost:5173,https://your-frontend-domain.com
   ```

   **Getting your Supabase credentials:**
   1. Go to [Supabase Dashboard](https://app.supabase.com)
   2. Select your project
   3. Go to **Settings > API**
   4. Copy:
      - **Project URL** → `SUPABASE_URL`
      - **anon/public key** → `SUPABASE_ANON_KEY`
      - **JWT Secret** → `SUPABASE_JWT_SECRET` (scroll down to find it)

4. **Set up Supabase database:**
   - Create a new Supabase project at https://supabase.com
   - Run the SQL schema from `supabase_schema.sql` in the Supabase SQL Editor
   - This creates the `jobs` and `course_cache` tables

### Frontend Setup

1. **Navigate to web directory:**
   ```bash
   cd web
   ```

2. **Install Node dependencies:**
   ```bash
   # Install all frontend dependencies from package.json
   npm install
   ```

   **Frontend dependencies installed:**

   **Production dependencies:**
   - `react^19.2.0` - UI framework for building user interfaces
   - `react-dom^19.2.0` - React DOM bindings for rendering

   **Development dependencies:**
   - `vite^7.2.4` - Fast build tool and dev server
   - `@vitejs/plugin-react^5.1.1` - Vite plugin for React
   - `tailwindcss^3.4.19` - Utility-first CSS framework
   - `postcss^8.5.6` - CSS post-processor
   - `autoprefixer^10.4.23` - CSS vendor prefixing
   - `vitest^1.0.0` - Fast unit test framework
   - `@testing-library/react^16.3.1` - React component testing utilities
   - `@testing-library/jest-dom^6.1.0` - Custom Jest matchers for DOM
   - `@testing-library/user-event^14.5.0` - User interaction simulation
   - `msw^2.0.0` - API mocking library for tests
   - `eslint^9.39.1` - JavaScript linter
   - `jsdom^23.0.0` - DOM implementation for Node.js (testing)

   **Verify installation:**
   ```bash
   # Check that key packages are installed
   npm list react vite tailwindcss
   ```

3. **Create environment file**:

   Copy the example file and fill in your credentials:
   ```bash
   cp .env.example .env.local
   ```

   **Required variables** (`web/.env.local`):
   ```bash
   # Backend API URL
   VITE_API_URL=http://localhost:8000

   # Supabase credentials (same as backend)
   VITE_SUPABASE_URL=https://your-project-id.supabase.co
   VITE_SUPABASE_ANON_KEY=your_supabase_anon_key_here
   ```

   **Note:** These must match your backend Supabase credentials for authentication to work.

---

## Authentication Setup

ScholarSource requires user authentication for all operations. Users must sign up and log in before submitting jobs.

### First-Time Setup

1. **Start both backend and frontend** (see "Running the Application" below)

2. **Create your first user account:**
   - Open http://localhost:5173 in your browser
   - You'll see the login/signup page
   - Click **Sign Up** tab
   - Enter your email and password
   - Check your email for the confirmation link (if email confirmation is enabled in Supabase)
   - Log in with your credentials

3. **Verify authentication is working:**
   - After logging in, you should see the course input form
   - Submit a test job to ensure everything works
   - Your jobs are private and only visible to you

### Managing Users

**Creating test users for development:**
```bash
# Option 1: Via the web UI (recommended)
# Just use the signup form at http://localhost:5173

# Option 2: Via Supabase Dashboard
# Go to Authentication > Users > Add User
```

**Disabling email confirmation for local development:**
1. Go to **Supabase Dashboard > Authentication > Providers > Email**
2. Toggle off "Confirm email"
3. Users can sign up without email verification

**Resetting passwords:**
- Users can use the "Forgot Password" link (if implemented)
- Or reset via **Supabase Dashboard > Authentication > Users > [User] > Reset Password**

### Security Best Practices

- **Never share JWT secrets** - Keep `SUPABASE_JWT_SECRET` private
- **Use strong passwords** - Supabase enforces minimum password requirements
- **Enable email confirmation in production** - Prevents fake accounts
- **Monitor authentication logs** - Check Supabase Dashboard > Authentication > Logs
- **Rotate API keys regularly** - Especially if compromised

---

## Running the Application

### Development Mode

#### Option 1: With Redis (Recommended for Production-like Setup)

**Terminal 1 - Start Backend:**
```bash
# From project root
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: http://localhost:8000

**Terminal 2 - Start Celery Worker:**
```bash
# From project root
./scripts/start_worker.sh

# Or manually:
celery -A backend.celery_app worker --loglevel=info --queues=crew_jobs,default --concurrency=2
```

The worker processes jobs from the task queue. **Required** for job execution.

**Terminal 3 - Start Frontend:**
```bash
# From web/ directory
cd web
npm run dev
```

Frontend will be available at: http://localhost:5173

#### Option 2: Without Redis (Simpler Local Development)

If you don't want to run Redis locally, you can use **synchronous mode** where tasks run in-process:

**Set environment variables:**
```bash
export SYNC_MODE=true
export ALLOW_IN_MEMORY_RATE_LIMIT=true  # For rate limiting without Redis
```

**Terminal 1 - Start Backend:**
```bash
# From project root
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Start Frontend:**
```bash
# From web/ directory
cd web
npm run dev
```

**Note:** In sync mode, the API will block during task execution (not suitable for production). For production, use Redis with Celery workers.

**Alternative:** Use a free cloud Redis service instead:
- **Upstash Redis** (free: 10K commands/day) - https://upstash.com/
- **Redis Cloud** (free: 30MB) - https://redis.com/try-free/
- **Railway Redis** (if using Railway)

Just set `REDIS_URL` and remove `SYNC_MODE`.

### Verify Installation

**Check backend health:**
```bash
curl http://localhost:8000/api/health
```

Should return:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "database": "skipped"
}
```

**Check frontend:**
Open http://localhost:5173 in your browser - you should see the course input form.

---

## Required API Keys

### OpenAI API Key
- **Purpose:** LLM inference for AI agents (GPT-4o, GPT-4o-mini)
- **Get it:** https://platform.openai.com/api-keys
- **Cost:** Pay-per-use (GPT-4o is expensive, GPT-4o-mini is cheaper)
- **Required:** Yes

### Serper API Key
- **Purpose:** Web search for resource discovery
- **Get it:** https://serper.dev/api-key
- **Cost:** Pay-per-use (cheaper than Google Custom Search)
- **Required:** Yes

### Supabase Credentials
- **Purpose:** PostgreSQL database for job persistence and caching
- **Get it:** Create project at https://supabase.com
- **Cost:** Free tier available (500MB database, 50K MAU)
- **Required:** Yes
- **What you need:**
  - `SUPABASE_URL`: Project URL (e.g., `https://xxxxx.supabase.co`)
  - `SUPABASE_KEY`: Anon key from project settings

---

## Environment Variables Reference

### Backend (.env)

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `OPENAI_API_KEY` | ✅ Yes | OpenAI API key for LLM inference | - |
| `SERPER_API_KEY` | ✅ Yes | Serper API key for web search | - |
| `SUPABASE_URL` | ✅ Yes | Supabase project URL | - |
| `SUPABASE_ANON_KEY` | ✅ Yes | Supabase anon/public key | - |
| `SUPABASE_JWT_SECRET` | ✅ Yes | Supabase JWT secret for token verification | - |
| `REDIS_URL` | Conditional | Redis connection for task queue & rate limiting | `redis://localhost:6379/0` |
| `SYNC_MODE` | No | Set to `true` to run without Redis (tasks run synchronously) | `false` |
| `ALLOW_IN_MEMORY_RATE_LIMIT` | No | Set to `true` for in-memory rate limiting (no Redis needed) | `false` |
| `COURSE_ANALYSIS_TTL_DAYS` | No | Cache TTL for course analysis (days) | 30 |
| `RESOURCE_RESULTS_TTL_DAYS` | No | Cache TTL for full results (days) | 7 |
| `ALLOWED_ORIGINS` | No | CORS allowed origins (comma-separated) | - |
| `RESEND_API_KEY` | No | Email notification service API key | - |
| `RESEND_FROM_EMAIL` | No | From email address for notifications | - |

### Frontend (web/.env.local)

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `VITE_API_URL` | ✅ Yes | Backend API URL | - |
| `VITE_SUPABASE_URL` | ✅ Yes | Supabase project URL (same as backend) | - |
| `VITE_SUPABASE_ANON_KEY` | ✅ Yes | Supabase anon key (same as backend) | - |

**Note:** 
- `REDIS_URL` is required for production deployments. Get a free Redis instance from [Redis Cloud](https://redis.com/try-free/) or [Upstash](https://upstash.com/).
- For local development without Redis, set `SYNC_MODE=true` and `ALLOW_IN_MEMORY_RATE_LIMIT=true`. This runs tasks synchronously in-process (not suitable for production).

---

## How It Works

1. **User submits course/book information** via the web form
2. **Backend creates a background job** and returns a job ID
3. **CrewAI multi-agent system executes** (2-5 minutes):
   - Analyzes textbook structure
   - Discovers aligned resources
   - Validates resource quality
   - Formats results
4. **Frontend polls for status** every 2 seconds
5. **Results displayed** when complete, ready to import into NotebookLM

---

## Deployment

### Deployment Choices

ScholarSource is designed to be deployed on the following platforms:

- **Frontend**: **Cloudflare Pages** (Free tier)
  - Unlimited bandwidth
  - Global CDN
  - Automatic HTTPS
  - Easy GitHub integration

- **Backend**: **Railway** (~$5/month)
  - No request timeouts (critical for long-running AI jobs)
  - Always-on service (no cold starts)
  - Simple deployment process
  - Automatic HTTPS

- **Database**: **Supabase PostgreSQL** (Free tier / $25/month Pro)
  - Free tier: 500MB database, 50K monthly active users
  - Better tooling than Railway's database add-on
  - Built-in authentication ready for future features

### Preparing for Railway Deployment

**Important:** Railway requires a `requirements.txt` file for Python dependencies, but this project uses `pyproject.toml` for dependency management.

**Convert pyproject.toml to requirements.txt:**

```bash
# Option 1: Using pip-tools (recommended)
pip install pip-tools
pip-compile pyproject.toml -o requirements.txt

# Option 2: Using pip directly
pip install -e .
pip freeze > requirements.txt

# Option 3: Manual conversion
# Extract dependencies from pyproject.toml and create requirements.txt
# The requirements.txt file is already included in the repository
```

**Note:** The `requirements.txt` file is already included in this repository and kept in sync with `pyproject.toml`. If you modify dependencies in `pyproject.toml`, regenerate `requirements.txt` before deploying to Railway.

**Railway Deployment Steps:**

1. **Create Procfile** (already included in repository):
   ```
   web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
   ```

2. **Connect GitHub repository** to Railway

3. **Set environment variables** in Railway dashboard:
   - `OPENAI_API_KEY`
   - `SERPER_API_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_KEY` (or `SUPABASE_ANON_KEY`)
   - `ALLOWED_ORIGINS` (your frontend URL)

4. **Railway auto-detects** Python and installs from `requirements.txt`

**Cloudflare Pages Deployment Steps:**

1. **Connect GitHub repository** to Cloudflare Pages

2. **Build settings:**
   - Build command: `npm run build`
   - Build output directory: `web/dist`
   - Root directory: `web`

3. **Environment variables:**
   - `VITE_API_URL` = Your Railway backend URL

For detailed deployment instructions, see `docs/Deployment_Plan.md`.

---

## Documentation


- **System Design Document:** `docs/scholar_source_SDD.md` - High-level architecture and design rationale
- **Technical Design Document:** `docs/scholar_source_TDD.md` - Detailed implementation specifications
- **Testing Guide:** `docs/TESTING_GUIDE.md` - Testing documentation
- **Deployment Plan:** `docs/Deployment_Plan.md` - Step-by-step deployment guide

---

## License

This project is built with CrewAI. See [CrewAI GitHub](https://github.com/joaomdmoura/crewai) for framework license details.
