# **ScholarSource v2 — Learning Plan**

Goal: Rebuild ScholarSource as a production-style RAG system. Learn RAG, pgvector, embeddings, evals, and LangGraph by writing the code yourself — using AI as a tutor, not a developer.

---

## **The Core Rule**

**You design the module. You write the first version. You ask for review or explanation. You refactor after you understand it.**

This isn't just a learning preference — it's what makes the project defensible in interviews. Per the "Build a Personal Project" doc: if you can't debug a module live in five minutes of questioning, it shouldn't be on your resume. Every piece of this system should be something you can whiteboard from memory.

Where AI helps: explaining concepts, reviewing your code, debugging with you, answering "why does this work this way." Where AI does not help: writing the first version of any module you plan to claim as your own.

---

## **Why This Rewrite (Your 60-Second Pitch)**

Practice this until it's automatic. You'll need it in every interview.

"ScholarSource v1 used CrewAI agents to find study resources, but I ran into a fundamental problem: the same input produced inconsistent results on every run. I diagnosed this as a retrieval problem, not an agent problem. So I rebuilt it from scratch as a controlled RAG pipeline — user input goes through query generation, semantic retrieval from a pgvector store, reranking by relevance, and a final LLM synthesis step. I added evals so any change to the pipeline has to pass a golden test set before it ships. LangGraph handles the workflow orchestration. The result is a system that returns consistent, traceable, explainable results."

---

## 

## **Tech Stack**

| Layer | Tool | Why |
| ----- | ----- | ----- |
| Backend | FastAPI | You already know it. No ramp-up cost. |
| Database | PostgreSQL \+ pgvector via Supabase | You already use Supabase. pgvector is just an extension — no new infrastructure. |
| Embeddings | OpenAI `text-embedding-3-small` or Anthropic | Industry standard. Easy to swap later. |
| LLM | Claude (Anthropic) or GPT-4o | Use what you know. |
| Document loading \+ splitting | LangChain | Best ecosystem for chunking, loaders, and retrieval chains. |
| Retrieval chains | LangChain | Handles the retrieve → format → generate pipeline cleanly. |
| Workflow orchestration | LangGraph | Only added in Phase 4, after the pipeline is stable. |
| Evals | Ragas \+ LangSmith | Ragas measures retrieval and generation quality. LangSmith traces every step. |
| Tracing / Observability | LangSmith | Log every LLM call, retrieval step, and chunk with full input/output. Start day one. |
| Python linting / formatting | Ruff | Fast, modern replacement for the older black + isort + flake8 stack; keeps CI and local validation on one tool. |
| Frontend | React / TypeScript | Unchanged from v1. |
| Hosting | Cloudflare Pages \+ Railway | Unchanged from v1. |
| CI/CD | GitHub Actions | Run evals on every PR. Block merges on regressions. |

---

## **Best Practices From the Two Docs**

### **From Google's Agentic Engineering Paper**

**Agent \= Model \+ Harness.** The model is maybe 10% of what makes an agent work well. The harness — your system prompts, tools, guardrails, retrieval logic, and observability — is 90%. Most agent failures are configuration failures, not model failures. This is why v1 was inconsistent: the harness wasn't doing its job.

**Set up your harness before you write production code.** Before Phase 1, create an `AGENTS.md` file at the root of the repo. Start with 10 lines: your stack, naming conventions, what AI tools are allowed to generate vs. what you write yourself, and hard rules the agent cannot break (e.g., "never return a source without a URL", "always cite chunk source in the response").

**Write evals before you write the agent.** Tests verify deterministic behavior (given this input, return that output). Evals verify non-deterministic behavior (did the agent retrieve relevant sources? is the response grounded in what was retrieved?). A system without evals is always vibe coding, regardless of how clean the code looks.

**Context engineering over prompt engineering.** The quality of your retrieval depends less on clever prompts and more on the quality of what you put in the context window. Good chunking strategy, good metadata on your embeddings, and good retrieval filters matter more than tweaking wording.

