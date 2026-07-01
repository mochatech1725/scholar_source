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

## [ ] Phase 0: Baseline, Diagnosis, and Project Contract

**Goal:** Understand the current system failure modes before replacing them.

**Primary learning focus:** Diagnosis, observability mindset, system boundaries.

### [x]0.1 Baseline Current Behavior

- [x] Pick one representative course or textbook input.
- [x] Run the current system five times with the same input.
- [x] Save each final output.
- [x] Record whether the same sources appear across runs.
- [x] Record whether the same search terms appear across runs.
- [x] Record whether the same topics are extracted across runs.
- [x] Record whether the final prose changes while sources stay stable.
- [x] Summarize the largest inconsistency in one paragraph.
- [x] Results
 is the agentic retrieval harness: the resource search agent makes different search-planning decisions for the same input, which leads to different search queries, different candidate resources, different validation inputs, and different final outputs.

### [x] 0.2 Identify Root Cause Categories

The main inconsistency appears to come from nondeterministic query generation inside the agentic retrieval harness. The search agent can make different planning decisions for the same input, which changes the search queries it sends, the web results it receives, the sources selected for extraction, and the material passed into validation and LLM synthesis. Source extraction and synthesis may amplify the differences, but they are downstream effects rather than the primary cause. Missing run logs make this harder to prove precisely, but the behavior points to search-planning nondeterminism as the root instability source.

### [x] 0.3 Define the Development Contract

- [x] Confirm the project rules for what you write and what AI can assist with.
- [x] Add hard rules for citations, source quality, and hallucinated URLs.
- [x] Add hard rules for logging and traceability.
- [x] Add hard rules for when a result is too weak to show confidently.
- [x] Add a short explanation of the v2 architecture goal.

### 0.4 Set Up Observability

- [ ] Create tracing accounts or projects needed for LLM and retrieval visibility.
- [ ] Add local environment values for tracing.
- [ ] Verify that a simple LLM call appears in the tracing dashboard.
- [ ] Verify that request timing and token usage are visible.
- [ ] Document where to inspect traces during debugging.

### 0.5 Phase Completion Criteria

- [ ] You have five saved baseline runs from v1.
- [ ] You can explain what changed between those runs.
- [ ] You have a written diagnosis of the most likely instability source.
- [ ] You have a project contract that defines AI usage and system guardrails.
- [ ] You can view at least one traced LLM call.

---

## [ ] Phase 1: Controlled Non-Agentic RAG Pipeline

**Goal:** Build the simplest reliable retrieval pipeline before adding orchestration or agent behavior.

**Primary learning focus:** Chunking, embeddings, vector search, reranking, cited synthesis.

### 1.1 Define the Pipeline Boundary

- [ ] Decide the minimum accepted input for v2.
- [ ] Decide the minimum accepted output for v2.
- [ ] Decide which existing frontend behavior can stay unchanged.
- [ ] Decide which current backend flow should be bypassed or replaced during v2 work.
- [ ] Write a short pipeline diagram in prose.

### 1.2 Source Collection

- [ ] Choose the first source type to support.
- [ ] Define what metadata must be saved for every source.
- [ ] Define what makes a source eligible for inclusion.
- [ ] Define what makes a source rejected.
- [ ] Add a manual test input with known good source candidates.
- [ ] Verify source collection can return stable source records for the same input.

### 1.3 Text Extraction

- [ ] Extract readable text from collected sources.
- [ ] Preserve source title, URL, and extraction timestamp.
- [ ] Handle pages with no usable text.
- [ ] Handle fetch failures without crashing the entire run.
- [ ] Store or log enough information to debug extraction failures.
- [ ] Verify the same source produces the same extracted content when cached.

### 1.4 Chunking

- [ ] Choose an initial chunk size.
- [ ] Choose an initial chunk overlap.
- [ ] Explain why overlap is useful.
- [ ] Preserve source metadata on every chunk.
- [ ] Preserve chunk order within the source.
- [ ] Add a way to inspect chunks for a single source.
- [ ] Verify chunks are neither too tiny to be useful nor too large to retrieve precisely.

### 1.5 Embeddings

