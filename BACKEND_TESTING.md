# Backend Testing Guide

## Part 1 Implementation Complete ✅

All backend files have been created. Before testing, you need to install the new dependencies.

## Installation

Install the new FastAPI dependencies:

```bash
cd /Users/teial/Tutorials/AI/scholar_source
source .venv/bin/activate
pip install -e .
```

This will install:
- `fastapi>=0.115.0` - Web framework
- `uvicorn[standard]>=0.30.0` - ASGI server
- `python-multipart>=0.0.9` - Form parsing
- `pydantic>=2.0.0` - Data validation
- `supabase>=2.0.0` - Database client
- `python-dotenv>=1.0.0` - Environment variables

## Running the Backend

Start the FastAPI development server:

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs (interactive Swagger UI)
- **Health**: http://localhost:8000/api/health

## Testing the API

### 1. Health Check

```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "database": "connected"
}
```

### 2. Submit a Job

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

Expected response:
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "pending",
  "message": "Job created successfully. Use job_id to poll for status."
}
```

**Save the `job_id`** for the next steps!

### 3. Check Job Status

Replace `<job_id>` with the ID from step 2:

```bash
curl http://localhost:8000/api/status/<job_id>
```

Expected statuses:
- `pending` - Job created, waiting to start
- `running` - CrewAI is executing
- `completed` - Job finished successfully (check `results` field)
- `failed` - Job encountered an error (check `error` field)

### 4. Get Shareable Results

Once job is `completed`:

```bash
curl http://localhost:8000/api/results/<job_id>
```

This endpoint is used for shareable links and only returns completed jobs.

## Interactive API Documentation

Visit http://localhost:8000/docs to:
- View all endpoints with descriptions
- Test endpoints directly in the browser
- See request/response schemas

## Files Created

### Backend Structure
```
backend/
├── __init__.py              ✅ Package marker
├── database.py              ✅ Supabase client initialization
├── models.py                ✅ Pydantic request/response models
├── jobs.py                  ✅ Job CRUD operations (Supabase)
├── crew_runner.py           ✅ Background CrewAI execution
├── markdown_parser.py       ✅ Parse crew output to JSON
└── main.py                  ✅ FastAPI app with 4 endpoints
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information |
| GET | `/api/health` | Health check |
| POST | `/api/submit` | Submit new job |
| GET | `/api/status/{job_id}` | Get job status |
| GET | `/api/results/{job_id}` | Get completed job results (shareable) |

## Troubleshooting

### "SUPABASE_URL and SUPABASE_ANON_KEY must be set"

Check your `.env` file contains:
```bash
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=eyJ...your_key_here
```

### "Module not found" errors

Make sure you installed the dependencies:
```bash
pip install -e .
```

### Database connection errors

Verify your Supabase project is running and the `jobs` table exists (run `supabase_schema.sql` in SQL Editor).

### Import errors for ScholarSource

The `crew_runner.py` adds `src/` to the Python path to import the ScholarSource crew. Make sure `src/scholar_source/crew.py` exists.

## Next Steps

After testing the backend successfully:
1. Mark "Test backend API locally" as complete in [Future_plans.md](Future_plans.md)
2. Move to Part 2: Frontend (React/Vite) Implementation