**Observability from day one.** LangSmith gives you traces — a full log of every step the system took, with latency and token cost. Start it on day one. This is how you'll diagnose why v1 returned different results: you'll be able to see exactly what the system retrieved and why.

**Start as a "Conductor," not an "Orchestrator."** You want to be in the code, understanding every step, writing the logic yourself. This is the right instinct. The Google doc calls this conductor mode — fine-grained control, real-time understanding. Only move toward orchestrator mode (delegating to agents) in Phase 4, after you deeply understand the non-agentic pipeline.

### **From "Build a Personal Project"**

**The bar has moved.** "I rebuilt ScholarSource" is table stakes. The signal is: "I identified the root cause, rebuilt it with a proper architecture, added evals, shipped it, and here's what I learned." You need the full story, including what changed and why.

**One new skill per phase.** Each phase introduces one primary new concept. Don't try to learn pgvector, LangGraph, and Ragas simultaneously. Master each layer before adding the next.

**Ship past the demo cliff.** After Phase 1 is working, get the app back in front of real users. Auth edge cases, empty states, error states, and mobile layout matter. These are the things AI doesn't help you finish — they require your judgment.

**Track something measurable.** Before you can say the rewrite "improved" the system, you need a number. Pick at least two metrics from day one: eval pass rate (what % of your golden test set passes?) and retrieval latency (how long does a full query take?). Numbers beat adjectives in interviews.

**Keep a public changelog.** A dated "what changed and why" on the GitHub README is one of the most underrated portfolio artifacts. It proves you iterate, and it gives interviewers something concrete to ask about.

**Get 10 non-friend users.** You have a real distribution channel: NSBE Jr families, students you tutor, parent communities. Use them. A real user who reports a bug is worth more than a polished demo.

---

## **Phase 0: Diagnose \+ Foundation (1 week)**

**New skill this phase:** None — this is setup and diagnosis. Understand before you rebuild.

### **Step 1: Diagnose v1's inconsistency**

Before writing a single line of new code, run v1 five times with the same input and log what's different each time. Ask yourself:

* Is the agent making different tool calls each run?  
* Are different search queries being generated?  
* Is the chunking or retrieval varying?  
* Is the LLM just producing different prose from the same retrieved context?

The answer determines where Phase 1 focuses first. If retrieval is already consistent but generation varies, that's a different fix than if retrieval itself is unstable.

### **Step 2: Set up your harness**

Create `AGENTS.md` in the project root. It should define:

* Stack and conventions  
* What you write vs. what AI can generate  
* Hard rules (citation required, no hallucinated URLs, etc.)  
* How modules should be structured

This file is your architectural contract with yourself and with any AI tool you use. Treat it as code — version controlled, reviewed before changes.

### **Step 3: Set up LangSmith**

Sign up at smith.langchain.com (free tier available). Add the environment variables to your FastAPI project. From this point forward, every LLM call is traced automatically. You should be able to see the full input/output of every retrieval step before you've written a single RAG module.

### **Step 4: Write your 60-second pitch and position the project**

Before building, write the positioning statement:

* What ScholarSource v2 is  
* Who it's for  
* What problem it solves  
* What's different from v1  
* What's different from generic AI search

If you can't articulate this in 60 seconds, the scope isn't sharp enough yet.

---

## **Phase 1: Non-Agentic RAG Pipeline (2–3 weeks)**

**New skills this phase:** Embeddings, pgvector, LangChain document loaders and splitters, retrieval chains.

**What you're building:** A controlled, deterministic pipeline that takes a topic or textbook as input and returns ranked, cited study resources — no agents, no unpredictability.

### **The pipeline flow**

User input (topic \+ textbook)  
    → Query generation (LLM call, deterministic settings: temp=0)  
    → Web search / source collection  
    → Page text extraction (LangChain document loaders)  
    → Chunking (LangChain text splitters)  
    → Embedding (OpenAI or Anthropic embeddings API)  
    → Store in pgvector (Supabase)  
    → Semantic retrieval (top-k chunks)  
    → Reranking (score chunks against original query)  
    → LLM synthesis (produce source list with citations)  
    → Return to user

