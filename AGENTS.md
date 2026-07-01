# ScholarSource — Agent Contract

## Stack

Backend: Python 3.12, FastAPI, Pydantic v2, Supabase (PostgreSQL + pgvector), Celery + Redis, OpenAI/Anthropic embeddings and LLMs.
RAG tooling: LangChain for loading, splitting, and retrieval chains; LangGraph for workflow orchestration; Ragas + LangSmith for evals and tracing.
Frontend: React 19, Vite, Tailwind CSS 3, TypeScript/TSX.
Infrastructure: Railway (backend), Cloudflare Pages (frontend), Supabase (db + auth), GitHub Actions (CI/CD).

See `docs/react_tailwind_guidelines.md` for React and Tailwind conventions.

## Naming Conventions

Python: `snake_case` functions and variables, `PascalCase` classes, `UPPER_SNAKE_CASE` constants, `_single_underscore` for non-public names.
React/JS: `PascalCase` components, `camelCase` functions, `kebab-case` filenames, `useFoo` for custom hooks.
Database columns: `snake_case`. Boolean fields read as yes/no questions: `is_active`, `has_error`, `can_retry`.

## Authorship Rules

The human writes the first version of every core pipeline module: chunker, embedder, vector store client, retriever, reranker, and synthesis prompt.

AI may generate: boilerplate (Pydantic schemas, route stubs, test fixtures, SQL migrations), utility helpers with no retrieval logic, and frontend UI components.

AI may not generate the initial production implementation of any module the human intends to explain or defend in an interview.

## Hard Rules — Never Break

1. Never return a source to the user without a verified, stored URL.
2. Every cited recommendation must map back to a stored chunk with a source ID, URL, and title.
3. Every generated answer must explicitly separate retrieved evidence from model synthesis.
4. Never embed a chunk without storing its content hash and the embedding model identifier alongside it.
5. Never skip a run log entry — every submitted query must produce a structured run record before the pipeline returns.
6. Never present a low-confidence retrieval result as a confident answer; surface a weak-evidence warning instead.
7. Never store or log raw user-submitted content beyond what is required for job processing and traceability.
8. Never call an LLM for synthesis when retrieved evidence is empty; return a transparent limitation message instead.
