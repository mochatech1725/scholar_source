# Supabase Local RAG Setup

This guide describes the recommended local database setup for ScholarSource v2
RAG work.

Use the Supabase local development stack instead of a plain Postgres container.
The backend and frontend use Supabase clients, which talk to Supabase HTTP APIs,
not directly to a `postgres://` connection string. Running Supabase locally gives
the project a local Postgres database, pgvector, Auth, PostgREST, Studio, and
local API keys without touching the hosted dev or prod projects.

## Goal

Use a disposable local Supabase instance for RAG source collection, extraction,
chunk storage, embedding metadata, retrieval experiments, and run logs.

This protects the hosted dev database while the RAG pipeline is still changing.

## What This Setup Gives You

- Local Supabase API URL for `supabase-py` and `supabase-js`.
- Local Postgres with `pgvector`.
- Local Auth and JWT signing keys.
- Local Supabase Studio.
- A resettable database loaded from the ScholarSource schema.
- A safe place to write RAG rows without tainting hosted dev or prod.

## Important Constraint

Do not point `SUPABASE_URL` at a raw Postgres URL.

This will not work:

```env
SUPABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres
```

The Supabase clients expect an HTTP API URL like this:

```env
SUPABASE_URL=http://127.0.0.1:54321
```

The direct Postgres URL is still useful for `psql`, database inspection, and
one-off SQL commands, but not for `create_client(...)`.

## Prerequisites

Install and start a Docker-compatible runtime first.

On macOS, Docker Desktop is the most common option:

```bash
open -a Docker
docker version
```

If you prefer OrbStack or Colima, make sure the `docker` CLI works before
continuing:

```bash
docker ps
```

Install the Supabase CLI.

Recommended on macOS:

```bash
brew install supabase/tap/supabase
supabase --version
```

Alternative if you do not want a global CLI and you have Node.js 20 or newer:

```bash
npx supabase --version
```

If you use `npx`, replace each `supabase ...` command below with
`npx supabase ...`.

## One-Time Project Initialization

Run these commands from the repository root:

```bash
cd /Users/teial/Tutorials/AI/scholar_source
supabase init
```

This creates a local `supabase/` directory. It is safe to commit this directory
once the project decides to standardize on Supabase CLI migrations.

Check the generated files:

```bash
find supabase -maxdepth 2 -type f | sort
```

## Add the ScholarSource Schema as a Local Migration

Supabase CLI applies migrations from `supabase/migrations/`. The current repo
keeps the complete fresh-database schema at the project root in
`supabase_schema.sql`, so copy it into the CLI migration directory for local
RAG work.

Run:

```bash
mkdir -p supabase/migrations
cp supabase_schema.sql supabase/migrations/20260707000000_scholar_source_bootstrap.sql
```

Why use the full bootstrap schema here:

- Local RAG work needs a fresh database with `jobs`, RAG tables, indexes, RLS,
  and extensions.
- `migrations/001_create_rag_traceability_schema.sql` is an incremental
  migration for an existing database that already has `jobs`.
- A local clean database should start from `supabase_schema.sql`.

If the root schema changes later, refresh the local bootstrap migration:

```bash
cp supabase_schema.sql supabase/migrations/20260707000000_scholar_source_bootstrap.sql
supabase db reset
```

## Start Local Supabase

Start the local stack:

```bash
supabase start
```

The first start can take several minutes because Docker images are downloaded.
When it finishes, Supabase prints local service URLs and keys.

Check status any time:

```bash
supabase status
```

The important values are:

```text
API URL:     http://127.0.0.1:54321
DB URL:      postgresql://postgres:postgres@127.0.0.1:54322/postgres
Studio URL:  http://127.0.0.1:54323
JWT secret:  <local JWT secret>
anon key or publishable key: <local browser-safe key>
service_role key: <local service role key>
```

You can also print env-style values:

```bash
supabase status -o env
```

## Reset the Local Database

Use this whenever you want a clean local RAG database:

```bash
supabase db reset
```

This recreates the local database, applies `supabase/migrations/*`, and discards
local data.

