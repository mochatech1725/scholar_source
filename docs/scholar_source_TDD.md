# ScholarSource Technical Design Document

> **Note:** This document contains detailed implementation specifications. For high-level system architecture and design rationale, see `scholar_source_SDD.md`.

## Document Control

| Field | Value |
|-------|-------|
| **Document Title** | ScholarSource Technical Design Document |
| **Version** | 1.0 |
| **Date** | December 2024 |
| **Author** | ScholarSource Development Team |
| **Status** | Approved |

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Backend Technical Design](#2-backend-technical-design)
3. [Database Technical Design](#3-database-technical-design)
4. [Frontend Technical Design](#4-frontend-technical-design)
5. [CrewAI Technical Design](#5-crewai-technical-design)
6. [API Technical Design](#6-api-technical-design)
7. [Caching Technical Design](#7-caching-technical-design)
8. [Rate Limiting Technical Design](#8-rate-limiting-technical-design)
9. [Testing Technical Design](#9-testing-technical-design)
10. [References](#10-references)

---

## 1. Introduction

This Technical Design Document (TDD) provides detailed implementation specifications for ScholarSource components. It covers function signatures, algorithms, data structures, and implementation flows that developers need to write code.

**Audience:** Software engineers implementing or maintaining the system.

**Related Documents:**
- `scholar_source_SDD.md` - High-level system architecture and design rationale
- `docs/TESTING_GUIDE.md` - Testing documentation

---

## 2. Backend Technical Design

### 2.1 Job Management Component (`backend/jobs.py`)

#### 2.1.1 Function Signatures

**`create_job(inputs: dict) -> str`**

Creates a new job in Supabase database.

- **Parameters:**
  - `inputs`: Dictionary of course input parameters
- **Returns:** UUID of the created job (string)
- **Raises:** Exception if job creation fails

**Implementation Details:**
- Generates search title from inputs using `_generate_search_title()`
- Sets initial status to 'pending'
- Stores inputs as JSONB in database
- Returns job UUID from database

**`get_job(job_id: str) -> Optional[Dict[str, Any]]`**

Gets job data from Supabase database.

- **Parameters:**
  - `job_id`: UUID of the job
- **Returns:** Job data dictionary or None if not found

**Implementation Details:**
- Queries `jobs` table by `id` column
- Returns None if job not found
- Logs errors but doesn't raise exceptions

**`update_job_status(job_id: str, status: str, results: Optional[list] = None, error: Optional[str] = None, status_message: Optional[str] = None, raw_output: Optional[str] = None, metadata: Optional[dict] = None) -> None`**

Updates job status and optional fields in Supabase.

- **Parameters:**
  - `job_id`: UUID of the job
  - `status`: New status (pending, running, completed, failed, cancelled)
  - `results`: List of Resource dictionaries (optional)
  - `error`: Error message if failed (optional)
  - `status_message`: Current progress message (optional)
  - `raw_output`: Raw markdown output from crew (optional)
  - `metadata`: Additional metadata (optional)
- **Raises:** Exception if update fails

**Implementation Details:**
- Updates `jobs` table using Supabase client
- Sets `completed_at` timestamp when status is 'completed' or 'failed'
- All optional fields can be None
- Raises exception on database errors

**Future Job Management Functions:**

**`delete_job(job_id: str) -> bool`**

Deletes a job from the database.

- **Parameters:**
  - `job_id`: UUID of job to delete
- **Returns:** True if deleted, False if not found
- **Use Cases:** Manual cleanup, user-requested deletion

**`cleanup_expired_jobs(max_age_days: int = 90) -> int`**

Deletes jobs older than specified number of days.

- **Parameters:**
  - `max_age_days`: Maximum age in days (default: 90)
- **Returns:** Number of deleted jobs
- **Implementation:** Queries jobs where created_at < NOW() - INTERVAL 'max_age_days days' and deletes them
- **Use Cases:** Automatic cleanup, scheduled maintenance

#### 2.1.2 Job Management Flow

The job management system coordinates job submission, execution, and status tracking through a distributed task queue architecture with Celery, Redis, and Supabase.

**Request Flow:**

1. **Client submits job** → POST `/api/submit`
   - API validates input and checks rate limits (Redis-backed)
   - `create_job()` creates job record in Supabase with `status: "pending"`
   - `run_crew_async()` enqueues job to Celery queue (via `run_crew_task.apply_async()`)
   - API returns `job_id` immediately (200 OK)

2. **API enqueues Celery task** → Job stored in Redis queue
   - Job status updated to `"queued"` in Supabase
   - Task metadata stored (celery_task_id, bypass_cache)
   - API response returned immediately (non-blocking)

3. **Celery worker picks up task** → Worker consumes job from Redis queue
   - Worker process polls Redis for jobs from `crew_jobs` queue
   - Worker selects job based on queue and priority
   - `run_crew_task()` executes in separate worker process

4. **Worker executes CrewAI** → `run_crew_task()` runs multi-agent workflow
   - Worker updates job status to `"running"` in Supabase
   - CrewAI execution begins (LLM calls, web scraping, resource discovery)
   - Execution takes 2-10 minutes depending on complexity
   - Worker periodically updates `status_message` during execution

5. **Worker updates job status** → Updates stored in Supabase database
   - On completion: updates status to `"completed"` with results via `update_job_status()`
   - On failure: updates status to `"failed"` with error message via `update_job_status()`
   - Status messages include progress updates during execution

6. **Client polls status** → GET `/api/status/{job_id}`
   - Client polls this endpoint repeatedly (every 2 seconds) to check job progress
   - API queries Supabase by `job_id` using `get_job()`
   - Returns current status, results (if completed), or error (if failed)
   - No direct communication between API and worker processes (database acts as coordination point)

**Key Characteristics:**
- **State Storage:** Supabase `jobs` table serves as the single source of truth for job state
- **Execution Model:** Distributed task queue with Celery workers (separate processes, not threads)
- **Communication:** Worker processes write to Supabase; Redis queue coordinates job distribution
- **Queue System:** Jobs are queued in Redis, distributed across available workers
- **Process Isolation:** Worker crashes don't affect API availability; jobs can be retried
- **Scalability:** API and worker layers can scale independently based on demand

The job record in Supabase acts as the coordination point between the API (which creates jobs and handles status polling) and the Celery worker processes (which execute the CrewAI workflow and update job status).

### 2.2 Crew Runner Component (`backend/crew_runner.py`)

#### 2.2.1 Function Signatures

**`run_crew_async(job_id: str, inputs: Dict[str, str], bypass_cache: bool = False) -> str`**

Enqueues a ScholarSource crew job to the Celery task queue, or runs synchronously if in SYNC_MODE.

- **Function flow:**
  1. Validates job exists and is in correct status
  2. If SYNC_MODE: Runs job synchronously in current process (development only)
  3. If Celery mode: Enqueues job to Celery queue via `run_crew_task.apply_async()`
  4. Updates job status to 'queued' with Celery task ID
  5. Returns Celery task ID (or "sync" in SYNC_MODE)
- **Parameters:**
  - `job_id`: UUID of the job to run
  - `inputs`: Dictionary of course input parameters
  - `bypass_cache`: If True, bypass cache and get fresh results
- **Returns:**
  - `str`: Celery task ID (in async mode) or "sync" (in sync mode)

**Implementation Details:**
- Enqueues job to Celery queue using `run_crew_task.apply_async()`
- Job routed to `crew_jobs` queue with default priority
- Celery task ID stored in job metadata for cancellation tracking
- Returns immediately after enqueuing (non-blocking)

### 2.3 Celery Task Component (`backend/tasks.py`)

#### 2.3.1 Function Signatures

**`run_crew_task(job_id: str, inputs: Dict[str, str], bypass_cache: bool = False) -> Dict[str, any]` (Celery Task)**

Celery task that executes the ScholarSource crew. Runs in separate worker process.

- **Function flow:**
  1. Updates job status to 'running'
  2. Checks cache (if not bypassed) using `get_cached_analysis()`
  3. Executes the crew with provided inputs using `kickoff_async()`
  4. Parses the markdown output into structured resources
  5. Updates job with results or error
  6. Supports cancellation via Celery's revoke mechanism
- **Parameters:**
  - `job_id`: UUID of the job to run
  - `inputs`: Dictionary of course input parameters
  - `bypass_cache`: If True, bypass cache and get fresh results
- **Returns:**
  - `Dict[str, any]`: Status and results/error information

**Implementation Details:**
- Decorated with `@app.task()` making it a Celery task
- Runs in separate worker process (not in API process)
- Handles retries automatically (max 3 retries, 60s delay)
- Updates job status via `update_job_status()` throughout execution

**Execution Flow:**
1. Check if job was cancelled before starting
2. Update job status to 'running'
3. Check cache (if not bypassed) using `get_cached_analysis()`
4. If cache hit and valid, use cached results, skip to parsing
5. Create ScholarSource crew instance
6. Execute crew with `crew().kickoff_async(inputs=inputs)`
7. Store async task in `_active_tasks` dict for cancellation
8. Parse markdown output using `parse_markdown_to_resources()`
9. Update job with results, raw_output, and metadata
10. Store results in cache using `set_cached_analysis()`
11. Handle exceptions and update job with error

**`cancel_crew_job(job_id: str) -> bool`**

Cancels an active crew job by cancelling its async task.

- **Parameters:**
  - `job_id`: UUID of the job to cancel
- **Returns:** True if task was found and cancelled, False otherwise

**Implementation Details:**
- Looks up task in `_active_tasks` dict by job_id
- Calls `task.cancel()` if task exists and not done
- Returns True if cancelled, False if not found

### 2.3 Markdown Parser Component (`backend/markdown_parser.py`)

#### 2.3.1 Function Signatures

**`parse_markdown_to_resources(markdown_content: str, excluded_sites: Optional[str] = None) -> Dict[str, Any]`**

Parses markdown report into structured resources and metadata.

- **Parameters:**
  - `markdown_content`: Raw markdown content from crew output
  - `excluded_sites`: Comma-separated list of domains to exclude
- **Returns:** Dictionary with 'resources' (list) and 'textbook_info' (dict or None)

**Post-Processing:**
- Filters out resources with "ERROR" in title, description, or URL
- Filters excluded domains if `excluded_sites` provided
- Extracts textbook info from markdown (pattern: `**Textbook:** ...`)

**`_filter_excluded_domains(resources: List[Dict], excluded_sites: str) -> List[Dict]`**

Filters resources by excluded domains.

- **Parameters:**
  - `resources`: List of resource dictionaries
  - `excluded_sites`: Comma-separated list of domains (e.g., "mit.edu, khanacademy.org")
- **Returns:** List of resources with excluded domains removed

**Implementation Details:**
- Splits `excluded_sites` by comma
- Strips whitespace from each domain
- Checks if resource URL contains any excluded domain
- Case-insensitive matching

**`_contains_error(url: str, title: str, description: str) -> bool`**

Checks if resource contains error indicators.

- **Parameters:**
  - `url`: Resource URL
  - `title`: Resource title
  - `description`: Resource description
- **Returns:** True if error detected, False otherwise

**Error Detection:**
- Checks for "ERROR" (case-insensitive) in url, title, or description
- Checks for "Failed to connect", "Could not fetch", "404", "Not found"
- Returns True if any error indicator found

### 2.4 Database Component (`backend/database.py`)

#### 2.4.1 Supabase Client Initialization

**`get_supabase_client() -> Client`**

Initializes and returns Supabase client.

- **Returns:** Supabase client instance
- **Raises:** ValueError if SUPABASE_URL or SUPABASE_ANON_KEY not set

**Implementation Details:**
- Reads environment variables on import
- Raises ValueError if missing (fails fast)
- Client is module-level singleton

---

## 3. Database Technical Design

### 3.1 Complete SQL Schema

#### 3.1.1 Jobs Table DDL

The `jobs` table is created with the following schema:
- Primary key: `id` (UUID, auto-generated)
- Status field with CHECK constraint allowing: pending, running, completed, failed, cancelled
- JSONB fields for inputs, results, and metadata
- TEXT fields for raw_output, error, status_message, search_title
- Timestamps: created_at (defaults to NOW()), completed_at (nullable)

Indexes:
- `idx_jobs_status` on status column
- `idx_jobs_created_at` on created_at column (DESC)

Row Level Security is enabled with a permissive policy allowing all operations.

**Field Descriptions:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key, auto-generated |
| `status` | TEXT | Job status (enum: pending, running, completed, failed, cancelled) |
| `inputs` | JSONB | Original input parameters from user |
| `results` | JSONB | Parsed resource list (when completed) |
| `raw_output` | TEXT | Raw markdown output from crew |
| `error` | TEXT | Error message (when failed) |
| `status_message` | TEXT | Current progress message |
| `search_title` | TEXT | Generated title for display |
| `metadata` | JSONB | Additional metadata (textbook_info, etc.) |
| `created_at` | TIMESTAMPTZ | Job creation timestamp |
| `completed_at` | TIMESTAMPTZ | Job completion timestamp (null until completed/failed) |

**Indexes:**
- `idx_jobs_status` - Optimizes status queries (polling)
- `idx_jobs_created_at` - Optimizes chronological queries

#### 3.1.2 Course Cache Table DDL

The `course_cache` table is created with the following schema:
- Primary key: `cache_key` (TEXT)
- `config_hash` (TEXT, NOT NULL) - Hash of agents.yaml + tasks.yaml
- `cache_type` (TEXT, NOT NULL, default 'analysis') - Either 'analysis' or 'full'
- JSONB fields for inputs and results
- `cached_at` (TIMESTAMPTZ, defaults to NOW())

Indexes:
- `idx_course_cache_config_hash` on config_hash column
- `idx_course_cache_cached_at` on cached_at column (DESC)

Row Level Security is enabled with a permissive policy allowing all operations.

**Field Descriptions:**

| Field | Type | Description |
|-------|------|-------------|
| `cache_key` | TEXT | Primary key, format: "analysis:hash" or "full:hash" |
| `config_hash` | TEXT | SHA256 hash of agents.yaml + tasks.yaml (first 16 chars) |
| `cache_type` | TEXT | 'analysis' or 'full' |
| `inputs` | JSONB | Original input parameters (for debugging) |
| `results` | JSONB | Cached results |
| `cached_at` | TIMESTAMPTZ | Cache creation timestamp (for TTL) |

**Indexes:**
- `idx_course_cache_config_hash` - Optimizes config-based invalidation queries
- `idx_course_cache_cached_at` - Optimizes TTL expiration queries

### 3.2 Data Validation Rules

#### 3.2.1 CourseInputRequest Validation

**Pydantic Model: `CourseInputRequest`**

The model includes the following optional fields:
- `university_name`, `course_name`, `course_url` (strings)
- `book_title`, `book_author`, `isbn`, `book_pdf_path`, `book_url` (strings)
- `topics_list`, `excluded_sites` (strings)
- `desired_resource_types` (list of strings)
- `bypass_cache` (boolean, defaults to False)

**Validation Logic:**
1. **Empty String Conversion:**
   - `@model_validator(mode='before')` converts empty strings to None
   - Whitespace-only strings also converted to None

2. **At Least One Field Required:**
   - Custom validation in `validate_crew_inputs()` function
   - Checks for: course_url, course_name, university_name, book_title+author, isbn, book_pdf_path, book_url
   - Raises HTTPException 400 if none provided

3. **Field Types:**
   - String fields: Optional[str] (nullable)
   - Lists: Optional[List[str]] (nullable)
   - Boolean: Optional[bool] (defaults to False)

---

## 4. Frontend Technical Design

### 4.1 HomePage Component (`web/src/pages/HomePage.jsx`)

#### 4.1.1 State Management

The HomePage component uses React hooks for state management with the following state variables:

- Job-related state: `jobId`, `isLoading`, `results`, `searchTitle`, `textbookInfo`, `error`, `statusMessage`
- Form state: `searchParamType`, `formData` (containing course_url, book_url, book_title, book_author, isbn, topics_list, desired_resource_types, excluded_sites, bypass_cache), `validationError`

**State Structure:**
- `jobId` - Current job UUID (null when no active job)
- `isLoading` - Whether job is in progress
- `results` - Parsed resource list (null until completed)
- `searchTitle` - Generated search title for display
- `textbookInfo` - Extracted textbook metadata
- `error` - Error message (null if no error)
- `statusMessage` - Current progress message
- `formData` - Form input values
- `validationError` - Form validation error message

#### 4.1.2 Handler Functions

**`handleSubmit(e)` (async)**

Handles form submission:
1. Prevents default form submission
2. Validates form data using `isFormValid()`
3. Calls `submitJob()` API with form data
4. Updates state with job_id and sets loading state
5. Handles errors by setting error message

**`pollJobStatus()` (async, useCallback)**

Polls job status:
1. Calls `getJobStatus(jobId)` API
2. Updates status, results, error based on response
3. Stops polling if status is completed, failed, or cancelled
4. Continues polling if status is pending or running

**`handleCancel()` (async)**

Handles job cancellation:
1. Calls `cancelJob(jobId)` API
2. Updates job status to cancelled
3. Stops polling (cleared by useEffect cleanup)

#### 4.1.3 Polling Implementation

The polling is implemented using `useEffect` hook:
- Sets up an interval using `setInterval` that calls `pollJobStatus()` every 2000ms (2 seconds)
- Cleans up the interval on unmount or when jobId changes
- Only polls when jobId is not null

**Polling Strategy:**
- Polls every 2 seconds while job is active
- Stops polling when job completes, fails, or is cancelled
- Cleans up interval on unmount or jobId change

### 4.2 Search Form (Inline in `web/src/pages/HomePage.jsx`)

The search form is implemented inline within HomePage rather than as a separate component.

#### 4.2.1 Form Fields

**Search Type Selector:**
- Dropdown with options: course_url, book_url, book_title_author, isbn
- Controls which input fields are shown

**Dynamic Input Fields (based on search type):**
- `course_url` - URL input (shown when "Course URL" selected)
- `book_url` - URL input (shown when "Book URL" selected)
- `book_title` + `book_author` - Text inputs (shown when "Book Title + Author" selected)
- `isbn` - Text input (shown when "Book ISBN" selected)

**Optional Accordion Sections:**
- `desired_resource_types` - Checkboxes (textbooks, practice_problem_sets, practice_exams_tests, lecture_videos)
- `topics_list` - Textarea (comma-separated focus topics)
- `excluded_sites` - Textarea (comma-separated domains to exclude)
- `targeted_sites` - Textarea (comma-separated domains to prioritize)
- `bypass_cache` - Checkbox (force refresh, skip cache)

#### 4.2.2 Validation Logic

**`isFormValid()` function**

Validates based on selected search type:
- `course_url`: course_url must not be empty
- `book_url`: book_url must not be empty
- `book_title_author`: both book_title AND book_author must not be empty
- `isbn`: isbn must not be empty

**Validation Rules:**
- Submit button disabled when form invalid
- Validation error displayed on submit attempt with invalid form
- Error cleared when user modifies inputs

### 4.3 ResultsTable Component (`web/src/components/ResultsTable.jsx`)

#### 4.3.1 Features

**Filtering:**

Uses `useState` for `filterType` state and `useMemo` to compute filtered resources. Filters resources by type when filterType is not 'all', otherwise returns all resources.

- Filter by resource type (Textbook, PDF, Video, etc.)
- Dropdown selector for type filter
- "All" option shows all resources

**Sorting:**

Uses `useState` for `sortBy` state and `useMemo` to compute sorted resources. When sortBy is 'type', sorts by type then by title. When sortBy is 'title', sorts by title only.

- Sort by type (alphabetical)
- Sort by title (alphabetical)
- Default: by type, then by title

**NotebookLM Integration Limitation:**
The application does not programmatically create NotebookLM notebooks. The "Copy + NotebookLM" button opens NotebookLM in a new tab, but users must manually import the resource URLs. This is because:
- Programmatic notebook creation via API is only available in NotebookLM Enterprise (paid/enterprise tier)
- ScholarSource targets the free/public NotebookLM tier used by students
- No NotebookLM API integration exists in the codebase
- Manual import is the only viable workflow for the target user base

#### 4.3.2 State Management

ResultsTable component uses React hooks for state:
- `filterType` - Current filter selection (defaults to 'all')
- `sortBy` - Current sort option (defaults to 'type')
- `copiedUrl` - URL that was recently copied (null or URL string)

---

## 5. CrewAI Technical Design

### 5.1 Agent Configuration

#### 5.1.1 Agent Definitions (`src/scholar_source/crew.py`)

**course_intelligence_agent:**

Agent definition using `@agent` decorator. Reads configuration from `agents_config['course_intelligence_agent']`. LLM model can be overridden via `COURSE_INTELLIGENCE_AGENT_MODEL` environment variable (defaults to 'openai/gpt-4o'). Uses WebPageFetcherTool and WebsiteSearchTool.

**resource_discovery_agent:**

Agent definition using `@agent` decorator. Reads configuration from `agents_config['resource_discovery_agent']`. LLM model can be overridden via `RESOURCE_DISCOVERY_AGENT_MODEL` environment variable (defaults to 'openai/gpt-4o-mini'). Uses SerperDevTool for web search.

**resource_validator_agent:**

Agent definition using `@agent` decorator. Reads configuration from `agents_config['resource_validator_agent']`. LLM model can be overridden via `RESOURCE_VALIDATOR_AGENT_MODEL` environment variable (defaults to 'openai/gpt-4o-mini'). Uses SerperDevTool, WebsiteSearchTool, and YoutubeVideoSearchTool.

**output_formatter_agent:**

Agent definition using `@agent` decorator. Reads configuration from `agents_config['output_formatter_agent']`. LLM model can be overridden via `OUTPUT_FORMATTER_AGENT_MODEL` environment variable (defaults to 'openai/gpt-4o-mini'). No tools (formatting only).

### 5.2 Task Configuration

#### 5.2.1 Task Definitions

**course_analysis_task:**
- Extracts textbook info from course page
- Uses WebPageFetcherTool to fetch course content
- Outputs: course_title, topics_list, textbook_title, textbook_author

**resource_search_task:**
- Searches for 5-7 resources using SerperDevTool
- Outputs to `report.md` file

**resource_validation_task:**
- Validates resources using WebsiteSearchTool and YoutubeVideoSearchTool
- Filters out invalid/illegal resources

**final_output_task:**
- Formats final markdown output
- Outputs to `report.md` file

### 5.3 Crew Execution Flow

1. **Crew Creation:**
   - Creates crew instance using `ScholarSource().crew()`

2. **Async Execution:**
   - Executes crew using `crew.kickoff_async(inputs=inputs)`

3. **Output Access:**
   - Accesses markdown output via `result.raw` property

4. **File Output:**
   - Tasks with `output_file='report.md'` write to file
   - File created in project root directory

---

## 6. API Technical Design

### 6.1 Request/Response Schemas

#### 6.1.1 POST /api/submit

**Request Body:**

JSON object with optional fields:
- `course_url` (string)
- `book_title`, `book_author` (strings)
- `desired_resource_types` (array of strings)
- `excluded_sites` (string, comma-separated domains)
- `bypass_cache` (boolean, default false)
- Other course/book input fields

**Error Responses:**
- **400 Bad Request:** Invalid inputs (at least one field required)
- **429 Too Many Requests:** Rate limit exceeded
- **500 Internal Server Error:** Job creation failed

#### 6.1.2 GET /api/status/{job_id}

**Response (200 OK - Pending/Running):**

JSON object containing:
- `job_id` (UUID string)
- `status` (string: "pending" or "running")
- `status_message` (string, optional)
- `search_title` (string, optional)
- `created_at` (ISO 8601 timestamp)

**Error Responses:**
- **404 Not Found:** Job ID doesn't exist
- **429 Too Many Requests:** Rate limit exceeded

#### 6.1.3 POST /api/cancel/{job_id}

**Response (200 OK):**

JSON object containing:
- `job_id` (UUID string)
- `status` (string: "cancelled")
- `message` (string)

**Error Responses:**
- **400 Bad Request:** Job already completed/failed/cancelled
- **404 Not Found:** Job ID doesn't exist
- **429 Too Many Requests:** Rate limit exceeded
- **500 Internal Server Error:** Cancellation failed

#### 6.1.4 GET /api/health

**Response (200 OK):**

JSON object containing:
- `status` (string: "healthy")
- `version` (string: "0.1.0")
- `database` (string: "skipped" or connection status)

**Purpose:**
- Health check endpoint for Railway deployment
- Used by monitoring systems to verify service availability
- Simplified check (skips database connectivity to avoid timeout during container startup)

**Future Health Check Improvements:**
- Check database connectivity
- Check external API availability (OpenAI, Serper)
- Return detailed health status for each component
- Include uptime and system metrics

### 6.2 Error Handling

**Error Response Format:**

JSON object with `detail` field containing:
- `error` (string): Error type
- `message` (string): Human-readable error message

**HTTP Status Codes:**
- 200: Success
- 400: Bad Request (validation errors)
- 404: Not Found (job doesn't exist)
- 429: Too Many Requests (rate limit exceeded)
- 500: Internal Server Error (server errors)

**Future Error Handling Enhancements:**

**Network Error Detection:**
- Distinguish network timeout vs server error
- Provide user-friendly error messages with actionable suggestions
- Include "what went wrong" and "how to fix it" in error responses

**Retry Logic:**
- Implement exponential backoff for transient network errors (503, 502, timeouts)
- Show retry countdown to user
- Manual "Try Again" option for non-retryable errors
- Auto-retry transient errors with configurable max attempts

**Error Categorization:**
- Detect OpenAI API errors vs network vs validation errors
- Show specific next steps based on error type
- Add "Show Details" option for debugging
- Categorize job failure error messages

**Rate Limiting Detection:**
- Detect 429 responses from backend/OpenAI
- Show wait time and auto-retry after delay
- Queue job if rate limited
- Display rate limit information to user

**Empty Results Handling:**
- Explain why no resources found
- Suggest how to improve search (broaden inputs, try different keywords)
- Provide helpful suggestions for empty result scenarios

### 6.3 NotebookLM Integration Constraints

**No Programmatic Notebook Creation:**
ScholarSource does not integrate with NotebookLM's API to automatically create notebooks. This is a deliberate design constraint based on NotebookLM's API availability:

**Constraint:**
- **NotebookLM Enterprise API Required:** Programmatic notebook creation is only available through NotebookLM Enterprise API (paid/enterprise subscription)
- **Free Tier Limitation:** The free/public NotebookLM version does not provide API access for automated operations
- **Target User Base:** ScholarSource is designed for students using the free NotebookLM tier

**Current Implementation:**
- Frontend provides "Copy + NotebookLM" button that:
  1. Opens NotebookLM in a new browser tab using `window.open()` with NotebookLM URL
  2. Users manually paste resource URLs into NotebookLM
  3. NotebookLM processes the URLs and creates study materials

**Why Not Enterprise API:**
- Enterprise API requires paid subscription (not accessible to free-tier users)
- Would add complexity (authentication, API key management)
- Would limit user base to Enterprise subscribers only
- Manual import is sufficient for the use case (one additional user step)

---

## 7. Caching Technical Design

### 7.1 Cache Key Generation Algorithm

**Inputs to Hash:**
1. course_url (if provided)
2. book_url (if provided)
3. book_title + book_author (if both provided)
4. isbn (if provided)
5. topics_list (sorted, comma-separated)
6. desired_resource_types (sorted, comma-separated)
7. config_hash (SHA256 of agents.yaml + tasks.yaml)

**Algorithm:**

The `_generate_cache_key()` function:
1. Builds key parts list from input parameters (course_url, book_url, book_title+author, isbn, topics_list, desired_resource_types)
2. Normalizes topics and resource types by sorting
3. Joins key parts with '|' separator and appends config_hash
4. Computes SHA256 hash of the key string
5. Returns cache key in format: `"{cache_type}:{first_16_chars_of_hash}"`

**Cache Key Format:**
- Analysis: `"analysis:{hash}"`
- Full: `"full:{hash}"`

### 7.2 Config Hash Computation

**`get_config_hash() -> str`**

Computes a SHA256 hash of agents.yaml and tasks.yaml files.

- Reads both config files from `src/scholar_source/config/`
- Concatenates their content
- Computes SHA256 hash
- Returns hex string
- Caches hash in memory to avoid re-reading files on every call

**Implementation Details:**
- Reads `src/scholar_source/config/agents.yaml` and `tasks.yaml`
- Computes SHA256 hash of both files concatenated
- Returns hex string (e.g., "a7f3c2e1...")
- Handles missing files gracefully (uses placeholder string)
- Uses in-memory cache to avoid file I/O on every call

### 7.2.1 Input Normalization

**`normalize_cache_inputs(inputs: Dict[str, Any]) -> Dict[str, Any]`**

Creates consistent cache keys from user inputs by normalizing and extracting only cache-relevant fields.

- **Parameters:**
  - `inputs`: Dictionary of user input parameters
- **Returns:** Normalized dictionary with sorted keys

**Function flow:**
1. Extracts only cache-relevant fields: `course_url`, `book_title`, `book_author`, `isbn`, `topics_list`, `desired_resource_types`
2. Sorts keys alphabetically
3. Normalizes URLs (removes trailing slashes, converts to lowercase)
4. Returns sorted dictionary for consistent hashing

### 7.3 TTL Implementation

**TTL Values:**
- Analysis cache: 30 days (configurable via `COURSE_ANALYSIS_TTL_DAYS` env var, default 30)
- Full cache: 7 days (configurable via `RESOURCE_RESULTS_TTL_DAYS` env var, default 7)

**Expiration Check:**

The `is_cache_expired()` function:
- Selects appropriate TTL based on cache_type (COURSE_ANALYSIS_TTL_DAYS for 'analysis', RESOURCE_RESULTS_TTL_DAYS for 'full')
- Calculates age as difference between current time and cached_at timestamp
- Returns True if age exceeds TTL threshold

**TTL Logic:**
- Analysis cache: 30 days (textbook extraction, topics) - Changes infrequently
- Full cache: 7 days (complete resource discovery results) - New resources may be published
- Checks `cached_at` timestamp against current time
- Returns None if expired or not found

### 7.4 Cache Retrieval and Storage

**`get_cached_analysis(inputs: Dict[str, Any], cache_type: str = 'analysis', bypass_cache: bool = False) -> Optional[Dict[str, Any]]`**

Retrieves cached course analysis or full results.

- **Parameters:**
  - `inputs`: Course input parameters
  - `cache_type`: 'analysis' or 'full'
  - `bypass_cache`: If True, always returns None (force fresh)
- **Returns:** Cached results dictionary or None if not found/expired

**Function flow:**
1. Returns None immediately if bypass_cache is True
2. Computes current config hash
3. Generates cache key from inputs and config hash
4. Queries Supabase course_cache table by cache_key
5. Returns None if entry not found
6. Validates config hash matches (returns None if different)
7. Checks TTL expiration (returns None if expired)
8. Returns cached results

**`set_cached_analysis(inputs: Dict[str, Any], results: Dict[str, Any], cache_type: str = 'analysis') -> None`**

Stores cached course analysis or full results.

- **Parameters:**
  - `inputs`: Original input parameters
  - `results`: Results to cache
  - `cache_type`: 'analysis' or 'full'

**Function flow:**
1. Computes current config hash
2. Generates cache key from inputs and config hash
3. Upserts cache entry into Supabase course_cache table with cache_key, config_hash, cache_type, inputs, results, and cached_at timestamp

### 7.5 Cache Invalidation

**Automatic Invalidation:**
- When `agents.yaml` or `tasks.yaml` changes, config_hash changes
- New cache keys generated, old cache entries become orphaned
- Old entries can be cleaned up manually or via scheduled job

**Manual Invalidation:**
- User sets `bypass_cache=true` in request
- Cache is checked but result is ignored
- Fresh crew execution always performed

### 7.5.1 Cache Cleanup

**`clear_cache_for_config_change() -> int`**

Removes stale cache entries from old config versions.

- **Returns:** Number of deleted entries

**Function flow:**
1. Gets current config hash via `get_config_hash()`
2. Deletes all rows from `course_cache` table where `config_hash != current_hash`
3. Returns count of deleted rows

**Use Cases:**
- Periodic cleanup of orphaned cache entries
- Run after configuration file changes
- Can be scheduled as cron job or background task

### 7.5.2 Cache Statistics

**`get_cache_stats() -> Dict[str, Any]`**

Gets cache statistics for monitoring and health checks.

- **Returns:** Dictionary with cache statistics

**Function flow:**
1. Gets current config hash via `get_config_hash()`
2. Queries `course_cache` table for:
   - Total entries
   - Valid entries (matching current config hash)
   - Stale entries (different config hash)
   - Entries by cache_type (analysis vs full)
   - Average age of entries
3. Returns statistics as dictionary

**Statistics Returned:**
- `total_entries`: Total number of cache entries
- `valid_entries`: Entries matching current config hash
- `stale_entries`: Entries with different config hash
- `config_hash`: Current configuration hash
- `by_type`: Dictionary with counts by cache_type
- `average_age`: Average age of cache entries in days

### 7.6 Two-Tier Caching Strategy

**Tier 1: Course Analysis (30 days TTL)**
- **What:** Textbook extraction, topic identification, course metadata
- **Why Cache:** This is expensive (requires parsing course pages) and changes infrequently
- **TTL:** 30 days (configurable via `COURSE_ANALYSIS_TTL_DAYS`)
- **When Invalidated:**
  - Config files change (agents.yaml, tasks.yaml)
  - TTL expires (30 days)
  - Force refresh requested

**Tier 2: Full Resource Results (7 days TTL)**
- **What:** Complete resource discovery results (all found resources)
- **Why Shorter TTL:** New resources may be published online daily
- **TTL:** 7 days (configurable via `RESOURCE_RESULTS_TTL_DAYS`)
- **When Invalidated:**
  - Config files change
  - TTL expires (7 days - ensures fresh results)
  - Force refresh requested

**Recommended Approach: Cache Analysis Only**
- Best Practice: Cache only course analysis, always run resource discovery fresh
- Benefits:
  - ✅ Fast course parsing (cached for 30 days)
  - ✅ Fresh resource discovery (always current)
  - ✅ Best balance of speed and freshness

---

## 8. Rate Limiting Technical Design

### 8.1 Implementation Details

#### 8.1.1 Rate Limiter Initialization

The rate limiter is initialized in `backend/rate_limiter.py`:
- Checks for `REDIS_URL` environment variable
- If REDIS_URL is set: Creates Limiter with Redis storage_uri for multi-instance deployments
- If REDIS_URL is not set: Creates Limiter with in-memory storage for single instance
- Uses `get_remote_address` as key function (IP-based rate limiting)
- Sets default limit of 1000 requests/hour
- Logs which backend is active (Redis vs in-memory)

**Key Points:**
- ✅ **Redis-ready from day 1:** Automatically uses Redis if `REDIS_URL` is set
- ✅ **Zero-config migration:** Just add `REDIS_URL` env var when scaling
- ✅ **Startup logging:** Shows which backend is active (Redis vs in-memory)
- ✅ **Single instance safe:** Works perfectly with in-memory for 1 instance
- ⚠️ **Multi-instance warning:** If you scale, you MUST add Redis (see migration guide)
- Uses IP address for rate limiting (`get_remote_address`)
- Global fallback: 1000 requests/hour for any endpoint

#### 8.1.2 Rate Limit Decorators

Rate limits are applied using `@limiter.limit()` decorator on FastAPI endpoint functions:

- `POST /api/submit`: `@limiter.limit("10/hour; 2/minute")` - Combined limit decorator
- `GET /api/status/{job_id}`: `@limiter.limit("100/minute")` - Per-minute limit decorator
- `POST /api/cancel/{job_id}`: `@limiter.limit("20/hour")` - Per-hour limit decorator
- `GET /api/health`: No rate limit decorator (unlimited)

**Rate Limit Configuration:**

| Endpoint | Limit | Reasoning |
|----------|-------|-----------|
| `POST /api/submit` | `10/hour; 2/minute` | Each job costs money (OpenAI API). Allow 10 jobs/hour (reasonable for students). Prevent burst spam (max 2/min). |
| `GET /api/status/{job_id}` | `100/minute` | Cheap operation (just database read). Frontend polls every 2-3 seconds. Be generous to avoid false positives. |
| `POST /api/cancel/{job_id}` | `20/hour` | Rare operation. Allow retries if needed. Not expensive. |
| `GET /api/health` | **No limit** | Health checks should always work. Used by Railway/monitoring systems. |

**Rate Limit Syntax:**
- `"10/hour"` = 10 requests per hour
- `"2/minute"` = 2 requests per minute
- `"10/hour; 2/minute"` = **Combined limit:** Max 10/hour, but no more than 2 in any given minute

**Why Combined Limits:**
- Prevents burst attacks: `"10/hour"` alone allows 10 requests in 10 seconds, then nothing
- `"10/hour; 2/minute"` allows 2 requests/min up to 10 total/hour
- Better for legitimate users who make requests over time

#### 8.1.3 Error Handler

**`rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse`**

Custom handler for rate limit exceeded errors.

- Returns JSONResponse with 429 status code
- Response body includes: error type, message with retry_after time, retry_after value, and limit details

**Retry-After Calculation:**
- Extracts time window from limit string
- Default: 60 seconds
- If "minute" in limit: 60 seconds
- If "hour" in limit: 3600 seconds
- If "second" in limit: 1 second

#### 8.1.4 FastAPI Integration

Rate limiting is integrated into FastAPI by:
1. Importing `limiter` and `rate_limit_handler` from `backend.rate_limiter`
2. Importing `RateLimitExceeded` exception from `slowapi.errors`
3. Registering limiter with app state: `app.state.limiter = limiter`
4. Adding exception handler: `app.add_exception_handler(RateLimitExceeded, rate_limit_handler)`

**Required Changes:**
1. Import rate limiting components
2. Register limiter with app state
3. Add exception handler for 429 errors
4. Add `Request` parameter to rate-limited endpoints
5. Add `@limiter.limit()` decorators with appropriate limits

### 8.2 Multi-Instance Deployment Considerations

#### 8.2.1 Current Scalable Architecture

**✅ The system now uses a distributed task queue architecture with Celery and Redis:**

- **API Layer** (FastAPI Backend service): Stateless, can scale horizontally
- **Worker Layer** (Celery service): Celery creates separate processes that execute jobs.  Celery service can scale independently of FastAPI service.
- **Redis**: Required for both task queuing (Celery broker) and rate limiting (shared state)

**Architecture Benefits:**
- ✅ **Independent Scaling**: Scale API and Worker instances separately based on demand
- ✅ **Process Isolation**: Worker crashes don't affect API availability
- ✅ **Shared Rate Limiting**: Redis-backed rate limiting works across all API instances
- ✅ **Task Distribution**: Jobs automatically distributed across available workers
- ✅ **Fault Tolerance**: Jobs persist in Redis queue, can be retried if worker fails

#### 8.2.2 Redis Requirements

**Redis is REQUIRED (not optional) for the current architecture:**

1. **Celery Message Broker**: Stores enqueued jobs in task queues
2. **Celery Result Backend**: Optional task result storage
3. **Rate Limiting**: Shared state across all API instances

**Without Redis:**
- ❌ Celery workers cannot receive jobs
- ❌ Rate limiting falls back to in-memory (single-instance only)
- ⚠️ System can run in `SYNC_MODE` (development only, not for production)

#### 8.2.3 Scaling Strategy

**API Layer Scaling:**
- Scale API instances based on HTTP request volume
- All instances share Redis for rate limiting (consistent limits)
- Stateless design allows horizontal scaling behind load balancer
- Each instance can handle job submission (enqueues to Redis)

**Worker Layer Scaling:**
- Scale worker instances based on queue depth and job volume
- Workers automatically consume jobs from Redis queue
- Each worker can process multiple jobs concurrently (configurable)
- Workers update job status in shared database

**Example Scaling Scenario:**

```
Initial Setup:
- 1 API instance (handles requests)
- 1 Worker instance (2 concurrent jobs)

High Load:
- 3 API instances (handle more requests)
- 5 Worker instances (10 concurrent jobs total)
- 1 Redis instance (shared by all)
```

#### 8.2.4 Redis Setup for Production

**Railway Deployment:**

1. **Add Redis Service:**
   - Go to Railway Dashboard → "+ New" → "Database" → "Add Redis"
   - Or use external Redis Cloud service (recommended)
   - Copy the `REDIS_URL` connection string

2. **Set Environment Variables:**
   - **Backend Service**: Add `REDIS_URL` environment variable
   - **Celery Service**: Add `REDIS_URL` environment variable (same value)
   - Value format: `redis://default:password@red-xxxxx.railway.app:6379`

3. **Verify Configuration:**
   - **API logs**: Should show `✅ Rate limiting: Redis (multi-instance mode)`
   - **Worker logs**: Should show `🚀 CELERY APP MODULE LOADED` and successful Redis connection
   - **Health check**: `/api/health/workers` should show available workers

4. **Test Multi-Instance Behavior:**
   - Deploy 2+ API instances
   - Make requests from same IP
   - Verify rate limits work consistently across instances
   - Submit multiple jobs and verify they're distributed to workers

**External Redis Options:**
- **Redis Cloud**: Managed service, free tier available
- **Upstash**: Serverless Redis, pay-per-use
- **Railway Redis**: Integrated with Railway platform

### 8.3 Rate Limiting Configuration

**Environment Variables:**

**Required `REDIS_URL` environment variable** for production deployments. Format: `redis://default:password@red-xxxxx.railway.app:6379`

**Note:** In development, the system can run without Redis using `SYNC_MODE=true`, but this is not suitable for production multi-instance deployments.

**Code Configuration:**
- Limits are hardcoded in endpoint decorators
- Can be made configurable via environment variables if needed
- Redis-backed rate limiting provides consistent limits across all API instances
- Rate limit state is shared via Redis, ensuring accurate enforcement in multi-instance deployments

---

## 9. Testing Technical Design

### 9.1 Test Structure

#### 9.1.1 Backend Test Structure

**Test Directory Organization:**

- `tests/` - Root test directory
  - `conftest.py` - Shared fixtures (300+ lines)
  - `unit/` - Unit tests (fast, isolated)
    - `test_markdown_parser.py` - Markdown parsing (60+ tests)
    - `test_models.py` - Pydantic validation tests
    - `test_cache.py` - Cache functionality tests
    - `test_rate_limiter.py` - Rate limiting tests
  - `integration/` - Integration tests
    - `test_api_endpoints.py` - API endpoint tests (40+ tests)
    - `test_job_lifecycle.py` - Job workflow tests
  - `e2e/` - End-to-end tests (future)

**Test Quality Goals:**
- Comprehensive test coverage for Markdown Parser
- Thorough testing of API Endpoints
- Complete validation testing for Models

#### 9.1.2 Frontend Test Structure

**Test File Organization:**

- `web/src/test/` - Test configuration and mocks
  - `setup.js` - Vitest configuration
  - `mocks/handlers.js` - MSW API handlers
  - `mocks/server.js` - MSW server setup
- `web/src/components/` - Component test files
  - `ResultCard.test.jsx`, `StatusMessage.test.jsx`, `ConfirmDialog.test.jsx`, `Hero.test.jsx`
- `web/src/api/` - API client tests
  - `client.test.js` - API client tests

**Test Quality Goals:**
- Comprehensive testing of UI Components
- Thorough testing of API client functionality

### 9.2 Test Tools and Configuration

#### 9.2.1 Backend Testing

**Tools:**
- **pytest** (≥7.4.0) - Test runner and framework
- **pytest-asyncio** (≥0.21.0) - Async test support for FastAPI
- **pytest-mock** (≥3.11.0) - Mocking external dependencies
- **httpx** (≥0.24.0) - HTTP client for testing FastAPI
- **fakeredis** (≥2.19.0) - Mock Redis for rate limiting
- **faker** (≥20.0.0) - Generate fake test data

**Configuration (`pytest.ini`):**

Configuration includes:
- testpaths set to 'tests'
- adopts: verbose mode
- asyncio_mode set to 'auto'

**Installation:**

Install dependencies via: `pip install -r requirements-dev.txt`

#### 9.2.2 Frontend Testing

**Tools:**
- **Vitest** (≥1.0.0) - Fast, Vite-native test runner
- **@vitest/ui** (≥1.0.0) - Visual test runner UI
- **@testing-library/react** (≥14.0.0) - User-centric component testing
- **@testing-library/jest-dom** (≥6.1.0) - Custom DOM matchers
- **@testing-library/user-event** (≥14.5.0) - User interaction simulation
- **MSW** (≥2.0.0) - Mock Service Worker for API mocking
- **jsdom** (≥23.0.0) - DOM implementation for Node.js

**Configuration (`vitest.config.js`):**

Configuration includes:
- test environment: 'jsdom'
- globals: true
- setupFiles: './src/test/setup.js'
- test environment and configuration

**Installation:**

Install dependencies via npm with dev flag: vitest, @vitest/ui, @testing-library/react, @testing-library/jest-dom, @testing-library/user-event, jsdom, msw

### 9.3 Mocking External Dependencies

#### 9.3.1 Backend: Mock Supabase

**Available Fixtures (from `conftest.py`):**
- `mock_supabase` - Complete Supabase client mock
- `mock_crew_success` - CrewAI returns valid markdown
- `mock_crew_failure` - CrewAI raises exception
- `mock_crew_with_errors` - CrewAI returns markdown with errors

**Example Usage:**

Tests use the `mock_supabase` fixture from conftest.py. Test functions can populate `mock_supabase.jobs_data` dictionary with test data, then call functions that use Supabase to verify behavior.

#### 9.3.2 Frontend: Mock API with MSW

**Mock Endpoints (`web/src/test/mocks/handlers.js`):**
- `GET /api/health` - Returns healthy status
- `POST /api/submit` - Returns job_id and pending status
- `GET /api/status/:jobId` - Returns job status (pending/running/completed)
- `POST /api/cancel/:jobId` - Returns cancellation confirmation

**Example Usage:**

Tests import `server` from MSW server setup and can override handlers for specific tests using `server.use()` with `http` and `HttpResponse` from MSW. Tests can then verify error handling behavior.

### 9.4 Test Execution

#### 9.4.1 Running Tests

**All Tests:**

Run via `./scripts/test-all.sh`

**Backend Tests:**

- Run all: `./scripts/test-backend.sh` or `pytest`
- Run specific file: `pytest tests/unit/test_markdown_parser.py`

**Frontend Tests:**

- Run all: `cd web && npm test`
- With UI: `npm run test:ui`

## 10. References

### 10.1 Implementation Files

- `backend/main.py` - FastAPI application
- `backend/jobs.py` - Job management
- `backend/crew_runner.py` - Crew execution
- `backend/markdown_parser.py` - Markdown parsing
- `backend/cache.py` - Caching system
- `backend/models.py` - Pydantic models
- `backend/rate_limiter.py` - Rate limiting
- `web/src/pages/HomePage.jsx` - Main page component
- `web/src/pages/HomePage.jsx` - Main page with inline search form
- `web/src/components/ResultsTable.jsx` - Results display
- `src/scholar_source/crew.py` - CrewAI crew definition

### 10.2 Configuration Files

- `src/scholar_source/config/agents.yaml` - Agent configurations
- `src/scholar_source/config/tasks.yaml` - Task configurations
- `pytest.ini` - Pytest configuration
- `web/vitest.config.js` - Vitest configuration
- `supabase_schema.sql` - Database schema

### 10.3 Related Documentation

- `scholar_source_SDD.md` - High-level system architecture
- `docs/TESTING_GUIDE.md` - Testing documentation
- `docs/DEPLOYMENT_PLAN.md` - Deployment procedures

---

**Document Version:** 1.0  
**Last Updated:** December 2024  
**Author:** ScholarSource Development Team

