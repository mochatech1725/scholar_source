# ScholarSource v2 Implementation Plan

## Overview

This plan turns the ScholarSource v2 learning plan into an execution checklist. The goal is to rebuild ScholarSource as a production-style RAG system while preserving the most important constraint: you write the implementation first, and AI acts as a tutor, reviewer, debugger, and architecture partner.

ScholarSource v2 replaces the current agent-first resource discovery flow with a controlled retrieval pipeline. The system should collect source content, split it into reusable chunks, embed those chunks, store them in a vector-enabled database, retrieve the most relevant evidence for a student query, rerank the evidence, and synthesize a cited study resource guide. Orchestration is added only after the basic pipeline is stable, tested, observable, and repeatable.

The plan intentionally avoids implementation code. Each section describes what to build, what to learn, what to verify, and what evidence proves the phase is complete.

---

## Guiding Rules

- You write the first version of each core module yourself.
- AI may explain concepts, review code, debug errors, suggest tests, and help compare design options.
- AI should not generate the initial production implementation for modules you want to defend in interviews.
- Every core behavior needs a short explanation you can give from memory.
- Every phase ends with a working artifact, not just notes.
- Every new abstraction should have a measurable reason to exist.
- Every retrieved source shown to a user must be traceable to stored evidence.
- Every generated answer must distinguish retrieved evidence from model synthesis.
- Determinism, observability, and evals are product features, not cleanup work.

---

## [x] Phase 0: Baseline, Diagnosis, and Project Contract

**Goal:** Understand the current system failure modes before replacing them.

**Primary learning focus:** Diagnosis, observability mindset, system boundaries.

### [x] 0.1 Baseline Current Behavior

- [x] 0.1.1 Pick one representative course or textbook input.
- [x] 0.1.2 Run the current system five times with the same input.
  - Current evidence captures five completed same-input runs from Railway API and worker logs. One additional same-input job in the worker log was cancelled before execution and is not counted as a completed baseline run.
- [x] 0.1.3 Save each final output.
  - Current saved evidence is log-derived, not clean machine-readable final result JSON per job. Use stored job results later if exact final URL comparison is needed.
- [x] 0.1.4 Record whether the same sources appear across runs.
- [x] 0.1.5 Record whether the same search terms appear across runs.
- [x] 0.1.6 Record whether the same topics are extracted across runs.
- [x] 0.1.7 Record whether the final prose changes while sources stay stable.
- [x] 0.1.8 Summarize the largest inconsistency in one paragraph.
- [x] 0.1.9 Results: the largest inconsistency is the agentic retrieval harness. The resource search agent makes different search-planning decisions for the same input, which leads to different search queries, different candidate resources, different validation inputs, and different final outputs.

### [x] 0.2 Identify Root Cause Categories

The main inconsistency appears to come from nondeterministic query generation inside the agentic retrieval harness. The search agent can make different planning decisions for the same input, which changes the search queries it sends, the web results it receives, the sources selected for extraction, and the material passed into validation and LLM synthesis. Source extraction and synthesis may amplify the differences, but they are downstream effects rather than the primary cause. Missing run logs make this harder to prove precisely, but the behavior points to search-planning nondeterminism as the root instability source.

### [x] 0.3 Define the Development Contract

- [x] 0.3.1 Confirm the project rules for what you write and what AI can assist with.
- [x] 0.3.2 Add hard rules for citations, source quality, and hallucinated URLs.
- [x] 0.3.3 Add hard rules for logging and traceability.
- [x] 0.3.4 Add hard rules for when a result is too weak to show confidently.
- [x] 0.3.5 Add a short explanation of the v2 architecture goal.

### [x] 0.4 Set Up Observability