- [ ] Generate embeddings for extracted chunks.
- [ ] Log the embedding model used.
- [ ] Store the embedding model version or identifier with each embedded chunk.
- [ ] Add a deduplication rule so identical content is not embedded repeatedly.
- [ ] Verify repeated runs do not create duplicate embeddings for unchanged content.
- [ ] Explain what the embedding vector represents in plain English.

### 1.6 Vector Storage

- [ ] Enable vector search in the database.
- [ ] Create storage for chunk text, vector values, source metadata, content hashes, and timestamps.
- [ ] Add indexes required for retrieval performance.
- [ ] Add a way to reset local test data safely.
- [ ] Verify inserted chunks can be retrieved by source and by semantic similarity.

### 1.7 Semantic Retrieval

- [ ] Convert the user query into the same embedding space as stored chunks.
- [ ] Retrieve the top matching chunks.
- [ ] Return similarity scores with retrieved chunks.
- [ ] Preserve enough metadata to cite every retrieved chunk.
- [ ] Verify known queries retrieve expected source chunks.
- [ ] Verify irrelevant queries do not return confident-looking weak results.

### 1.8 Reranking

- [ ] Score retrieved chunks against the original user need.
- [ ] Separate retrieval similarity from final relevance ranking.
- [ ] Keep the original retrieval score for debugging.
- [ ] Keep the rerank score for debugging.
- [ ] Verify reranking changes order when the nearest chunk is not the most useful chunk.
- [ ] Define what score is too weak to include.

### 1.9 Cited Synthesis

- [ ] Generate a final study guide from only the selected evidence.
- [ ] Require every recommendation to include a source citation.
- [ ] Refuse or soften the answer when retrieved evidence is insufficient.
- [ ] Include source titles and URLs in the final response.
- [ ] Avoid presenting unsupported claims as facts.
- [ ] Verify the answer can be traced back to stored chunks.

### 1.10 Phase Completion Criteria

- [ ] One input can complete the full path from query to cited answer.
- [ ] The answer is based on stored chunks, not live-only search output.
- [ ] Every cited recommendation maps back to source metadata.
- [ ] You can explain each pipeline step from memory.
- [ ] You have at least one manual test case that proves the pipeline works end to end.

---

## [ ] Phase 2: Repeatability, Caching, and Run Logs

**Goal:** Make identical inputs produce stable, debuggable results.

**Primary learning focus:** Caching, content hashes, run records, deterministic settings.

### 2.1 Deterministic Configuration

- [ ] Identify every LLM call in the v2 pipeline.
- [ ] Set deterministic settings wherever stable behavior is required.
- [ ] Document any step that intentionally allows variation.
- [ ] Ensure query generation uses stable settings.
- [ ] Ensure synthesis uses stable settings unless there is a clear reason not to.

### 2.2 Source and Extraction Cache

- [ ] Cache collected source results by normalized query or query hash.
- [ ] Cache fetched source content by normalized URL or URL hash.
- [ ] Store fetch timestamp and cache freshness rules.
- [ ] Avoid refetching unchanged sources during repeated runs.
- [ ] Add a manual way to invalidate cached source content during development.

### 2.3 Embedding Deduplication

- [ ] Hash chunk content before embedding.
- [ ] Check whether an embedding already exists before calling the embedding provider.
- [ ] Reuse existing embeddings when content and model match.
- [ ] Re-embed content only when the model changes or the content changes.
- [ ] Track duplicate avoidance in logs.

### 2.4 Run Logging

- [ ] Create a run record for every submitted query.
- [ ] Log normalized input.
- [ ] Log generated search terms.
- [ ] Log collected source identifiers.
- [ ] Log retrieved chunk identifiers.
- [ ] Log reranked order.
- [ ] Log final selected evidence.
- [ ] Log total latency and major step timings.
- [ ] Log token usage and provider cost when available.
- [ ] Log failure states in a structured way.

### 2.5 Run Comparison

- [ ] Add a simple way to compare two runs with the same input.
- [ ] Compare collected sources.
- [ ] Compare retrieved chunks.
- [ ] Compare reranked order.
- [ ] Compare final cited sources.
- [ ] Use the comparison to explain any differences between runs.

