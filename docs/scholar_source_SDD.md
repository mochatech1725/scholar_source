# ScholarSource System Design Document

## Document Control

| Field | Value |
|-------|-------|
| **Document Title** | ScholarSource System Design Document |
| **Version** | 1.0 |
| **Date** | December 2024 |
| **Author** | ScholarSource Development Team |
| **Status** | Approved |

---

## Table of Contents

1. [Project Description](#1-project-description)
2. [Overview](#2-overview)
3. [System Architecture](#3-system-architecture)
4. [Application Domain Design](#4-application-domain-design)
5. [Data Design](#5-data-design)
6. [User Interface Design](#6-user-interface-design)
7. [External Interfaces](#7-external-interfaces)
8. [Design Decisions and Rationale](#8-design-decisions-and-rationale)
9. [Assumptions and Constraints](#9-assumptions-and-constraints)
10. [Security Design](#10-security-design)
11. [Future Improvements and Features](#11-future-improvements-and-features)
12. [Glossary](#12-glossary)
13. [References](#13-references)

---

## 1. Project Description

### 1.1 Project

**Project Name:** ScholarSource

### 1.2 Description

ScholarSource is a web application that helps students discover curated educational resources aligned with their course textbooks. The system was created to address a critical need: students often struggle to find reputable, high-quality resources to supplement their textbook learning and generate effective study materials.

**Problem Statement:**

Students need reliable, legally accessible educational resources that align with their specific textbooks to create quality study materials. However, finding such resources is time-consuming and challenging, as students must:
- Manually search across multiple platforms
- Verify resource quality and legality
- Ensure resources match their textbook's structure and topics
- Validate that resources are suitable for study material generation

**Solution Approach:**

ScholarSource automates this process by:
1. **Analyzing textbook structure** - Extracts topics, concepts, and organization from course materials or book metadata
2. **Discovering aligned resources** - Searches for 5-7 high-quality, legally accessible resources that match the textbook's content structure
3. **Validating quality** - Ensures resources are free, legal, NotebookLM-compatible, and from reputable sources
4. **Enabling study material generation** - Provides resources ready to import into Google NotebookLM

**NotebookLM Integration:**

Using NotebookLM gives students a sanitized way to ensure their study materials are valid. ScholarSource provides discovered resources that students manually import into NotebookLM, which then processes them to generate study guides, flashcards, and practice tests. This workflow ensures students work with legitimate, high-quality educational content.

### 1.3 Revision History

| Date | Version | Comment | Author |
|------|---------|---------|--------|
| December 2024 | 1.0 | Initial System Design Document | Development Team |

---

## 2. Overview

### 2.1 Purpose

This System Design Document (SDD) describes the high-level architecture and design rationale for ScholarSource. It focuses on **why** architectural and design decisions were made, rather than **how** they are implemented. This document is intended for architects, senior engineers, product managers, and stakeholders who need to understand the system's design philosophy, trade-offs, and evolution path.

**For detailed implementation specifications, see `scholar_source_TDD.md`.**

### 2.2 Scope

This document covers:
- Overall system architecture and decomposition
- Architectural decisions and their rationale
- High-level component design and interactions
- Data architecture and storage decisions
- External interface design decisions
- Design trade-offs and alternatives considered
- Security architecture
- Scalability and performance considerations

This document does **not** cover:
- Detailed function signatures and algorithms (see Technical Design Document)
- Implementation code specifics
- Deployment procedures (see Deployment Plan)
- Testing procedures (see Testing Guide)

### 2.3 Requirements Overview

The system must satisfy the following high-level requirements:

| Requirement | Description | Priority |
|-------------|-------------|----------|
| R1 | Automatically discover educational resources aligned with textbook content | High |
| R2 | Validate resource quality, legality, and NotebookLM compatibility | High |
| R3 | Support multiple input types (course URLs, book metadata, ISBNs) | High |
| R4 | Provide real-time job status updates | High |
| R5 | Persist job state across server restarts | High |
| R6 | Prevent abuse through rate limiting | Medium |
| R7 | Cache results to reduce redundant AI operations | Medium |

For detailed requirements traceability, see Section 2.3.2.

### 2.3.1 High-Level Estimates

| Component | Description | Complexity |
|-----------|-------------|------------|
| Frontend | React SPA with form, polling, results display | Medium |
| Backend API | FastAPI REST endpoints with job management | Medium |
| CrewAI Integration | Multi-agent orchestration for resource discovery | High |
| Database Schema | Job persistence and caching | Low |
| Caching System | Two-tier caching with config-based invalidation | Medium |

### 2.3.2 Requirements Traceability

| Requirement | Design Section | Status |
|-------------|----------------|--------|
| R1 | Section 4.2.3 (CrewAI Domain) | ✅ Implemented |
| R2 | Section 4.2.3 (CrewAI Domain) | ✅ Implemented |
| R3 | Section 6 (UI Design) | ✅ Implemented |
| R4 | Section 4.2.1 (Frontend Domain) | ✅ Implemented |
| R5 | Section 5 (Data Design) | ✅ Implemented |
| R6 | Section 8.4 (Rate Limiting Decision) | ✅ Implemented |
| R7 | Section 8.3 (Caching Strategy) | ✅ Implemented |

---

## 3. System Architecture

### 3.1 Architecture Overview

ScholarSource follows a **layered architecture** with clear separation between presentation, application, data, and external service layers. The system uses a **distributed task queue architecture** with separate API and worker processes, enabling independent scaling and fault isolation.

**High-Level Architecture Diagram:**

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                             │
│  React + Vite Frontend (Cloudflare Pages)                  │
│  - Stateless SPA architecture                              │
│  - Client-side polling for status updates                  │
│  - No server-side rendering required                       │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS/REST API
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                   API LAYER                                 │
│  FastAPI Backend (Railway - Backend Service)               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ - RESTful API endpoints                              │  │
│  │ - Request validation and rate limiting               │  │
│  │ - JOB MANAGER (backend/jobs.py)                     │  │
│  │   • create_job(), get_job(), update_job_status()    │  │
│  │ - CREW RUNNER (backend/crew_runner.py)               │  │
│  │   • run_crew_async() - Enqueues jobs to Celery      │  │
│  └──────────────────────────────────────────────────────┘  │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ Enqueue jobs to Celery queue
       │
┌──────▼──────────────────────────────────────────────────────┐
│              TASK QUEUE LAYER                               │
│  Redis (Celery Message Broker)                             │
│  - Celery task queue (stores enqueued jobs)                │
│  - Rate limit state (shared across API instances)         │
│  - Result backend (optional task results)                  │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ Workers consume jobs from queue
       │
┌──────▼──────────────────────────────────────────────────────┐
│              WORKER LAYER                                   │
│  Celery Worker Processes (Railway - Celery Service)         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ - CREW RUNNER Execution (backend/tasks.py)          │  │
│  │   • run_crew_task() - Executes CrewAI jobs          │  │
│  │   • Runs CrewAI orchestration                        │  │
│  │   • Updates job status via JOB MANAGER              │  │
│  │ - Process isolation (separate from API)              │  │
│  │ - Can scale independently                             │  │
│  └──────────────────────────────────────────────────────┘  │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ Job status updates
       │
┌──────▼──────────────────────────────────────────────────────┐
│              DATABASE LAYER                                 │
│  Supabase PostgreSQL                                        │
│  - Job persistence (via JOB MANAGER)                        │
│  - Result caching                                           │
└──────┬──────────────────────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────────────┐
│              EXTERNAL SERVICES                              │
│  - OpenAI API (LLM inference)                              │
│  - Serper API (web search)                                 │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 Architectural Style

The system employs a **RESTful API architecture** with **distributed task queue processing**:

- **Stateless communication** - Each request contains all necessary information
- **Resource-based URLs** - Endpoints represent resources (jobs, status)
- **JSON data exchange** - Standard format for request/response payloads
- **Distributed task queue** - Jobs are enqueued to Celery/Redis and executed by separate worker processes
- **Process isolation** - API and worker processes run independently, enabling independent scaling
- **Asynchronous job processing** - Long-running operations execute in background worker processes
- **Polling-based status updates** - Frontend polls for job status (trade-off: simplicity vs. real-time)

### 3.3 System Decomposition

The system is decomposed into seven major domains:

1. **Frontend Domain** - React/Vite single-page application
2. **Backend Domain** - FastAPI REST API server (handles job submission and status)
3. **Task Queue Domain** - Redis/Celery message broker (enqueues and distributes jobs)
4. **Worker Domain** - Celery service creates separate processes that execute CrewAI jobs asynchronously (can scale independently of API)
5. **CrewAI Domain** - Multi-agent orchestration framework (runs within workers)
6. **Database Domain** - Supabase PostgreSQL persistence layer
7. **Caching Domain** - Two-tier caching system

See Section 4 for detailed domain descriptions.

---

## 4. Application Domain Design

### 4.1 Application Domain Overview

The system is organized into five primary domains, each with distinct responsibilities and clear interfaces between them.

**Domain Interaction Flow:**

```
Frontend Domain
    │
    ├─→ API Requests ─→ Backend Domain
    │                       │
    │                       ├─→ Job Management ─→ Database Domain
    │                       │
    │                       └─→ Crew Execution ─→ CrewAI Domain
    │                                               │
    │                                               └─→ External APIs
    │
    └─→ Status Polling ←── Job Status ←── Database Domain
```

### 4.2 Domain Descriptions

#### 4.2.1 Frontend Domain (React/Vite)

**Purpose:** Provide user interface for resource discovery workflow.

**Architectural Decision:** Single-Page Application (SPA) architecture chosen over Server-Side Rendering (SSR).

**Rationale:**
- ✅ **Simplicity** - No SSR infrastructure needed (no Next.js complexity)
- ✅ **Fast development** - Vite provides instant hot reload
- ✅ **Easy deployment** - Static files on Cloudflare Pages (free tier)
- ✅ **No server state** - Stateless frontend simplifies scaling
- ❌ **Trade-off:** Initial page load slightly slower than SSR (acceptable for this use case)

**Key Components:**
- HomePage (main container, state management, inline form handling)
- ResultsTable (display, filtering, sorting)
- Status polling (client-side, 2-second intervals)

**State Management Approach:**
- React hooks (`useState`, `useEffect`) - No global state management library
- **Rationale:** Component tree is shallow, state flow is unidirectional, no need for Redux/Zustand complexity

#### 4.2.2 Backend Domain (FastAPI/Python)

**Purpose:** Provide REST API for job submission, status tracking, and result retrieval.

**Architectural Decision:** FastAPI framework chosen over Flask/Django.

**Rationale:**
- ✅ **Performance** - Fast request handling (async support)
- ✅ **Type safety** - Pydantic models provide runtime validation
- ✅ **API documentation** - Automatic OpenAPI/Swagger docs
- ✅ **Modern Python** - Async/await support for I/O-bound operations
- ✅ **Simple deployment** - Works well with Railway (no WSGI configuration needed)

**Key Responsibilities:**
- Request validation (Pydantic models)
- Job lifecycle management
- Rate limiting enforcement
- CORS handling
- Error handling and logging

#### 4.2.3 CrewAI Domain (Multi-Agent System)

**Purpose:** Orchestrate AI agents to discover and validate educational resources.

**Architectural Decision:** Multi-agent sequential workflow chosen over single-agent or parallel execution.

**Rationale:**
- ✅ **Specialization** - Each agent has focused responsibility (analysis, discovery, validation, formatting)
- ✅ **Quality** - Validation step ensures resource quality before final output
- ✅ **Modularity** - Agents can be independently improved/configured
- ✅ **CrewAI Framework** - Proven multi-agent orchestration framework
- ❌ **Trade-off:** Sequential execution is slower than parallel, but ensures data quality

**Agent Architecture:**
1. **course_intelligence_agent** - Extracts textbook info and topics
2. **resource_discovery_agent** - Searches for aligned resources
3. **resource_validator_agent** - Validates quality and legality
4. **output_formatter_agent** - Formats results for presentation

**External Dependencies:**
- OpenAI API (GPT-4o, GPT-4o-mini)
- Serper API (web search)

#### 4.2.4 Database Domain (Supabase PostgreSQL)

**Purpose:** Persist job state and cache analysis results.

**Architectural Decision:** Supabase PostgreSQL chosen over Railway PostgreSQL or other databases.

**Rationale:**
- ✅ **Free tier available** - Suitable for MVP
- ✅ **Better tooling** - Dashboard, SQL editor, better UX than Railway DB
- ✅ **Independent scaling** - Database scales separately from backend
- ✅ **Built-in auth** - Ready for future user authentication
- ✅ **Row Level Security** - Fine-grained access control when needed
- ❌ **Trade-off:** External service dependency (acceptable risk)

**Data Storage Strategy:**
- **Jobs table** - Job state, inputs, results (persistent)
- **Course cache table** - Cached analysis and results (TTL-based expiration)

#### 4.2.5 Caching Domain

**Purpose:** Reduce redundant AI operations and improve response times.

**Architectural Decision:** Database-backed caching chosen over Redis or in-memory caching.

**Rationale:**
- ✅ **No additional infrastructure** - Uses existing Supabase database
- ✅ **Persistent across restarts** - Survives server deployments
- ✅ **Simple TTL logic** - Timestamp-based expiration
- ✅ **Config-based invalidation** - Automatic cache invalidation when agent configs change
- ❌ **Trade-off:** Slower than Redis, but acceptable for current scale

**Caching Strategy:**
- **Two-tier approach:**
  - Analysis cache (30-day TTL) - Textbook extraction, topics
  - Full results cache (7-day TTL) - Complete resource discovery results

**Cache Invalidation:**
- Time-based (TTL expiration)
- Config-based (automatic when agents.yaml or tasks.yaml changes)
- Manual (user can bypass cache)

**Cache Maintenance:**
- Periodic cleanup of stale entries via `clear_cache_for_config_change()` function
- Cache statistics monitoring via `get_cache_stats()` function
- Stale cache entries are automatically ignored (config hash mismatch)
- Manual cleanup script recommended for production (see Section 9.3 Maintenance)

---

## 5. Data Design

### 5.1 Data Architecture Overview

The system uses a **relational database** (PostgreSQL) with JSONB fields for flexible schema evolution. Data is organized into two primary tables: `jobs` (transactional data) and `course_cache` (cache data).

### 5.2 Persistent Data Design

#### 5.2.1 Jobs Table

**Purpose:** Store job state, inputs, and results for the resource discovery workflow.

**Design Rationale:**
- **UUID primary key** - Globally unique, no collisions in distributed systems
- **Status enum** - Enforces valid state transitions (pending → running → completed/failed)
- **JSONB fields** - Flexible schema for inputs/results (allows evolution without migrations)
- **Timestamps** - Track job lifecycle (created_at, completed_at)

**Data Flow:**
1. Job created with `status='pending'`, `inputs` populated
2. Status updated to `status='running'` when crew starts
3. Status updated to `status='completed'` with `results`, `raw_output`, `metadata`
4. Or status updated to `status='failed'` with `error` message

#### 5.2.2 Course Cache Table

**Purpose:** Cache expensive AI operations (course analysis and resource discovery results).

**Design Rationale:**
- **TEXT primary key** - Cache key is deterministic hash (no collisions)
- **Config hash** - Enables automatic invalidation when configurations change
- **Cache type** - Distinguishes analysis cache from full results cache (different TTLs)
- **TTL-based expiration** - Timestamp comparison for expiration logic

**Cache Key Strategy:**
- Includes input parameters (course_url, book info, topics, etc.)
- Includes config hash (agents.yaml + tasks.yaml)
- SHA256 hash for deterministic, collision-resistant keys

### 5.3 Transient Data

**In-Memory Data:**
- Rate limit counters (single instance) or Redis counters (multi-instance)
- Active crew execution state (thread-local)
- Request context (FastAPI request state)

---

## 6. User Interface Design

### 6.1 UI Architecture Overview

The user interface follows a **single-page application** pattern with client-side routing and state management.

**Design Principles:**
- **Progressive disclosure** - Collapsible sections for advanced options
- **Real-time feedback** - Status polling shows job progress
- **Error resilience** - Clear error messages with actionable guidance
- **Mobile-responsive** - Adapts to different screen sizes

### 6.2 User Flow

**Primary Workflow:**
1. **Landing** - User sees hero section and search form
2. **Input** - User selects search type and fills relevant fields
3. **Submission** - User submits form, job created, job ID received
4. **Polling** - Frontend polls status every 2 seconds
5. **Results** - Results displayed with filtering and actions
6. **Export** - User copies URLs for NotebookLM import

**Error Handling:**
- Form validation errors displayed inline
- API errors displayed with user-friendly messages
- Network errors trigger retry logic
- Job failures show detailed error messages

### 6.3 UI Component Architecture

**Component Hierarchy:**
```
HomePage (container)
├── Hero (intro section)
├── Search Form (inline in HomePage)
│   ├── Search type selector
│   ├── Input fields (conditional display)
│   ├── Optional accordions (Resource Types, Focus Topics, Exclude Sites, Target Sites)
│   └── Submit/reset buttons
├── InlineSearchStatus (polling display)
└── ResultsTable (results display)
    ├── Filter controls
    ├── Resource cards
    └── Action buttons (copy, NotebookLM)
```

---

## 7. External Interfaces

### 7.1 External Service Interfaces

#### 7.1.1 OpenAI API

**Purpose:** LLM inference for AI agents (GPT-4o, GPT-4o-mini).

**Interface Type:** REST API (OpenAI Python SDK wrapper).

**Authentication:** API key via environment variable.

**Design Decision:** Use OpenAI SDK rather than direct REST calls.

**Rationale:**
- ✅ **Abstraction** - SDK handles authentication, retries, rate limits
- ✅ **Type safety** - SDK provides type hints
- ✅ **Error handling** - SDK provides structured error responses
- ✅ **Future-proof** - Easy to switch to other providers if needed

#### 7.1.2 Serper API

**Purpose:** Web search for resource discovery and validation.

**Interface Type:** REST API.

**Authentication:** API key via environment variable.

**Design Decision:** Use Serper API rather than Google Custom Search or Bing API.

**Rationale:**
- ✅ **Cost-effective** - Lower cost than Google Custom Search
- ✅ **Simple API** - Clean, easy-to-use interface
- ✅ **Good results** - Quality search results for educational content
- ✅ **Rate limits** - Reasonable limits for MVP scale

#### 7.1.3 Supabase API

**Purpose:** Database operations (job CRUD, cache operations).

**Interface Type:** PostgreSQL via Supabase Python client.

**Authentication:** Project URL and anon key via environment variables.

**Design Decision:** Use Supabase client library rather than raw psycopg2.

**Rationale:**
- ✅ **Abstraction** - Client handles connection pooling, retries
- ✅ **Type safety** - Client provides type hints for responses
- ✅ **Row Level Security** - Client respects RLS policies
- ✅ **Future features** - Easy to add auth, real-time, storage features

### 7.2 NotebookLM Integration

**Design Decision:** Manual import workflow (no programmatic notebook creation).

**Rationale:**
- **NotebookLM Enterprise API required** - Programmatic notebook creation only available in paid/enterprise tier
- **Target user base** - ScholarSource targets free NotebookLM tier used by students
- **Manual import is sufficient** - One additional user step is acceptable trade-off
- **No API dependency** - Reduces complexity, eliminates API availability risk

**Implementation:**
- Frontend provides "Copy + NotebookLM" button
- Opens NotebookLM in new tab
- Users manually paste resource URLs
- No backend integration with NotebookLM API

---

## 8. Design Decisions and Rationale

This section documents major architectural and design decisions, alternatives considered, and the rationale for choices made.

### 8.1 Background Job Execution

**Decision:** Use Celery with Redis for distributed task queue processing.

**Rationale:**
- ✅ **Horizontal Scalability** - Can scale API and worker instances independently
- ✅ **Process Isolation** - Worker crashes don't affect API availability
- ✅ **Fault Tolerance** - Jobs persist in Redis queue, can be retried if worker fails
- ✅ **Task Distribution** - Jobs automatically distributed across available workers
- ✅ **Production Ready** - Industry-standard solution for background job processing

**Implementation:**
- **Celery** - Distributed task queue library
- **Redis** - Message broker and task queue storage
- **Separate Services** - API (FastAPI) and Workers (Celery) run as separate Railway services
- **Job Persistence** - Job status stored in Supabase, tasks queued in Redis

**Alternatives Considered:**
- **Python Threading** - Initial implementation, limited scalability (migrated away from this)
- **AWS SQS / Google Cloud Tasks** - Vendor lock-in, more complex setup
- **RQ (Redis Queue)** - Simpler but less features than Celery

**Trade-offs:**
- ✅ Enables horizontal scaling of both API and workers
- ✅ Process isolation improves reliability
- ✅ Jobs can be retried and distributed across workers
- ❌ Additional infrastructure (Redis required)
- ❌ More complex deployment (separate services)
- ❌ Slightly higher operational overhead

**Current Architecture:**
- API Layer: FastAPI service on Railway (handles job submission, enqueues to Celery)
- Task Queue: Redis (stores enqueued jobs, shared rate limit state)
- Worker Layer: Celery worker service on Railway (consumes jobs from Redis, executes CrewAI tasks)
- Database: Supabase (stores job status and results)

**Migration Status:**
- ✅ **Completed** - Migrated from threading-based to Celery-based architecture
- ✅ **Completed** - Separate API and Worker services deployed on Railway
- ✅ **Completed** - Redis integration for task queue and rate limiting

### 8.2 Database Choice

**Decision:** Supabase PostgreSQL (standalone, not Railway add-on).

**Rationale:**
- ✅ **Free tier available** - Suitable for MVP
- ✅ **Better tooling** - Dashboard, SQL editor, better UX than Railway DB
- ✅ **Built-in auth** - Ready for future user authentication features
- ✅ **Independent scaling** - Database scales separately from backend
- ✅ **Row Level Security** - Fine-grained access control when needed

**Alternatives Considered:**
- **Railway PostgreSQL** - More expensive, less tooling
- **SQLite** - Not suitable for production (no concurrency, no network access)
- **MongoDB** - Overkill, relational data fits better (jobs have structured schema)

**Trade-offs:**
- ✅ Better developer experience and tooling
- ✅ Lower cost (free tier)
- ❌ External service dependency (acceptable risk)

### 8.3 Caching Strategy

**Decision:** Database-backed caching in Supabase (no Redis).

**Rationale:**
- ✅ **No additional infrastructure** - Uses existing Supabase database
- ✅ **Persistent across restarts** - Survives server deployments
- ✅ **Simple TTL logic** - Timestamp-based expiration
- ✅ **Config-based invalidation** - Automatic when agent configs change
- ✅ **Sufficient performance** - Database queries are fast enough for cache lookups

**Alternatives Considered:**
- **Redis** - Faster but adds infrastructure and cost
- **In-memory caching** - Lost on restart, not suitable for production
- **CDN caching** - Not applicable for dynamic API responses

**Trade-offs:**
- ✅ Simpler architecture (no Redis to manage)
- ✅ Persistent (survives restarts)
- ❌ Slower than Redis (acceptable for current scale)
- ❌ Database load for cache operations (minimal impact)

**Future Evolution Path:**
- Migrate to Redis if cache performance becomes bottleneck
- Or implement hybrid approach (Redis for hot data, DB for persistence)

### 8.4 Rate Limiting

**Decision:** slowapi with in-memory storage (single instance) or Redis (multi-instance).

**Rationale:**
- ✅ **Flexible** - Works with or without Redis
- ✅ **Simple implementation** - Decorator-based API
- ✅ **Good enough for current scale** - Single instance sufficient
- ✅ **Easy migration** - Just set REDIS_URL env var when scaling

**Alternatives Considered:**
- **Nginx rate limiting** - Requires reverse proxy, more complex
- **Cloudflare rate limiting** - Adds external dependency, costs money

**Trade-offs:**
- ✅ Simple implementation (decorator-based)
- ✅ No additional infrastructure for single instance
- ❌ In-memory limits reset on deploy (acceptable risk)
- ❌ Must migrate to Redis before scaling to multiple instances

**Critical Constraint:**
- ⚠️ **In-memory rate limiting ONLY works for single-instance deployments**
- ⚠️ **MUST migrate to Redis BEFORE scaling to 2+ instances**

### 8.5 Frontend Framework

**Decision:** React + Vite (not Next.js, not Svelte).

**Rationale:**
- ✅ **Fast development** - Vite provides instant hot reload
- ✅ **Simple SPA** - No SSR needed for this use case
- ✅ **Good component ecosystem** - Large React ecosystem
- ✅ **Easy deployment** - Static files on Cloudflare Pages (free tier)
- ✅ **Team familiarity** - React is widely known

**Alternatives Considered:**
- **Next.js** - SSR not needed, adds complexity and deployment requirements
- **Svelte** - Smaller bundle size, but smaller ecosystem
- **Vue** - Similar to React, but React has larger ecosystem

**Trade-offs:**
- ✅ Fast development experience
- ✅ Simple deployment (static files)
- ❌ Larger bundle size than Svelte (acceptable)

### 8.6 Status Update Mechanism

**Decision:** Client-side polling (2-second intervals) instead of WebSockets or Server-Sent Events.

**Rationale:**
- ✅ **Simplicity** - No WebSocket infrastructure needed
- ✅ **HTTP-only** - Works behind any proxy/firewall
- ✅ **Easy error handling** - Standard HTTP error codes
- ✅ **Sufficient for use case** - 2-second updates are acceptable
- ✅ **Stateless** - Each poll is independent request

**Alternatives Considered:**
- **WebSockets** - Real-time updates but adds complexity (connection management, reconnection logic)
- **Server-Sent Events (SSE)** - Simpler than WebSockets but still requires connection management

**Trade-offs:**
- ✅ Simpler implementation and deployment
- ✅ Works with standard HTTP infrastructure
- ❌ Slightly higher server load (acceptable for current scale)
- ❌ 2-second delay (acceptable for this use case)

**Future Evolution Path:**
- Migrate to WebSockets if real-time updates become critical
- Or use SSE for simpler real-time updates

---

## 9. Assumptions and Constraints

### 9.1 Assumptions

#### 9.1.1 Deployment Assumptions

1. **Single Instance Deployment (Initial)**
   - Assumes single Railway instance (not horizontally scaled)
   - Rate limiting uses in-memory storage
   - Background jobs run in same process

2. **Job Duration**
   - Jobs complete within 2-5 minutes
   - No timeout handling needed initially
   - Railway doesn't kill long-running processes

3. **User Behavior**
   - Users poll status every 2 seconds
   - Users don't submit duplicate requests rapidly
   - Rate limits are sufficient (10/hour, 2/minute)

#### 9.1.2 External Service Assumptions

1. **API Availability**
   - OpenAI API is available and reliable
   - Serper API is available and reliable
   - API keys are valid and have sufficient quota

2. **Data Volume**
   - Moderate number of concurrent jobs (< 10)
   - Cache size manageable (< 1GB)
   - Database size manageable (Supabase free tier sufficient)

#### 9.1.3 User Assumptions

1. **NotebookLM Usage**
   - Users have access to free NotebookLM tier
   - Users are comfortable with manual URL import
   - Users understand the manual import workflow

### 9.2 Constraints

#### 9.2.1 Technical Constraints

1. **NotebookLM API Limitation**
   - No programmatic notebook creation (Enterprise API required)
   - Must use manual import workflow
   - Constraint drives UI design (copy buttons, clear instructions)

2. **Single Instance Constraint**
   - Rate limiting uses in-memory storage (single instance only)
   - Must migrate to Redis before horizontal scaling
   - Background jobs run in same process (no distributed execution)

3. **Database Constraints**
   - Supabase free tier limits (500MB database, 500K API requests/month)
   - Must monitor usage and upgrade if needed

#### 9.2.2 Business Constraints

1. **Cost Constraints**
   - OpenAI API costs per job (GPT-4o is expensive)
   - Must optimize token usage (use GPT-4o-mini for some agents)
   - Must implement caching to reduce redundant operations

2. **Time Constraints**
   - Jobs take 2-5 minutes (AI operations are slow)
   - Users must wait for results (background job pattern)
   - Status polling provides feedback during wait

### 9.3 Maintenance and Operations

#### 9.3.1 Cache Maintenance

**Periodic Cleanup:**
- Stale cache entries accumulate when configuration files (`agents.yaml`, `tasks.yaml`) are modified
- The `clear_cache_for_config_change()` function removes entries with mismatched config hashes
- Recommended: Run cleanup script periodically (e.g., weekly cron job or scheduled task)
- Script name: `scripts/clear_cache.py` (to be implemented)

**Cache Monitoring:**
- Use `get_cache_stats()` function to monitor cache health
- Track valid vs stale entries
- Monitor cache hit rates (if implemented)
- Check average cache age to identify optimization opportunities

---

## 10. Security Design

### 10.1 Security Architecture Overview

The system follows a **defense-in-depth** strategy with multiple layers of security controls.

### 10.2 Authentication and Authorization

**Current State:**
- **No user authentication** - Public access (MVP)
- **Row Level Security (RLS)** - Enabled but permissive policy
- **API keys** - Stored in environment variables (never in code)

**Future State:**
- Add user authentication (Supabase Auth)
- Restrict RLS policies to user-owned data
- API key rotation strategy

**Design Rationale:**
- MVP focuses on core functionality (resource discovery)
- Authentication adds complexity (can be added later)
- RLS provides foundation for future access control

### 10.3 Data Security

**API Keys:**
- Stored in environment variables (never in code)
- Never exposed to frontend
- Rotated periodically (future enhancement)

**Database:**
- Supabase connection uses HTTPS
- RLS policies prevent unauthorized access (when configured)
- Anon key used (read-only for public data)

**Input Validation:**
- Pydantic models validate all inputs
- SQL injection prevented by parameterized queries (Supabase client)
- XSS prevented by React's automatic escaping

### 10.4 Rate Limiting

**Purpose:** Prevent abuse and API cost overruns.

**Implementation:**
- IP-based rate limiting (10/hour, 2/minute on submit)
- Protects against DDoS (basic level)
- Prevents API cost overruns

**Limitations:**
- IP-based limits can affect shared networks (dorms, libraries)
- VPN evasion possible (acceptable risk for MVP)
- Consider per-user limits when authentication is added

### 10.5 CORS Protection

**Configuration:**
- Whitelist of allowed origins
- Credentials allowed (for future auth)
- Specific methods (GET, POST, OPTIONS)

**Security:**
- Prevents unauthorized frontend access
- Only Cloudflare Pages and localhost allowed

### 10.6 CSRF Protection

**Current Implementation:**
- Origin header validation on state-changing POST requests
- Validates requests come from allowed origins
- Applied to `/api/submit` and `/api/cancel/{job_id}` endpoints

**Rationale:**
- Traditional CSRF attacks exploit cookie-based sessions
- Since ScholarSource has no authentication/sessions, traditional CSRF isn't a risk
- Origin validation provides defense-in-depth against cross-origin POST requests

**Future Considerations:**
- When authentication is added, implement CSRF tokens (synchronizer token pattern)
- Add SameSite cookie attributes for auth cookies

---

## 11. Future Improvements and Features

### 11.1 Future Improvements

**Cache System Enhancements:**
- [ ] Test force refresh functionality
- [ ] Test config invalidation
- [ ] Test cache stats function
- [ ] Verify TTL expiration works correctly
- [ ] Add metrics/monitoring for cache performance
- [ ] Implement cache cleanup job (remove expired entries)
- [ ] Consider implementing Option B (individual task execution) for better performance

**Performance Optimizations:**
- Migrate to Redis for cache storage if database-backed caching becomes a bottleneck
- Implement horizontal scaling with distributed rate limiting
- Optimize crew execution to run tasks individually when cache is available
- Add response caching headers for static resources (CSS, JS)
- Optimize frontend bundle size (code splitting, lazy loading components)
- Implement database query optimization (indexes for frequently queried fields)

**Monitoring and Observability:**
- Add comprehensive metrics collection for cache hit rates
- Implement performance monitoring dashboards
- Add alerting for cache health and performance degradation
- Implement application metrics (job completion rates, API response times, error counts)
- Add error tracking (Sentry integration, exception capture, alerting)
- Improve health check endpoint (database connectivity, external API availability)

**Error Handling Strategy:**
- Add network error detection and user-friendly messages (distinguish network timeout vs server error)
- Implement retry logic with exponential backoff for transient network errors (503, 502, timeouts)
- Categorize and improve job failure error messages (OpenAI API errors vs network vs validation)
- Add rate limiting detection and handling (429 responses, wait time display, auto-retry)
- Add empty results handling with helpful suggestions (explain why no resources found, suggest improvements)

**Job Management:**
- Implement job deletion/cleanup (automatic or manual)
- Add job expiration policies (auto-delete after 30/60/90 days)

**Performance Optimizations:**
- Add response caching headers for static resources
- Optimize frontend bundle size (code splitting, lazy loading)
- Implement database query optimization (indexes for frequently queried fields)

### 11.2 Future Features

**User Experience Enhancements:**
- Add ability to email results to users
- Implement user authentication and personalized job history
  - User registration and login
  - JWT token management
  - Password reset flow
  - OAuth integration (Google, GitHub)
- Add ability to save favorite resources

**Advanced Functionality:**
- Add batch processing for multiple courses
- Implement scheduled job execution
- Add export functionality (CSV, JSON formats)
- Integrate with NotebookLM Enterprise API when available

---

## 12. Glossary

**Agent:** An AI agent in the CrewAI framework that performs a specific task (e.g., resource discovery).

**Crew:** A collection of agents and tasks orchestrated by CrewAI.

**Job:** A single resource discovery request with unique ID and status.

**Cache Key:** A unique identifier for cached results, based on inputs and config hash.

**Config Hash:** SHA256 hash of agents.yaml and tasks.yaml files, used for cache invalidation.

**Rate Limiter:** Component that restricts API request frequency per IP address.

**RLS (Row Level Security):** PostgreSQL feature that restricts data access at the row level.

**TTL (Time To Live):** Duration before cached data expires.

**CrewAI:** Multi-agent orchestration framework for AI workflows.

**Serper API:** Web search API service used by agents.

**Supabase:** Backend-as-a-Service platform providing PostgreSQL database.

**NotebookLM:** Google's AI-powered note-taking tool that accepts URLs for content import.

---

## 13. References

### 12.1 Project Documentation

- `scholar_source_TDD.md` - Detailed technical implementation specifications
- `docs/TESTING_GUIDE.md` - Testing documentation
- `docs/DEPLOYMENT_PLAN.md` - Deployment procedures

### 12.2 External Documentation

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [CrewAI Documentation](https://docs.crewai.com/)
- [React Documentation](https://react.dev/)
- [Supabase Documentation](https://supabase.com/docs)
- [Railway Documentation](https://docs.railway.app/)
- [Cloudflare Pages Documentation](https://developers.cloudflare.com/pages)

### 12.3 API References

- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Serper API Documentation](https://serper.dev/docs)
- [Supabase Python Client](https://supabase.com/docs/reference/python/introduction)

---

**Document Version:** 1.0  
**Last Updated:** December 2024  
**Author:** ScholarSource Development Team