Do not use `--linked` for local RAG experiments:

```bash
# Do not run this for local RAG work.
supabase db reset --linked
```

`--linked` targets a hosted project after `supabase link`, which defeats the
purpose of protecting hosted dev and prod.

## Optional: Use a Hosted Dev Project Instead

The recommended RAG sandbox is the local Supabase stack above. If you choose to
use a hosted Supabase dev project instead, treat that project as disposable.
`supabase db reset --linked` is destructive against the linked hosted project.

Use this path only when all of these are true:

- The hosted project is a dev/test project, not production.
- The data can be wiped.
- `.env.local` and `web/.env.local` are intended to point at the same hosted
  dev project.
- You have confirmed the linked project ref before running destructive
  commands.

### Choose the Supabase Project Ref

Open the Supabase Dashboard and choose the dev project for this repo. If you do
not already have one, create a new project with a clear name such as
`scholar-source-dev`.

When the project is open, the browser URL looks like this:

```text
https://supabase.com/dashboard/project/abcdefghijklmnopqrst
```

The final path segment is the project ref:

```text
abcdefghijklmnopqrst
```

This is the value to use anywhere this guide says `YOUR_DEV_PROJECT_REF`.

Do not use an organization ID, database ID, API key, JWT secret, or connection
string in place of the project ref.

### Log In to Supabase CLI

The CLI must be authenticated before it can list or link hosted projects:

```bash
supabase login
```

If `supabase projects list` previously failed with an access-token error, that
is expected before login:

```text
Access token not provided. Supply an access token by running `supabase login`
or setting the SUPABASE_ACCESS_TOKEN environment variable.
```

After login, verify that the CLI can see your projects:

```bash
supabase projects list
```

Find the row for the dev project and confirm its project ref matches the final
segment of the dashboard URL.

### Link This Repo to the Hosted Dev Project

From the repository root:

```bash
cd /Users/teial/Tutorials/AI/scholar_source
supabase link --project-ref YOUR_DEV_PROJECT_REF
```

The CLI may prompt for the hosted database password. Use the database password
for that Supabase project.

After linking, verify the local link metadata:

```bash
cat supabase/.temp/project-ref
```

Expected output:

```text
YOUR_DEV_PROJECT_REF
```

If `supabase/.temp/project-ref` does not exist, the repo is not linked yet.
Run `supabase link --project-ref YOUR_DEV_PROJECT_REF` again from the repo
root.

### Point App Env Files at the Same Hosted Dev Project

The CLI link controls Supabase CLI commands. The app still uses env files at
runtime.

Root `.env.local` should point the backend at the hosted dev project:

```env
ENVIRONMENT=local
SUPABASE_URL=https://YOUR_DEV_PROJECT_REF.supabase.co
SUPABASE_ANON_KEY=<dev project anon key>
SUPABASE_SERVICE_ROLE_KEY=<dev project service_role key>
SUPABASE_JWT_SECRET=<dev project JWT secret>
DATABASE_URL=postgresql://postgres:<database password>@db.YOUR_DEV_PROJECT_REF.supabase.co:5432/postgres
```

Frontend `web/.env.local` should point the browser app at the same hosted dev
project:

```env
VITE_SUPABASE_URL=https://YOUR_DEV_PROJECT_REF.supabase.co
VITE_SUPABASE_ANON_KEY=<dev project anon key>
```

Get these values from the Supabase Dashboard:

- Project URL and anon key: project **Settings > API**.
- Service role key: project **Settings > API**. Keep this server-side only.
- JWT secret: project **Settings > API > JWT Settings**.
- Database connection string: project **Settings > Database**.