### 2.6 Phase Completion Criteria

- [ ] Run the same input five times through v2.
- [ ] Confirm the same top evidence appears each time, unless cache freshness intentionally changes it.
- [ ] Confirm final citations are stable.
- [ ] Confirm run logs make differences explainable.
- [ ] You can point to one run record and explain the full path from input to output.

---

## [ ] Phase 3: Evaluation Harness

**Goal:** Define what good means and make regressions visible before they reach users.

**Primary learning focus:** Golden datasets, retrieval metrics, answer groundedness, CI gates.

### 3.1 Golden Test Set

- [ ] Create twenty representative student queries.
- [ ] Include a mix of textbook-based, topic-based, and course-based inputs.
- [ ] For each case, list expected source domains or URLs.
- [ ] For each case, list forbidden source types.
- [ ] For each case, list key concepts that should appear in the answer.
- [ ] Include at least three cases where good sources are hard to find.
- [ ] Include at least three cases where low-quality sources are tempting.

### 3.2 Retrieval Evaluation

- [ ] Measure whether retrieved chunks are relevant to the query.
- [ ] Measure whether expected source domains appear.
- [ ] Measure whether forbidden source types are excluded.
- [ ] Measure whether top results are better than lower-ranked results.
- [ ] Set an initial threshold for acceptable retrieval quality.
- [ ] Save baseline retrieval scores.

### 3.3 Generation Evaluation

- [ ] Measure whether answers are grounded in retrieved evidence.
- [ ] Measure whether answers include required concepts.
- [ ] Measure whether answers avoid forbidden claims.
- [ ] Measure whether citations are present and usable.
- [ ] Set an initial threshold for acceptable answer quality.
- [ ] Save baseline generation scores.

### 3.4 Regression Gate

- [ ] Add a repeatable command to run the eval suite locally.
- [ ] Add eval output that is easy to compare over time.
- [ ] Add thresholds that fail when quality drops too far.
- [ ] Add a lightweight CI path for the golden test set.
- [ ] Decide which expensive evals run locally only and which run in CI.

### 3.5 Phase Completion Criteria

- [ ] You have twenty golden cases.
- [ ] You can run evals repeatedly.
- [ ] You have baseline scores for retrieval and generation.
- [ ] A bad retrieval change can fail the eval suite.
- [ ] You can explain the difference between a normal test and an eval.

---

## [ ] Phase 4: Stateful Orchestration

**Goal:** Add workflow control only after the retrieval pipeline is reliable.

**Primary learning focus:** Graph state, node boundaries, conditional routing, fallbacks.

### 4.1 Preconditions

- [ ] Confirm Phase 1 end-to-end flow works.
- [ ] Confirm Phase 2 repeatability checks pass.
- [ ] Confirm Phase 3 evals have a baseline.
- [ ] Identify what orchestration problem actually needs solving.
- [ ] Avoid adding orchestration just to make the architecture look more advanced.

### 4.2 Define Graph State

- [ ] List every field that moves through the workflow.
- [ ] Identify which step creates each field.
- [ ] Identify which step reads each field.
- [ ] Identify which fields are user-facing.
- [ ] Identify which fields are debug-only.
- [ ] Decide how errors and fallback reasons are represented.

### 4.3 Define Workflow Steps

- [ ] Add a request classification step.
- [ ] Add a search term generation step.
- [ ] Add a candidate retrieval step.
- [ ] Add a candidate quality evaluation step.
- [ ] Add a reranking step.
- [ ] Add a synthesis step.
- [ ] Add a fallback path for weak evidence.
- [ ] Add a transparent user response when quality is too low.

### 4.4 Fallback Behavior

- [ ] Define what counts as insufficient evidence.
- [ ] Define when to broaden a query.
- [ ] Define when to try alternate source types.
- [ ] Define when to stop and return a transparent limitation message.
- [ ] Log every fallback decision.
- [ ] Include fallback behavior in eval coverage.

### 4.5 Phase Completion Criteria

- [ ] The workflow produces the same successful outputs as the linear pipeline.
- [ ] Weak retrieval results follow a clear fallback path.
- [ ] The graph state can be inspected in traces.
- [ ] You can draw the workflow from memory.
- [ ] You can explain why orchestration was added after the pipeline was stable.