### **What to write yourself (in order)**

1. **The chunking module.** Read the LangChain docs on `RecursiveCharacterTextSplitter`. Write the splitter yourself, choosing chunk size and overlap. Understand why overlap exists and what happens without it.

2. **The embedding function.** Call the OpenAI or Anthropic embeddings API directly first — not through a LangChain abstraction. Understand what an embedding is (a list of floats that represents semantic meaning), what the dimensions are, and how cosine similarity works. Then wrap it in LangChain.

3. **The pgvector schema.** Enable pgvector in Supabase. Write and understand the SQL manually before hiding it behind an ORM or library. The project schema is tracked in `supabase_schema.sql` for fresh databases and `migrations/` for incremental upgrades. The v2 schema must preserve traceability across `rag_sources`, `rag_source_rejections`, `rag_extracted_documents`, `rag_chunks`, `rag_embeddings`, `rag_runs`, and `rag_run_steps`. At minimum, every embedded chunk must carry source URL, title, chunk index, content hash, embedding model, vector dimensions, and timestamps.

4. **The retrieval query.** Write the SQL cosine similarity query by hand before using LangChain's retriever abstraction. You should be able to explain what `<=>` does in pgvector without looking it up.

5. **The reranking step.** After retrieving top-k chunks, score each one against the original query using a second LLM call (or Cohere's rerank API). Return the top 5 reranked results.

6. **The synthesis step.** Pass the top 5 chunks plus the original query to the LLM. System prompt must require citations. This is where your AGENTS.md guardrail ("always cite chunk source") applies.

### **Key settings for determinism**

Set `temperature=0` on every LLM call that should be consistent. Cache page extraction results so the same URL doesn't produce different text on different runs. Use fixed chunk sizes and overlap. Log the chunk IDs retrieved for each query so you can compare runs.

### **Courses to take alongside Phase 1**

* [Building and Evaluating Advanced RAG — DeepLearning.AI](https://www.deeplearning.ai/courses/building-evaluating-advanced-rag) — Take this in week 1 of this phase. It explains chunking strategies and retrieval architecture clearly.  
* [Retrieval Augmented Generation — DeepLearning.AI](https://www.deeplearning.ai/courses/retrieval-augmented-generation) — Go deeper on vector DBs and semantic search after you've built the first version.

---

## **Phase 2: Make It Repeatable (2 weeks)**

**New skill this phase:** Caching, logging, deterministic configuration.

**Goal:** Run the same input 5 times and get the same results every time. If you can't demonstrate this, Phase 1 isn't done.

### **What to build**

**Result caching.** Cache search results by query hash. If you've already fetched and chunked a URL, don't fetch it again — return the stored chunks. Use Redis (Railway makes this easy) or a simple Supabase table keyed by URL hash.

**Embedding deduplication.** Before embedding a chunk, check if an embedding already exists for that content hash. This prevents re-embedding the same text on every run and keeps your pgvector store clean.

**Run logging.** For every query, log: the input, the generated search queries, the chunk IDs retrieved, the reranked order, and the final response. Store this in a Supabase table. This gives you a paper trail to compare runs.

**Diff tool.** Write a simple script that takes two run IDs and diffs the retrieved chunk IDs. This is how you'll prove the system is consistent and how you'll catch regressions.

### **Interview talking point this phase**

"I built a caching layer so the same query always hits stored embeddings rather than re-fetching and re-embedding content. Combined with temperature=0 and deterministic retrieval, the system now returns identical results for identical inputs. I built a run logging table to verify this and catch regressions."

---

## **Phase 3: Evals (2 weeks)**

**New skill this phase:** Ragas, LangSmith eval tracking, GitHub Actions CI gate.

**Write the eval set before you build the eval harness.** This is the Google doc principle: evals are the contract with the AI. They communicate what "correct" means more precisely than any prompt.

### **Build your golden test set first**

Create 20 test cases in a JSON file. Each case has:

* `input`: a topic \+ textbook combination a real student might enter  
* `expected_sources`: at least 2-3 URLs or domains you'd expect to see in a good result  
* `forbidden_sources`: sources that should never appear (paywalled, irrelevant, low quality)  
* `expected_concepts`: key concepts that should appear in the synthesized response

Do this before writing any eval code. Sit down with the app and think about what good looks like for 20 different real student queries.

### **Eval metrics to measure (using Ragas)**

* **Context Precision:** Are the retrieved chunks actually relevant to the query?  
* **Context Recall:** Did the system retrieve all the relevant information that exists?  
* **Answer Groundedness (Faithfulness):** Is the synthesized response supported by the retrieved chunks, or is it hallucinating?  
* **Answer Relevance:** Does the response actually answer what the user asked?

### **Wire evals into GitHub Actions**

Write a GitHub Actions workflow that runs your 20 golden examples on every PR. If the eval scores drop below a threshold (e.g., context precision \< 0.80), the PR fails. This is the agentic engineering practice from the Google doc: "evals run in CI" is what separates a demo from a production-grade system.

### **Courses to take alongside Phase 3**

* [Evaluating AI Agents — DeepLearning.AI](https://www.deeplearning.ai/courses/evaluating-ai-agents) — Take this at the start of Phase 3\.

---

## **Phase 4: LangGraph Orchestration (2–3 weeks)**

**New skill this phase:** LangGraph graph construction, state management, node design.

**Only add LangGraph after your pipeline passes evals.** If you add orchestration on top of a broken retrieval pipeline, you'll spend weeks debugging the wrong layer.

### **What LangGraph adds**

LangGraph turns your linear pipeline into a stateful graph where each step is a node with typed inputs and outputs, and you can add conditional branching, fallbacks, and state that persists across steps.

### **Your graph nodes**

classify\_request  
    → generate\_search\_queries  
    → retrieve\_candidates (pgvector semantic search)  
    → evaluate\_candidates (score each result)  
    → rerank  
    → synthesize\_response  
    → \[fallback if results are weak\]

The fallback node is important and often skipped. If the retrieval step returns fewer than 3 high-quality chunks, the graph should route to a fallback (broaden the query, try alternative sources, or return a transparent "couldn't find enough quality sources" message) rather than synthesizing a weak response.

### **What to write yourself**

Write the graph schema and node function signatures before implementing any node. Define the `State` TypedDict — what fields flow through the graph, what each node reads and writes. This is the architectural decision that matters. The implementations of individual nodes you already have from Phase 1\.

### **Courses to take alongside Phase 4**

* [AI Agents in LangGraph — DeepLearning.AI](https://www.deeplearning.ai/courses/ai-agents-in-langgraph) — Take this before starting Phase 4\.

---

## **Phase 5: Ship Past the Demo Cliff (1–2 weeks)**

**New skill this phase:** None. This is follow-through and polish — the part most developers skip.

Per the "Build a Personal Project" doc: AI gets you to 80% fast, then leaves you alone with the long tail. This phase is that long tail.

### **What "past the demo cliff" means for ScholarSource v2**

* Error states: what happens when a URL can't be fetched? When the LLM returns a malformed response? When pgvector returns no results?  
* Empty states: what does a new user see before they've entered anything?  
* Loading states: the pipeline takes time — show meaningful progress, not a spinner  
* Mobile layout: test it on your phone  
* Rate limiting: prevent abuse of your LLM calls  
* Auth edge cases: session expiry, invalid tokens

### **After you ship**

Get the app in front of 10 non-friend users within the first week. Your NSBE Jr families, students you tutor, and college-bound communities are your distribution channel. Real users surface problems your own testing won't.

Write a visible v1.1 within two weeks of shipping — even a small fix. It proves you iterate.

Start a public changelog on the README. Format: `[date] — what changed and why.`

---

## **Metrics to Track**

Pick these from day one and be able to cite them in interviews:

| Metric | How to measure | Target |
| ----- | ----- | ----- |
| Eval pass rate | Ragas \+ golden test set | \> 80% |
| Retrieval latency | Log in LangSmith, p50 and p95 | p50 \< 3s |
| Run consistency | % of same-input runs returning same top-3 chunk IDs | 100% |
| Weekly active users | Supabase analytics | Growing |

---

## **Interview Prep: What You Need to Be Able to Say**

Per the "Build a Personal Project" doc — the conversation is the artifact. Assume the interviewer won't open the link.

**60-second pitch** (already written above — memorize it)

**Architecture in 2 minutes:** Be able to draw this on a whiteboard from memory: user input → query generation → pgvector semantic retrieval → reranking → LangGraph orchestration → LLM synthesis → response with citations. Know what every arrow means.

**A real tradeoff you made:** "I chose pgvector over Qdrant because I already use Supabase and didn't need to manage a separate vector DB at this scale. If I needed filtered search across millions of embeddings with complex metadata, I'd evaluate Qdrant."

**A moment you overrode the AI:** Have one ready. "When I wrote the reranking step, Claude suggested using cross-encoder reranking with a HuggingFace model. I overrode it and used a second LLM call instead because I didn't want to add a local model inference dependency to the Railway deployment."

**Your AI usage answer:** "I used Claude to explain concepts like cosine similarity and to review my chunking module after I wrote the first version. I wrote the pgvector schema, retrieval query, and LangGraph graph structure myself — those are the pieces where understanding the implementation matters for debugging."

**What you learned from users:** Have a specific example. "A student told them the results were good but they didn't know which sources to trust. That feedback drove the reranking feature — we now score sources by domain authority and show a quality indicator."

**What's next:** "I'd add a feedback loop — when a user marks a result as helpful or not, that signal feeds back into how we weight sources in retrieval. Long term I'd evaluate Qdrant for filtered search across a larger corpus."

**Evals answer:** "I have 20 golden examples. Any change to the retrieval pipeline or system prompt has to pass a Ragas eval suite in CI before it merges. Context precision is my primary metric — currently at \[X\]%."

---

## **Recommended Course Sequence**

Take these alongside the phases they map to, not all at once upfront.

| Phase | Course |
| ----- | ----- |
| Phase 1 | [Building and Evaluating Advanced RAG — DeepLearning.AI](https://www.deeplearning.ai/courses/building-evaluating-advanced-rag) |
| Phase 1 (deeper) | [Retrieval Augmented Generation — DeepLearning.AI](https://www.deeplearning.ai/courses/retrieval-augmented-generation) |
| Phase 3 | [Evaluating AI Agents — DeepLearning.AI](https://www.deeplearning.ai/courses/evaluating-ai-agents) |
| Phase 4 | [AI Agents in LangGraph — DeepLearning.AI](https://www.deeplearning.ai/courses/ai-agents-in-langgraph) |
| Optional (paid, comprehensive) | [IBM RAG and Agentic AI Professional Certificate — Coursera](https://www.coursera.org/professional-certificates/ibm-rag-and-agentic-ai) |

---

## **Timeline Summary**

| Phase | Duration | Primary New Skill |
| ----- | ----- | ----- |
| Phase 0: Diagnose \+ Foundation | 1 week | None — setup and diagnosis |
| Phase 1: Non-Agentic RAG Pipeline | 2–3 weeks | Embeddings, pgvector, LangChain |
| Phase 2: Make It Repeatable | 2 weeks | Caching, logging, determinism |
| Phase 3: Evals | 2 weeks | Ragas, LangSmith, CI evals |
| Phase 4: LangGraph | 2–3 weeks | Graph orchestration, state management |
| Phase 5: Ship Past Demo Cliff | 1–2 weeks | Follow-through, real users |
| **Total** | **10–13 weeks** |  |

---

*Last updated: June 2026*