Do not put `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, or
`DATABASE_URL` in `web/.env.local`. Anything prefixed with `VITE_` is exposed to
the browser.

### Verify Everything Targets the Same Dev Project

Before running a reset, check all three places:

```bash
cat supabase/.temp/project-ref
grep -E '^(SUPABASE_URL|DATABASE_URL)=' .env.local
grep -E '^VITE_SUPABASE_URL=' web/.env.local
```

All three should contain the same project ref:

```text
YOUR_DEV_PROJECT_REF
```

If they do not match, stop and fix the mismatch before running any linked
database command.

### Reset the Hosted Dev Database

Only run this after verifying the linked project is the disposable dev project:

```bash
supabase db reset --linked
```

This resets the hosted linked database and reapplies Supabase CLI migrations
from `supabase/migrations/`. It does not reset the local Docker database.

For a non-destructive migration apply, use:

```bash
supabase db push
```

For the local Docker database, use:

```bash
supabase db reset
```

## Configure the Backend for Local Supabase

The backend loader reads `.env.local` when `ENVIRONMENT=local`. Existing shell
variables still win, so clear any hosted Supabase variables in your terminal if
you exported them manually.

Create or update `.env.local`:

```bash
test -f .env.local || cp .env.example .env.local
```

Then edit these values in `.env.local` using the output from
`supabase status`:

```env
ENVIRONMENT=local
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_ANON_KEY=<paste local anon or publishable key>
SUPABASE_SERVICE_ROLE_KEY=<paste local service_role key>
SUPABASE_JWT_SECRET=<paste local JWT secret>
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres
REDIS_URL=redis://localhost:6379/0
SYNC_MODE=true
ALLOW_IN_MEMORY_RATE_LIMIT=true
CELERY_BROKER_USE_SSL=false
LANGSMITH_TRACING=false
```

Keep provider keys only if you intentionally want local runs to call external
services:

```env
OPENAI_API_KEY=<your key if needed>
SERPER_API_KEY=<your key if needed>
LANGSMITH_API_KEY=
```

Before starting the backend, confirm your terminal is not overriding the file:

```bash
env | grep -E '^(ENVIRONMENT|SUPABASE_|DATABASE_URL)='
```

If hosted values appear, unset them for this terminal session:

```bash
unset SUPABASE_URL
unset SUPABASE_ANON_KEY
unset SUPABASE_SERVICE_ROLE_KEY
unset SUPABASE_JWT_SECRET
unset DATABASE_URL
export ENVIRONMENT=local
```

Start the backend:

```bash
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Check health:

```bash
curl http://localhost:8000/api/health
```

## Configure the Frontend for Local Supabase

Create or update the frontend local env file:

```bash
cd /Users/teial/Tutorials/AI/scholar_source/web
test -f .env.local || cp .env.example .env.local
```

Then edit `web/.env.local`:

```env
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=http://127.0.0.1:54321
VITE_SUPABASE_ANON_KEY=<paste local anon or publishable key>
VITE_SEARCH_TIMEOUT_MINUTES=5
```

Current project-specific blocker:

`web/src/lib/supabase.js` currently rejects Supabase URLs that do not start with
`https://` and do not include `.supabase.co`. It also rejects keys that do not
start with `eyJ`. Those guards can block local Supabase, especially newer local
keys printed as `sb_publishable_...`. Before the frontend can use this local
stack, update that validation to allow `http://127.0.0.1:54321`,
`http://localhost:54321`, and local publishable keys when `import.meta.env.DEV`
is true.

Start the frontend:

```bash
cd /Users/teial/Tutorials/AI/scholar_source/web
npm run dev
```

## Verify the Schema

Open Supabase Studio:

```bash
open http://127.0.0.1:54323
```

Or inspect with `psql`:

```bash
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres -c '\dx'
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres -c '\dt public.*'
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres -c '\d public.rag_embeddings'
```

Expected extension output should include:

```text
vector
pgcrypto
```

Expected tables should include:

```text
jobs
rag_runs
rag_sources
rag_source_rejections
rag_extracted_documents
rag_chunks
rag_embeddings
rag_run_steps
```

## Verify the Supabase REST API

Use the local anon or publishable key from `supabase status`:

```bash
export LOCAL_SUPABASE_URL=http://127.0.0.1:54321
export LOCAL_SUPABASE_ANON_KEY='<paste local anon or publishable key>'
```

Call PostgREST:

```bash
curl "$LOCAL_SUPABASE_URL/rest/v1/rag_sources?select=id,normalized_url,title&limit=1" \
  -H "apikey: $LOCAL_SUPABASE_ANON_KEY" \
  -H "Authorization: Bearer $LOCAL_SUPABASE_ANON_KEY"
```

An empty JSON array is fine:

```json
[]
```

If you get a relation-not-found error, the local schema was not applied. Run:

```bash
supabase db reset
```

## Create a Local Test User

The app uses Supabase Auth and RLS, so browser flows need a local user.

The easiest path is to use the app signup form while the frontend points at
local Supabase. Supabase local email confirmation links appear in Mailpit:

```text
http://127.0.0.1:54324
```

You can also create users in local Supabase Studio:

```text
http://127.0.0.1:54323
```

Use local-only test accounts. Do not reuse production credentials.

## Recommended Local RAG Workflow

Use this loop while building RAG pieces:

```bash
cd /Users/teial/Tutorials/AI/scholar_source
supabase start
supabase db reset
export ENVIRONMENT=local
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

In another terminal:

```bash
cd /Users/teial/Tutorials/AI/scholar_source/web
npm run dev
```

After running a local RAG experiment, inspect traceability tables:

```bash
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres \
  -c 'select id, status, weak_evidence_status, created_at from rag_runs order by created_at desc limit 10;'

psql postgresql://postgres:postgres@127.0.0.1:54322/postgres \
  -c 'select title, normalized_url, quality_status, quality_reason from rag_sources order by first_seen_at desc limit 10;'

psql postgresql://postgres:postgres@127.0.0.1:54322/postgres \
  -c 'select chunk_id, embedding_model, embedding_dimensions, embedded_at from rag_embeddings order by embedded_at desc limit 10;'
```

If the experiment writes bad data, reset only the local database:

```bash
supabase db reset
```

## Stop Local Supabase

Stop containers but keep local data:

```bash
supabase stop
```

Stop containers and discard local data volumes:

```bash
supabase stop --no-backup
```

Use `--no-backup` only when you are comfortable losing local data.

## Commands to Avoid

Avoid these during local-only RAG development unless you explicitly intend to
touch a hosted Supabase project:

```bash
supabase link
supabase db push
supabase db push --linked
supabase db reset --linked
supabase db pull
```

If you are using the hosted dev workflow, these commands are allowed only after
you complete the "Optional: Use a Hosted Dev Project Instead" checks above.
Double-check `supabase/.temp/project-ref`, `.env.local`, and `web/.env.local`
before running `supabase db reset --linked`.

## Troubleshooting

If `supabase start` fails because Docker is not running:

```bash
open -a Docker
docker ps
supabase start
```

If ports are already in use, check the conflicting processes:

```bash
lsof -i :54321
lsof -i :54322
lsof -i :54323
lsof -i :54324
```

If the backend still talks to hosted dev, check shell overrides:

```bash
env | grep -E '^(ENVIRONMENT|SUPABASE_|DATABASE_URL)='
```

Then clear hosted values:

```bash
unset SUPABASE_URL
unset SUPABASE_ANON_KEY
unset SUPABASE_SERVICE_ROLE_KEY
unset SUPABASE_JWT_SECRET
unset DATABASE_URL
export ENVIRONMENT=local
```

If `rag_embeddings` fails because `vector` does not exist, confirm the extension:

```bash
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres -c 'create extension if not exists vector;'
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres -c '\dx vector'
supabase db reset
```

If the frontend throws an invalid Supabase URL error, update
`web/src/lib/supabase.js` to allow local Supabase URLs in development.

If `supabase projects list` fails with an access-token error:

```bash
supabase login
supabase projects list
```

If `cat supabase/.temp/project-ref` says the file does not exist, the repo is
not linked to a hosted project yet:

```bash
supabase link --project-ref YOUR_DEV_PROJECT_REF
cat supabase/.temp/project-ref
```

## References

- Supabase CLI local development:
  <https://supabase.com/docs/guides/local-development/cli/getting-started>
- Supabase CLI reference:
  <https://supabase.com/docs/reference/cli>