- [x] 0.4.1 Create tracing accounts or projects needed for LLM and retrieval visibility.
  - Sign up at [smith.langchain.com](https://smith.langchain.com) (free tier). Generate an API key from **Settings → API Keys**.
  - Note which **organization/workspace** the key belongs to — it's shown in the top-left selector in the LangSmith UI. Traces only appear in the workspace the key was scoped to.
- [x] 0.4.2 Add local environment values for tracing.
  - Required vars in `.env.local`: `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT` (any project name; LangSmith creates it on first trace if it doesn't exist), `LANGSMITH_ENDPOINT=https://api.smith.langchain.com`.
  - `OPENAI_API_KEY` must also be set — the env vars above only configure *where traces go*, not what makes the LLM call.
- [x] 0.4.3 Verify that a simple LLM call appears in the tracing dashboard.
  - Env vars alone produce no traces. Something has to call an LLM through an instrumented client: either a LangChain wrapper (e.g. `ChatOpenAI` from `langchain-openai`) or the raw OpenAI SDK wrapped in the `langsmith` SDK's `@traceable` decorator.
  - Added `langchain-openai==1.3.3` and `langsmith==0.9.5` to `pyproject.toml` for this reason — install them (`pip install langchain-openai==1.3.3 langsmith==0.9.5` or `uv sync`) before expecting any trace to appear.
  - Verified using `scripts/verify_langsmith_trace.py`, a rerunnable script that loads `.env.local` and makes one `ChatOpenAI` call.
- [x] 0.4.4 Verify that request timing and token usage are visible.
  - Both appear automatically on the trace detail page — no extra configuration needed once 0.4.3 works.
- [x] 0.4.5 Document where to inspect traces during debugging.
  - Traces appear at smith.langchain.com under **Projects → `<LANGSMITH_PROJECT value>`** (e.g. `scholar-source-v2-local`), not on the dashboard home page.
  - Click into a run to see input/output, latency, and token counts. For multi-step pipeline code (Phase 1+), the same view shows a run tree of nested steps (retrieve → rerank → synthesize), not just a single call.
  - If a trace doesn't show up: check the org/workspace selector (top-left) — API keys are scoped to one org, and traces silently land wherever the key belongs, which may not be the workspace you're currently viewing.

### 0.5 Phase Completion Criteria

- [x] 0.5.1 You have five saved baseline runs from v1.
- [x] 0.5.2 You can explain what changed between those runs.
- [x] 0.5.3 You have a written diagnosis of the most likely instability source.
- [x] 0.5.4 You have a project contract that defines AI usage and system guardrails.
- [x] 0.5.5 You can view at least one traced LLM call.

### Phase 0 Status

Phase 0 is complete. Current saved evidence contains five completed same-input v1 runs. The completed runs show nondeterministic search-query generation, different search counts, different candidate resources, and different final resource counts for the same submitted input.

---

## [ ] Phase 1: Controlled Non-Agentic RAG Pipeline

**Goal:** Build the simplest reliable retrieval pipeline before adding orchestration or agent behavior.

**Primary learning focus:** Chunking, embeddings, vector search, reranking, cited synthesis.

### 1.0 Phase 1 Course Checkpoints

- [ ] 1.0.1 Start *Vector Database and Document Retrieval* (Manning liveProject, Matteus Tanha) before writing the Phase 1 RAG modules. Covers chunking, embeddings, and vector storage using Qdrant.
- [ ] 1.0.2 Finish the chunking, embedding, and vector storage lessons in *Vector Database and Document Retrieval* before implementing `backend/rag/chunking/`, `backend/rag/embeddings/`, and the vector storage layer in `backend/rag/retrieval/`. Translate Qdrant specific code into the Supabase and pgvector schema already defined in `supabase_schema.sql`.
- [ ] 1.0.3 Start *Hybrid Search and Retrieval Evaluation* (Manning liveProject, Matteus Tanha) after the first end to end retrieval path works once, meaning source extraction, chunking, embedding, vector storage, and basic semantic retrieval. Covers BM25, reciprocal rank fusion, and retrieval metrics like precision, recall, MRR, and NDCG.
- [ ] 1.0.4 Finish the hybrid ranking and evaluation lessons before implementing `backend/rag/reranking/`.
- [ ] 1.0.5 Start *Prompt Engineering for Context-Aware Q&A* (Manning liveProject, Matteus Tanha) before implementing cited synthesis. Covers system prompt design for staying on context, context injection for top ranked chunks, and source attribution.
- [ ] 1.0.6 Finish the prompt design and source attribution lessons before implementing the cited synthesis logic in section 1.9.
- [ ] 1.0.7 Hold off on *Building an Agentic RAG System with LangGraph* (Manning liveProject, Matteus Tanha) until Phase 1 is complete. That project covers tool wrapping, self evaluation nodes, and retry and fallback loops, which belong to a later agentic phase, not this one.

### 1.1 Define the Pipeline Boundary

- [ ] 1.1.1 Decide the pipeline boundary: the minimum accepted input for v2, the minimum accepted output, which existing frontend behavior stays unchanged, and which current backend flow gets bypassed or replaced during v2 work.
- [ ] 1.1.2 Write a short pipeline diagram in prose.

### 1.2 Source Collection

- [ ] 1.2.1 Decide the source collection design: the first source type to support, what metadata must be saved for every source, and what makes a source eligible versus rejected.
- [ ] 1.2.2 Add a manual test input with known good source candidates.
- [ ] 1.2.3 Verify source collection can return stable source records for the same input.

### 1.3 Text Extraction

- [ ] 1.3.1 Extract readable text from collected sources.
- [ ] 1.3.2 Preserve source title, URL, and extraction timestamp.
- [ ] 1.3.3 Handle pages with no usable text.
- [ ] 1.3.4 Handle fetch failures without crashing the entire run.
- [ ] 1.3.5 Store or log enough information to debug extraction failures.
- [ ] 1.3.6 Verify the same source produces the same extracted content when cached.

### 1.4 Chunking

*Reference: Vector Database and Document Retrieval (Manning liveProject, Matteus Tanha)*

- [ ] 1.4.1 Decide the initial chunk size and overlap, and be ready to explain why the overlap value is useful.
- [ ] 1.4.2 Preserve source metadata on every chunk.
- [ ] 1.4.3 Preserve chunk order within the source.
- [ ] 1.4.4 Add a way to inspect chunks for a single source.
- [ ] 1.4.5 Verify chunks are neither too tiny to be useful nor too large to retrieve precisely.

### 1.5 Embeddings

*Reference: Vector Database and Document Retrieval (Manning liveProject, Matteus Tanha)*

- [ ] 1.5.1 Generate embeddings for extracted chunks.
- [ ] 1.5.2 Log the embedding model used.
- [ ] 1.5.3 Store the embedding model version or identifier with each embedded chunk.
- [ ] 1.5.4 Add a deduplication rule so identical content is not embedded repeatedly.
- [ ] 1.5.5 Verify repeated runs do not create duplicate embeddings for unchanged content.
- [ ] 1.5.6 Explain what the embedding vector represents in plain English.

### 1.6 Vector Storage

*Reference: Vector Database and Document Retrieval (Manning liveProject, Matteus Tanha). The course uses Qdrant; translate concepts to the Supabase and pgvector schema below.*

### Qdrant to Postgres and pgvector Translation Reference

| Concept | Qdrant Term / Call | Postgres and pgvector Equivalent |
|---|---|---|
| Table of vectors | Collection | Table with a vector column |
| Stored item | Point (id, vector, payload) | Row (vector column plus ordinary metadata columns) |
| Create the table | `client.create_collection()`, vector size and distance metric set upfront | `CREATE TABLE` with a `vector(1536)` column, then `CREATE INDEX` for HNSW separately |
| Insert data | `client.upsert()` | `INSERT INTO` or `UPSERT` statement |
| Similarity search | `client.search()`, returns scored results | SQL query using `<=>` for cosine distance, ordered and limited to top N |
| Metadata filtering combined with search | Qdrant's built in filter query objects | Normal `WHERE` clause combined with the vector distance ordering in the same SQL query |
| Distance metric setting | Set explicitly at collection creation | Determined by which operator you use in the query (`<=>` for cosine, `<->` for Euclidean, etc.) |

**Rule of thumb:** any method call starting with `client.` that creates, inserts, or searches is Qdrant specific and needs a Postgres translation. Anything conceptual the course explains before the code, such as why you chunk a certain way, why you pick a certain vector size, or why cosine distance makes sense, carries over directly with no translation needed.

- Schema contract files:
  - Fresh database bootstrap: `supabase_schema.sql`
  - Incremental migration: `migrations/001_create_rag_traceability_schema.sql`
  - Required v2 tables: `rag_sources`, `rag_source_rejections`, `rag_extracted_documents`, `rag_chunks`, `rag_embeddings`, `rag_runs`, and `rag_run_steps`
  - Legacy note: older databases may still have `course_cache`; the current backend does not reference it, so the v2 migration leaves it untouched and fresh installs do not recreate it.
  - Current schema status: SQL contract exists, but it still needs to be applied and verified against Supabase before marking vector storage complete.

- [ ] 1.6.1 Enable vector search in the database.
- [ ] 1.6.2 Create storage for chunk text, vector values, source metadata, content hashes, and timestamps.
- [ ] 1.6.3 Add indexes required for retrieval performance.
- [ ] 1.6.4 Add a way to reset local test data safely.
- [ ] 1.6.5 Verify inserted chunks can be retrieved by source and by semantic similarity.

### 1.7 Semantic Retrieval

*Reference: Vector Database and Document Retrieval (Manning liveProject, Matteus Tanha)*

- [ ] 1.7.1 Convert the user query into the same embedding space as stored chunks.
- [ ] 1.7.2 Retrieve the top matching chunks.
- [ ] 1.7.3 Return similarity scores with retrieved chunks.
- [ ] 1.7.4 Preserve enough metadata to cite every retrieved chunk.
- [ ] 1.7.5 Verify known queries retrieve expected source chunks.
- [ ] 1.7.6 Verify irrelevant queries do not return confident looking weak results.

### 1.8 Reranking

*Reference: Hybrid Search and Retrieval Evaluation (Manning liveProject, Matteus Tanha). The course uses BM25 fused with reciprocal rank fusion rather than a cross encoder, but it satisfies the same requirement below.*

- [ ] 1.8.1 Score retrieved chunks against the original user need.
- [ ] 1.8.2 Separate retrieval similarity from final relevance ranking.
- [ ] 1.8.3 Keep the original retrieval score for debugging.
- [ ] 1.8.4 Keep the rerank score for debugging.
- [ ] 1.8.5 Verify reranking changes order when the nearest chunk is not the most useful chunk.
- [ ] 1.8.6 Define what score is too weak to include.

### 1.9 Cited Synthesis

*Reference: Prompt Engineering for Context-Aware Q&A (Manning liveProject, Matteus Tanha)*

- [ ] 1.9.1 Generate a final study guide from only the selected evidence.
- [ ] 1.9.2 Require every recommendation to include a source citation.
- [ ] 1.9.3 Refuse or soften the answer when retrieved evidence is insufficient.
- [ ] 1.9.4 Include source titles and URLs in the final response.
- [ ] 1.9.5 Avoid presenting unsupported claims as facts.
- [ ] 1.9.6 Verify the answer can be traced back to stored chunks.

### 1.10 Phase Completion Criteria

- [ ] 1.10.1 One input can complete the full path from query to cited answer.
- [ ] 1.10.2 The answer is based on stored chunks, not live only search output.
- [ ] 1.10.3 Every cited recommendation maps back to source metadata.
- [ ] 1.10.4 You can explain each pipeline step from memory.
- [ ] 1.10.5 You have at least one manual test case that proves the pipeline works end to end.
- [ ] 1.10.6 You can articulate the retrieval evaluation metrics from *Hybrid Search and Retrieval Evaluation* (precision, recall, MRR, NDCG, groundedness) for your own pipeline's results, even informally.

---

## [ ] Phase 2: Repeatability, Caching, and Run Logs

**Goal:** Make identical inputs produce stable, debuggable results.

**Primary learning focus:** Caching, content hashes, run records, deterministic settings.

### 2.1 Deterministic Configuration

- [ ] 2.1.1 Identify every LLM call in the v2 pipeline.
- [ ] 2.1.2 Set deterministic settings wherever stable behavior is required.
- [ ] 2.1.3 Document any step that intentionally allows variation.
- [ ] 2.1.4 Ensure query generation uses stable settings.
- [ ] 2.1.5 Ensure synthesis uses stable settings unless there is a clear reason not to.

### 2.2 Source and Extraction Cache

- [ ] 2.2.1 Cache collected source results by normalized query or query hash.
- [ ] 2.2.2 Cache fetched source content by normalized URL or URL hash.
- [ ] 2.2.3 Store fetch timestamp and cache freshness rules.
- [ ] 2.2.4 Avoid refetching unchanged sources during repeated runs.
- [ ] 2.2.5 Add a manual way to invalidate cached source content during development.

### 2.3 Embedding Deduplication

- [ ] 2.3.1 Hash chunk content before embedding.
- [ ] 2.3.2 Check whether an embedding already exists before calling the embedding provider.
- [ ] 2.3.3 Reuse existing embeddings when content and model match.
- [ ] 2.3.4 Re-embed content only when the model changes or the content changes.
- [ ] 2.3.5 Track duplicate avoidance in logs.

### 2.4 Run Logging

- [ ] 2.4.1 Create a run record for every submitted query.
- [ ] 2.4.2 Log normalized input.
- [ ] 2.4.3 Log generated search terms.
- [ ] 2.4.4 Log collected source identifiers.
- [ ] 2.4.5 Log retrieved chunk identifiers.
- [ ] 2.4.6 Log reranked order.
- [ ] 2.4.7 Log final selected evidence.
- [ ] 2.4.8 Log total latency and major step timings.
- [ ] 2.4.9 Log token usage and provider cost when available.
- [ ] 2.4.10 Log failure states in a structured way.

### 2.5 Run Comparison

- [ ] 2.5.1 Add a simple way to compare two runs with the same input.
- [ ] 2.5.2 Compare collected sources.
- [ ] 2.5.3 Compare retrieved chunks.
- [ ] 2.5.4 Compare reranked order.
- [ ] 2.5.5 Compare final cited sources.
- [ ] 2.5.6 Use the comparison to explain any differences between runs.

### 2.6 Phase Completion Criteria

- [ ] 2.6.1 Run the same input five times through v2.
- [ ] 2.6.2 Confirm the same top evidence appears each time, unless cache freshness intentionally changes it.
- [ ] 2.6.3 Confirm final citations are stable.
- [ ] 2.6.4 Confirm run logs make differences explainable.
- [ ] 2.6.5 You can point to one run record and explain the full path from input to output.

---

## [ ] Phase 3: Evaluation Harness

**Goal:** Define what good means and make regressions visible before they reach users.

**Primary learning focus:** Golden datasets, retrieval metrics, answer groundedness, CI gates.

### 3.0 Phase 3 Course Checkpoint

- [ ] 3.0.1 Start [Evaluating AI Agents - DeepLearning.AI](https://www.deeplearning.ai/courses/evaluating-ai-agents) before creating the Phase 3 golden test set and eval metrics.
- [ ] 3.0.2 Finish the evaluation design lessons before setting final local and CI eval thresholds.

### 3.1 Golden Test Set

- [ ] 3.1.1 Create twenty representative student queries.
- [ ] 3.1.2 Include a mix of textbook-based, topic-based, and course-based inputs.
- [ ] 3.1.3 For each case, list expected source domains or URLs.
- [ ] 3.1.4 For each case, list forbidden source types.
- [ ] 3.1.5 For each case, list key concepts that should appear in the answer.
- [ ] 3.1.6 Include at least three cases where good sources are hard to find.
- [ ] 3.1.7 Include at least three cases where low-quality sources are tempting.

### 3.2 Retrieval Evaluation

- [ ] 3.2.1 Measure whether retrieved chunks are relevant to the query.
- [ ] 3.2.2 Measure whether expected source domains appear.
- [ ] 3.2.3 Measure whether forbidden source types are excluded.
- [ ] 3.2.4 Measure whether top results are better than lower-ranked results.
- [ ] 3.2.5 Set an initial threshold for acceptable retrieval quality.
- [ ] 3.2.6 Save baseline retrieval scores.

### 3.3 Generation Evaluation

- [ ] 3.3.1 Measure whether answers are grounded in retrieved evidence.
- [ ] 3.3.2 Measure whether answers include required concepts.
- [ ] 3.3.3 Measure whether answers avoid forbidden claims.
- [ ] 3.3.4 Measure whether citations are present and usable.
- [ ] 3.3.5 Set an initial threshold for acceptable answer quality.
- [ ] 3.3.6 Save baseline generation scores.

### 3.4 Regression Gate

- [ ] 3.4.1 Add a repeatable command to run the eval suite locally.
  - Scaffold command exists: `uv run --extra dev run-evals`. If `just` is installed, `just evals` runs the same command. It validates `evals/golden_cases.json`; RAG pipeline scoring is not implemented yet.
- [ ] 3.4.2 Add eval output that is easy to compare over time.
- [ ] 3.4.3 Add thresholds that fail when quality drops too far.
- [ ] 3.4.4 Add a lightweight CI path for the golden test set.
- [ ] 3.4.5 Decide which expensive evals run locally only and which run in CI.

### Eval Harness Scaffold Status

Initial eval scaffold exists at `evals/`:

- `evals/golden_cases.json`
- `evals/README.md`
- `evals/run_evals.py`
- `evals/results/.gitkeep`

Verified scaffold commands:

- `uv run --extra dev run-evals`
- `just evals`
- `uv run --extra dev ruff check evals/run_evals.py`
- `uv run --extra dev ruff format --check evals/run_evals.py`

Project task aliases now live in `justfile`. Use `just --list` to inspect available commands such as `just lint`, `just test`, `just frontend-test`, `just evals`, and `just validate`.

Current status: schema validation works; RAG pipeline scoring is not implemented yet.

### 3.5 Phase Completion Criteria

- [ ] 3.5.1 You have twenty golden cases.
- [ ] 3.5.2 You can run evals repeatedly.
- [ ] 3.5.3 You have baseline scores for retrieval and generation.
- [ ] 3.5.4 A bad retrieval change can fail the eval suite.
- [ ] 3.5.5 You can explain the difference between a normal test and an eval.

---

## [ ] Phase 4: Stateful Orchestration

**Goal:** Add workflow control only after the retrieval pipeline is reliable.

**Primary learning focus:** Graph state, node boundaries, conditional routing, fallbacks.

### 4.0 Phase 4 Course Checkpoint

- [ ] 4.0.1 Start [AI Agents in LangGraph - DeepLearning.AI](https://www.deeplearning.ai/courses/ai-agents-in-langgraph) before designing the Phase 4 graph state or node boundaries.
- [ ] 4.0.2 Finish the graph construction and state management lessons before implementing LangGraph orchestration in the repo.

### 4.1 Preconditions

- [ ] 4.1.1 Confirm Phase 1 end-to-end flow works.
- [ ] 4.1.2 Confirm Phase 2 repeatability checks pass.
- [ ] 4.1.3 Confirm Phase 3 evals have a baseline.
- [ ] 4.1.4 Identify what orchestration problem actually needs solving.
- [ ] 4.1.5 Avoid adding orchestration just to make the architecture look more advanced.

### 4.2 Define Graph State

- [ ] 4.2.1 List every field that moves through the workflow.
- [ ] 4.2.2 Identify which step creates each field.
- [ ] 4.2.3 Identify which step reads each field.
- [ ] 4.2.4 Identify which fields are user-facing.
- [ ] 4.2.5 Identify which fields are debug-only.
- [ ] 4.2.6 Decide how errors and fallback reasons are represented.

### 4.3 Define Workflow Steps

- [ ] 4.3.1 Add a request classification step.
- [ ] 4.3.2 Add a search term generation step.
- [ ] 4.3.3 Add a candidate retrieval step.
- [ ] 4.3.4 Add a candidate quality evaluation step.
- [ ] 4.3.5 Add a reranking step.
- [ ] 4.3.6 Add a synthesis step.
- [ ] 4.3.7 Add a fallback path for weak evidence.
- [ ] 4.3.8 Add a transparent user response when quality is too low.

### 4.4 Fallback Behavior

- [ ] 4.4.1 Decide the fallback policy: what counts as insufficient evidence, when to broaden a query, when to try alternate source types, and when to stop and return a transparent limitation message.
- [ ] 4.4.2 Log every fallback decision.
- [ ] 4.4.3 Include fallback behavior in eval coverage.

### 4.5 Phase Completion Criteria

- [ ] 4.5.1 The workflow produces the same successful outputs as the linear pipeline.
- [ ] 4.5.2 Weak retrieval results follow a clear fallback path.
- [ ] 4.5.3 The graph state can be inspected in traces.
- [ ] 4.5.4 You can draw the workflow from memory.
- [ ] 4.5.5 You can explain why orchestration was added after the pipeline was stable.

---

## [ ] Phase 5: Product Integration and User Experience

**Goal:** Connect the v2 pipeline to the existing product surface and make the experience usable beyond a demo.

**Primary learning focus:** Full-stack integration, async UX, error states, user trust.

### 5.1 Backend Integration

- [ ] 5.1.1 Decide the backend integration approach: how v2 jobs are submitted, how job status is stored, and whether v1 and v2 run side by side during migration.
- [ ] 5.1.2 Preserve authentication requirements.
- [ ] 5.1.3 Preserve rate limiting requirements.
- [ ] 5.1.4 Preserve job ownership checks.
- [ ] 5.1.5 Return structured failure messages to the frontend.

### 5.2 Frontend Flow

- [ ] 5.2.1 Keep the input experience simple.
- [ ] 5.2.2 Show meaningful progress while the pipeline runs.
- [ ] 5.2.3 Show retrieval and synthesis stages in user-friendly language.
- [ ] 5.2.4 Show final cited results clearly.
- [ ] 5.2.5 Show source links in a way that encourages inspection.
- [ ] 5.2.6 Show weak-result warnings when confidence is low.
- [ ] 5.2.7 Handle empty results without a blank screen.
- [ ] 5.2.8 Handle expired sessions.

### 5.3 Trust and Safety

- [ ] 5.3.1 Make citations visible.
- [ ] 5.3.2 Make source quality signals visible.
- [ ] 5.3.3 Avoid implying that a generated guide replaces the original course material.
- [ ] 5.3.4 Avoid storing unnecessary user-provided sensitive content.
- [ ] 5.3.5 Limit repeated expensive requests.
- [ ] 5.3.6 Make failures understandable without exposing internal details.

### 5.4 Mobile and Accessibility

- [ ] 5.4.1 Test the main submission flow on a phone-sized viewport.
- [ ] 5.4.2 Test the final results page on a phone-sized viewport.
- [ ] 5.4.3 Verify keyboard navigation for form controls.
- [ ] 5.4.4 Verify visible focus states.
- [ ] 5.4.5 Verify color contrast for status and warning messages.
- [ ] 5.4.6 Verify long URLs and long source titles do not break layout.

### 5.5 Phase Completion Criteria

- [ ] 5.5.1 A signed-in user can submit a v2 request from the frontend.
- [ ] 5.5.2 The user can watch progress without refreshing.
- [ ] 5.5.3 The final response includes usable citations.
- [ ] 5.5.4 Expected error states are visible and understandable.
- [ ] 5.5.5 The flow works on desktop and mobile.

---

## [ ] Phase 6: Shipping, Feedback, and Portfolio Evidence

**Goal:** Ship the project as a credible personal project with measurable quality and a clear story.

**Primary learning focus:** Release discipline, user feedback, interview readiness.

### 6.1 Release Readiness

- [ ] 6.1.1 Run backend tests.
- [ ] 6.1.2 Run frontend tests.
- [ ] 6.1.3 Run the eval suite.
- [ ] 6.1.4 Run the same-input repeatability check.
- [ ] 6.1.5 Check logs for noisy warnings.
- [ ] 6.1.6 Check production environment variables.
- [ ] 6.1.7 Check rate limits and provider quotas.
- [ ] 6.1.8 Verify deployment health checks.

### 6.2 User Feedback

- [ ] 6.2.1 Recruit ten non-friend users.
- [ ] 6.2.2 Give users one clear task to complete.
- [ ] 6.2.3 Record where users hesitate.
- [ ] 6.2.4 Record which results they trust.
- [ ] 6.2.5 Record which results they ignore.
- [ ] 6.2.6 Ask whether the source citations are useful.
- [ ] 6.2.7 Turn feedback into a prioritized fix list.

### 6.3 Public Project Evidence

- [ ] 6.3.1 Add a concise v2 explanation to the project README.
- [ ] 6.3.2 Add a dated changelog entry for the v2 rewrite.
- [ ] 6.3.3 Add a short architecture summary.
- [ ] 6.3.4 Add current eval scores.
- [ ] 6.3.5 Add current repeatability result.
- [ ] 6.3.6 Add known limitations.
- [ ] 6.3.7 Add planned next improvements.

### 6.4 Interview Readiness

- [ ] 6.4.1 Memorize the 60-second project pitch.
- [ ] 6.4.2 Practice drawing the architecture in two minutes.
- [ ] 6.4.3 Prepare one tradeoff you made.
- [ ] 6.4.4 Prepare one bug you diagnosed from traces.
- [ ] 6.4.5 Prepare one example where evals caught a regression.
- [ ] 6.4.6 Prepare one example where you rejected an AI suggestion.
- [ ] 6.4.7 Prepare one user feedback story.

### 6.5 Phase Completion Criteria

- [ ] 6.5.1 The app is deployed.
- [ ] 6.5.2 At least ten users have tried the v2 flow.
- [ ] 6.5.3 The README explains what changed and why.
- [ ] 6.5.4 Eval and repeatability metrics are documented.
- [ ] 6.5.5 You can explain the architecture without reading the code.

---

## Implementation Order

- [ ] Diagnose current v1 behavior with repeated runs.
- [ ] Set up tracing and project guardrails.
- [ ] Build source collection for one source type.
- [ ] Build extraction and caching.
- [ ] Build chunking.
- [ ] Build embedding generation and deduplication.
- [ ] Build vector storage.
- [ ] Build semantic retrieval.
- [ ] Build reranking.
- [ ] Build cited synthesis.
- [ ] Add run logging.
- [ ] Add run comparison.
- [ ] Build the golden eval set.
- [ ] Add retrieval evals.
- [ ] Add generation evals.
- [ ] Add CI thresholds.
- [ ] Add stateful orchestration and fallback routing.
- [ ] Connect the v2 flow to the backend job system.
- [ ] Connect the v2 flow to the frontend.
- [ ] Test desktop, mobile, errors, and empty states.
- [ ] Ship to real users.
- [ ] Document metrics, lessons, and next steps.

---

## Review Checkpoints

Use these checkpoints when asking AI for help. The goal is to review your work without replacing your authorship.

### Checkpoint A: After Diagnosis

- [ ] Ask for feedback on whether the diagnosis is evidence-based.
- [ ] Ask what additional logs would make the conclusion stronger.
- [ ] Ask whether the proposed v2 architecture addresses the observed failure mode.

### Checkpoint B: After Chunking and Embeddings

- [ ] Ask for review of chunk boundaries and metadata preservation.
- [ ] Ask whether deduplication is robust enough.
- [ ] Ask whether the storage shape supports future debugging.

### Checkpoint C: After Retrieval

- [ ] Ask whether retrieval results are explainable.
- [ ] Ask whether similarity scores are being interpreted carefully.
- [ ] Ask what edge cases are missing from manual tests.

### Checkpoint D: After Reranking and Synthesis

- [ ] Ask whether citations are grounded.
- [ ] Ask whether the answer overstates weak evidence.
- [ ] Ask whether failure behavior is honest and user-friendly.

### Checkpoint E: After Evals

- [ ] Ask whether the golden set is diverse enough.
- [ ] Ask whether thresholds are too loose or too strict.
- [ ] Ask whether metrics align with the product goal.

### Checkpoint F: Before Shipping

- [ ] Ask for a code review focused on bugs and regressions.
- [ ] Ask for a UX review focused on error, empty, and loading states.
- [ ] Ask for an interview-readiness review of the architecture explanation.

---

## Metrics

| Metric | Why It Matters | Initial Target |
| --- | --- | --- |
| Eval pass rate | Shows whether output quality is improving or regressing | Above 80 percent |
| Retrieval consistency | Shows whether identical inputs retrieve stable evidence | 100 percent for top evidence in cached runs |
| Citation coverage | Shows whether recommendations are traceable | 100 percent for final recommendations |
| Retrieval latency | Shows whether the app feels responsive | Under 3 seconds for common cached retrieval |
| End-to-end latency | Shows whether the full workflow is usable | Track baseline first, then improve |
| User completion rate | Shows whether users can finish the main flow | Track after first user test |

---

## Definition of Done for ScholarSource v2

- [ ] The system can return cited study resources for real student inputs.
- [ ] Retrieved evidence is stored and traceable.
- [ ] Repeated cached runs produce stable top evidence.
- [ ] The eval suite runs locally.
- [ ] The eval suite protects against obvious retrieval regressions.
- [ ] The frontend displays progress, success, empty, and failure states.
- [ ] The production deployment has required environment values.
- [ ] The README explains the rewrite and current metrics.
- [ ] At least one real user feedback cycle has produced a shipped improvement.
- [ ] You can explain and debug every major part of the pipeline.

---