---

## [ ] Phase 5: Product Integration and User Experience

**Goal:** Connect the v2 pipeline to the existing product surface and make the experience usable beyond a demo.

**Primary learning focus:** Full-stack integration, async UX, error states, user trust.

### 5.1 Backend Integration

- [ ] Decide how v2 jobs are submitted.
- [ ] Decide how v2 job status is stored.
- [ ] Decide whether v1 and v2 can run side by side during migration.
- [ ] Preserve authentication requirements.
- [ ] Preserve rate limiting requirements.
- [ ] Preserve job ownership checks.
- [ ] Return structured failure messages to the frontend.

### 5.2 Frontend Flow

- [ ] Keep the input experience simple.
- [ ] Show meaningful progress while the pipeline runs.
- [ ] Show retrieval and synthesis stages in user-friendly language.
- [ ] Show final cited results clearly.
- [ ] Show source links in a way that encourages inspection.
- [ ] Show weak-result warnings when confidence is low.
- [ ] Handle empty results without a blank screen.
- [ ] Handle expired sessions.

### 5.3 Trust and Safety

- [ ] Make citations visible.
- [ ] Make source quality signals visible.
- [ ] Avoid implying that a generated guide replaces the original course material.
- [ ] Avoid storing unnecessary user-provided sensitive content.
- [ ] Limit repeated expensive requests.
- [ ] Make failures understandable without exposing internal details.

### 5.4 Mobile and Accessibility

- [ ] Test the main submission flow on a phone-sized viewport.
- [ ] Test the final results page on a phone-sized viewport.
- [ ] Verify keyboard navigation for form controls.
- [ ] Verify visible focus states.
- [ ] Verify color contrast for status and warning messages.
- [ ] Verify long URLs and long source titles do not break layout.

### 5.5 Phase Completion Criteria

- [ ] A signed-in user can submit a v2 request from the frontend.
- [ ] The user can watch progress without refreshing.
- [ ] The final response includes usable citations.
- [ ] Expected error states are visible and understandable.
- [ ] The flow works on desktop and mobile.

---

## [ ] Phase 6: Shipping, Feedback, and Portfolio Evidence

**Goal:** Ship the project as a credible personal project with measurable quality and a clear story.

**Primary learning focus:** Release discipline, user feedback, interview readiness.

### 6.1 Release Readiness

- [ ] Run backend tests.
- [ ] Run frontend tests.
- [ ] Run the eval suite.
- [ ] Run the same-input repeatability check.
- [ ] Check logs for noisy warnings.
- [ ] Check production environment variables.
- [ ] Check rate limits and provider quotas.
- [ ] Verify deployment health checks.

### 6.2 User Feedback

- [ ] Recruit ten non-friend users.
- [ ] Give users one clear task to complete.
- [ ] Record where users hesitate.
- [ ] Record which results they trust.
- [ ] Record which results they ignore.
- [ ] Ask whether the source citations are useful.
- [ ] Turn feedback into a prioritized fix list.

### 6.3 Public Project Evidence

- [ ] Add a concise v2 explanation to the project README.
- [ ] Add a dated changelog entry for the v2 rewrite.
- [ ] Add a short architecture summary.
- [ ] Add current eval scores.
- [ ] Add current repeatability result.
- [ ] Add known limitations.
- [ ] Add planned next improvements.

### 6.4 Interview Readiness

- [ ] Memorize the 60-second project pitch.
- [ ] Practice drawing the architecture in two minutes.
- [ ] Prepare one tradeoff you made.
- [ ] Prepare one bug you diagnosed from traces.
- [ ] Prepare one example where evals caught a regression.
- [ ] Prepare one example where you rejected an AI suggestion.
- [ ] Prepare one user feedback story.

### 6.5 Phase Completion Criteria

- [ ] The app is deployed.
- [ ] At least ten users have tried the v2 flow.
- [ ] The README explains what changed and why.
- [ ] Eval and repeatability metrics are documented.
- [ ] You can explain the architecture without reading the code.

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

*Last updated: June 2026*
