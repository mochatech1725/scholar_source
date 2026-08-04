# ScholarSource Backend API Reference

Internal reference for the FastAPI backend. Read this before modifying routes, auth, or job handling.

---

## Routes

| Method | Path | Auth | Rate Limit | Purpose |
| --- | --- | --- | --- | --- |
| GET | `/` | None | — | API info |
| GET | `/api/health` | None | — | Health check (db check skipped on startup) |
| GET | `/api/health/workers` | None | — | Celery worker availability |
| POST | `/api/submit` | JWT | 10/hour, 2/min | Submit a job |
| GET | `/api/status/{job_id}` | JWT | 100/min | Poll job status |
| POST | `/api/cancel/{job_id}` | JWT | 20/hour | Cancel a job |

All protected routes use the `get_current_user` FastAPI dependency (`backend/auth.py`).

---

## Authentication

**Dual-mode JWT verification** (`backend/auth.py`):

- `HS256` tokens — verified with `SUPABASE_JWT_SECRET` directly (legacy projects)
- `ES256` / `RS256` tokens — verified via JWKS at `{SUPABASE_URL}/auth/v1/.well-known/jwks.json` (current projects)

The algorithm is detected from the token header; no config required.

`get_current_user` returns:

```python
{
    "id": str,           # user UUID (sub claim)
    "email": str | None,
    "payload": dict,     # full decoded JWT payload
    "access_token": str  # raw token, threaded through to Supabase for RLS
}
```

Auth errors return `{"error": "..."}` with status 401 via a registered exception handler — not FastAPI's default 422 shape.

---

## Job Lifecycle

```
pending → queued → running → completed
                           → failed
                           → cancelled
```

- `pending` — created in DB, not yet picked up
- `queued` — handed to Celery (`crew_jobs` queue); `metadata.celery_task_id` is set
- `running` — worker has started execution
- `completed` / `failed` / `cancelled` — terminal; `completed_at` is set

**SYNC_MODE** (`SYNC_MODE=true`): the job runs inline inside a FastAPI `BackgroundTask` — no Celery, no Redis. The `queued` state is skipped; job goes `pending → running → completed/failed`. Used for local dev.

If a job is stuck in `queued` for more than 30 seconds, `GET /api/status` checks worker availability and adds a warning message to the response.

---

## Supabase Client Modes

`get_supabase_client()` in `backend/database.py` has two modes:

- `access_token=<token>` — authenticates as the user; Supabase RLS applies. Used in API route handlers.
- `use_service_role=True` — bypasses RLS using the service role key. Used in background tasks (Celery workers) that run outside the request context.

Never use `use_service_role=True` in a route handler — it bypasses row-level security.

---

## CORS and CSRF

Both systems share a single source of truth: `backend/origins.py`.

`allowed_origins` contains production origins always, plus dev origins when `ENVIRONMENT != "production"`. Add extra origins via `EXTRA_ALLOWED_ORIGINS` (comma-separated env var).

**CSRF protection** (`backend/csrf_protection.py`): validates the `Origin` header on every POST/PUT/DELETE. Requests without a matching `Origin` get 403. GET/OPTIONS/HEAD are skipped (safe methods). This runs in addition to CORS, not instead of it.

---

## Input Validation

`CourseInputRequest` (`backend/models.py`) validates all fields before any processing:

- Empty strings are coerced to `None` at the model level
- `course_url` and `book_url` must be `http://` or `https://` — no other schemes accepted
- All text fields are checked for prompt injection patterns and control characters
- `topics_list` allows up to 1000 characters; other text fields 200
- `excluded_sites` / `targeted_sites` must be comma-separated valid domain names (no IPs, no localhost)
- `isbn` must be a valid ISBN-10 or ISBN-13 format
- Unknown fields are rejected with 422

At least one of the following groups must be present or the request is rejected with 400:
- Course info: `course_name`, `university_name`, `course_url`, or `topics_list`
- Book identity: `textbook`, `book_title`, `book_author`, or `isbn`
- Book link: `book_url`

---

## Error Response Shapes

Most errors:

```json
{"error": "Short label", "message": "Human-readable detail"}
```

Auth errors (401):

```json
{"error": "Authentication failed"}
```

Rate limit errors (429): handled by SlowAPI, not the standard shape.

---

## Key Environment Switches

| Variable | Effect |
| --- | --- |
| `SYNC_MODE=true` | Run crew inline, skip Celery/Redis |
| `ENVIRONMENT=production` | Strip dev origins from CORS/CSRF allowlist |
| `EXTRA_ALLOWED_ORIGINS` | Comma-separated origins appended to allowlist |
| `ALLOW_IN_MEMORY_RATE_LIMIT=true` | Use in-memory rate limiter (no Redis needed) |
| `LOG_LEVEL` | Controls log verbosity (`INFO`, `DEBUG`, etc.) |

`env_loader.py` loads `.env.{ENVIRONMENT}` first (e.g. `.env.local`), then `.env` as fallback, both with `override=False` — so the environment-specific file wins.
