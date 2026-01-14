# ScholarSource Scaling Plan

## Document Control

| Field | Value |
|-------|-------|
| **Document Title** | ScholarSource Scaling Plan |
| **Version** | 1.0 |
| **Date** | December 2024 |
| **Author** | ScholarSource Development Team |
| **Status** | Draft |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current Architecture Analysis](#2-current-architecture-analysis)
3. [Scaling Bottlenecks](#3-scaling-bottlenecks)
4. [Scaling Strategy](#4-scaling-strategy)
5. [Component Changes Required](#5-component-changes-required)
6. [Implementation Phases](#6-implementation-phases)
7. [Technology Choices](#7-technology-choices)
8. [Cost Considerations](#8-cost-considerations)
9. [Monitoring and Metrics](#9-monitoring-and-metrics)
10. [Risk Assessment](#10-risk-assessment)
11. [Appendix: Current Code Analysis](#11-appendix-current-code-analysis)

---

## 1. Executive Summary

This document outlines a comprehensive plan to scale ScholarSource from a single-instance deployment to a horizontally scalable system capable of handling high concurrent loads. The primary focus is on decoupling job execution from the API layer, implementing proper task queuing, and enabling independent scaling of compute-intensive workers.

**Key Goals:**
- Support 10-100x increase in concurrent job processing
- Enable horizontal scaling of API and worker layers independently
- Maintain current functionality and user experience
- Minimize infrastructure costs through efficient resource utilization

**Primary Change Required:**
Migration from thread-based job execution to a distributed task queue architecture with separate worker processes.

---

## 2. Current Architecture Analysis

### 2.1 Current System Components

```
┌─────────────┐
│   Frontend  │ (React/Vite - Cloudflare Pages)
└──────┬──────┘
       │ HTTP/REST
┌──────▼─────────────────────────────────────────────┐
│          FastAPI Backend (Single Instance)         │
│  ┌──────────────────────────────────────────────┐  │
│  │ API Endpoints                                │  │
│  │  - /api/submit (job submission)              │  │
│  │  - /api/status/{job_id} (status polling)     │  │
│  │  - /api/cancel/{job_id} (job cancellation)   │  │
│  └──────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────┐  │
│  │ Job Execution (Threading)                    │  │
│  │  - run_crew_async() creates Thread           │  │
│  │  - Each thread runs CrewAI execution         │  │
│  │  - Threads are daemon (no cleanup)           │  │
│  └──────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────┐  │
│  │ Rate Limiting (In-Memory)                    │  │
│  │  - Single-instance only                      │  │
│  │  - Redis support exists but not required     │  │
│  └──────────────────────────────────────────────┘  │
└──────┬─────────────────────────────────────────────┘
       │
┌──────▼─────────────────────────────────────────────┐
│            Supabase PostgreSQL                     │
│  - jobs table (job status, results)                │
│  - course_cache table (analysis cache)             │
└────────────────────────────────────────────────────┘
```

### 2.2 Current Execution Flow

1. **Job Submission** (`main.py:92-156`)
   - Client POSTs to `/api/submit`
   - Rate limiting checked (in-memory)
   - Job created in Supabase
   - `run_crew_async()` called immediately
   - Returns job_id immediately

2. **Job Execution** (`crew_runner.py:37-66`)
   - Creates a new daemon thread
   - Thread creates new event loop
   - Runs `_run_crew_worker()` asynchronously
   - Thread completes when job finishes (minutes to hours)

3. **Status Polling** (`main.py:159-205`)
   - Client GETs `/api/status/{job_id}`
   - Direct database query
   - Returns current job status

### 2.3 Resource Characteristics

**CrewAI Job Execution:**
- **Duration:** 2-10 minutes per job (variable)
- **CPU:** Medium-high (LLM API calls, web scraping)
- **Memory:** 100-500 MB per job (varies with input size)
- **I/O:** Network-heavy (API calls, web requests)
- **Concurrency:** Limited by thread count and memory

**API Layer:**
- **Latency:** <100ms for status checks
- **Throughput:** High (stateless, simple DB queries)
- **Resource Usage:** Low (mostly I/O wait)

---

## 3. Scaling Bottlenecks

### 3.1 Critical Bottlenecks

#### 3.1.1 Thread-Based Execution Model
**Location:** `backend/crew_runner.py:53-66`

**Problem:**
- Jobs run in daemon threads within the API process
- Limited by Python GIL and thread overhead
- No process isolation (memory leaks affect entire API)
- Cannot scale workers independently
- Thread exhaustion under load

**Impact:**
- Maximum ~10-50 concurrent jobs per instance
- API becomes unresponsive under high job load
- Single point of failure for both API and job processing

#### 3.1.2 No Task Queue
**Location:** `backend/main.py:140`

**Problem:**
- Jobs start immediately upon submission
- No queuing or prioritization mechanism
- No backpressure handling
- Cannot distribute work across multiple workers

**Impact:**
- Overwhelming system under sudden load spikes
- No way to throttle job execution
- Cannot implement job priorities or scheduling

#### 3.1.3 In-Memory Rate Limiting
**Location:** `backend/rate_limiter.py:31-36`

**Problem:**
- Rate limiting stored in process memory
- Does not work across multiple API instances
- Warning already present in code (line 36)

**Impact:**
- Cannot horizontally scale API layer
- Rate limits reset on each instance
- Inconsistent rate limiting behavior

#### 3.1.4 Resource Contention
**Location:** Entire `backend/crew_runner.py`

**Problem:**
- Long-running CrewAI tasks compete with API requests
- CPU and memory contention
- Database connections shared between API and workers

**Impact:**
- Degraded API performance during job execution
- Potential connection pool exhaustion
- Unpredictable resource usage patterns

### 3.2 Secondary Bottlenecks

#### 3.2.1 Database Connection Management
- No explicit connection pooling configuration
- Supabase client may handle pooling, but not verified
- Potential connection exhaustion under high load

#### 3.2.2 Cache Storage
- Cache stored in Supabase (good for consistency)
- May become bottleneck if cache misses spike
- No in-memory hot cache layer

#### 3.2.3 Status Polling Pattern
- Clients poll `/api/status/{job_id}` repeatedly
- No WebSocket or SSE for real-time updates
- Creates unnecessary database load
- Works but not optimal for high concurrency

---

## 4. Scaling Strategy

### 4.1 Target Architecture

```
┌─────────────┐
│   Frontend  │ (React/Vite - Cloudflare Pages)
└──────┬──────┘
       │ HTTP/REST
┌──────▼─────────────────────────────────────────┐
│        FastAPI API Layer (Multiple Instances)  │
│  ┌──────────────────────────────────────────┐  │
│  │ API Endpoints (Stateless)                │  │
│  │  - /api/submit → Enqueue job to Celery   │  │
│  │  - /api/status/{job_id} → DB query       │  │
│  │  - /api/cancel/{job_id} → Cancel Celery  │  │
│  └──────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────┐  │
│  │ Rate Limiting (Redis-backed)             │  │
│  │  - Shared state across API instances     │  │
│  └──────────────────────────────────────────┘  │
└──────┬─────────────────────────────────────────┘
       │
       │ Celery Task Enqueue (via Redis)
       │
┌──────▼─────────────────────────────────────────┐
│      Redis (Celery Message Broker/Backend)     │
│  ┌──────────────────────────────────────────┐  │
│  │ Celery Task Queue: Stores enqueued jobs  │  │
│  │ Rate Limit State: Shared across instances │  │
│  │ Result Backend: Optional task results    │  │
│  └──────────────────────────────────────────┘  │
└──────┬─────────────────────────────────────────┘
       │
       │ Workers consume jobs from queue
       │ (Workers continuously poll Redis for new jobs)
       │
┌──────▼─────────────────────────────────────────┐
│   Celery Worker Processes (Multiple Instances) │
│  ┌──────────────────────────────────────────┐  │
│  │ Worker 1: Polls Redis, executes jobs      │  │
│  │ Worker 2: Polls Redis, executes jobs      │  │
│  │ Worker N: Polls Redis, executes jobs      │  │
│  │  - Each worker runs CrewAI execution      │  │
│  │  - Updates job status in DB               │  │
│  │  - Process isolation (separate from API)  │  │
│  └──────────────────────────────────────────┘  │
└──────┬─────────────────────────────────────────┘
       │
       │ Job Status Updates
       │
┌──────▼─────────────────────────────────────────┐
│            Supabase PostgreSQL                 │
│  - jobs table (job status, results)            │
│  - course_cache table (analysis cache)        │
└────────────────────────────────────────────────┘
```

**Key Architecture Changes:**
- **API Layer**: Stateless, can scale horizontally. Jobs are enqueued to Celery instead of executing immediately.
- **Redis**: Serves as Celery's message broker (task queue) and result backend. Also stores shared rate limit state.
- **Celery Workers**: Separate processes that consume jobs from Redis queue and execute CrewAI tasks independently.
- **Process Isolation**: API and workers run in separate processes, enabling independent scaling and fault isolation.

### 4.2 Scaling Dimensions

#### Horizontal Scaling
- **API Layer:** Scale to N instances behind load balancer
- **Worker Layer:** Scale to M instances based on queue depth
- **Independent Scaling:** Scale API and workers separately based on demand

#### Vertical Scaling (Limited)
- Workers can use larger instances for memory-intensive jobs
- API layer remains lightweight

### 4.3 Scaling Targets

**Phase 1 (Short-term):**
- Support 10-20 concurrent job executions
- Handle 100-500 requests/minute
- 2-3 API instances, 2-5 worker instances

**Phase 2 (Medium-term):**
- Support 50-100 concurrent job executions
- Handle 1000+ requests/minute
- 3-5 API instances, 5-20 worker instances

**Phase 3 (Long-term):**
- Support 200+ concurrent job executions
- Handle 5000+ requests/minute
- 5-10 API instances, 20-100 worker instances
- Advanced features (priorities, scheduling, batching)

---

## 5. Component Changes Required

### 5.1 Critical Changes

#### 5.1.1 Task Queue Implementation

**Component:** New `backend/queue.py` or use Celery

**Changes:**
- Replace `run_crew_async()` threading with queue enqueue
- Move `_run_crew_worker()` logic to queue worker task
- Implement job cancellation via queue API
- Add queue monitoring and metrics

**Code Changes:**
- `backend/main.py:140`: Change from `run_crew_async()` to `enqueue_job()`
- `backend/crew_runner.py`: Refactor `_run_crew_worker()` as queue task
- New worker process: Consume from queue, execute jobs

**Dependencies:**
- Add `redis` Python package
- Add `celery` package

#### 5.1.2 Worker Process Separation

**Component:** New `backend/worker.py` or separate worker service

**Changes:**
- Extract job execution logic to standalone worker process
- Worker connects to Redis queue
- Worker updates job status in Supabase
- Handle worker health checks and graceful shutdown

**Deployment:**
- Separate container/service for workers
- Can scale independently from API
- Environment variables for queue configuration

#### 5.1.3 Rate Limiting Redis Migration

**Component:** `backend/rate_limiter.py`

**Changes:**
- Make `REDIS_URL` required (or highly recommended)
- Remove in-memory fallback or keep as development-only
- Update deployment documentation

**Code Changes:**
```python
# backend/rate_limiter.py
REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    raise ValueError("REDIS_URL must be set for multi-instance deployments")

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=REDIS_URL,
    default_limits=["1000/hour"]
)
```

### 5.2 Moderate Changes

#### 5.2.1 Job Cancellation

**Component:** `backend/main.py:208-286` and `backend/crew_runner.py:69-84`

**Changes:**
- Cancel jobs via queue API instead of thread cancellation
- Update `cancel_crew_job()` to interact with queue
- Handle job cancellation in worker process

**Implementation:**
- Celery: Use `revoke()` method
- Update job status in database

#### 5.2.2 Connection Pooling

**Component:** `backend/database.py`

**Changes:**
- Verify Supabase client connection pooling
- Add connection pool configuration if needed
- Monitor connection usage

**Investigation Needed:**
- Check Supabase Python client documentation
- Test connection behavior under load
- May not need changes if client handles pooling

#### 5.2.3 Error Handling and Retries

**Component:** `backend/crew_runner.py` and queue worker

**Changes:**
- Implement job retry logic (queue-level)
- Handle worker failures gracefully
- Dead letter queue for failed jobs
- Improve error reporting

**Queue Features:**
- Celery: Retry policies and error handling
- Configure max retries and backoff

### 5.3 Optional Enhancements

#### 5.3.1 Job Priorities

**Component:** Queue configuration

**Changes:**
- Add priority queues (high, normal, low)
- Update job submission to accept priority
- Worker processes consume priority queues first

**Implementation:**
- Celery: Priority queues or routing

#### 5.3.2 Result Backend

**Component:** Redis result backend

**Changes:**
- Store job results in Redis (temporary)
- Reduce database queries for status checks
- TTL-based expiration

**Trade-off:**
- Faster status checks
- Additional Redis memory usage
- Still need DB for persistence

#### 5.3.3 Monitoring and Observability

**Component:** New monitoring setup

**Changes:**
- Queue monitoring dashboard (Flower)
- Metrics: Queue depth, worker count, job duration
- Alerts for queue buildup or worker failures

---

## 6. Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Goal:** Basic queue-based architecture operational

**Tasks:**

#### 1. [ ] Setup Redis
   - [✅] Add Redis service (Redis Cloud, AWS ElastiCache, or self-hosted)
   - [✅] Add `REDIS_URL` to environment variables
   - [✅] Test Redis connectivity

#### 2. [✅] Choose Queue System
   - [✅] **Selected: Celery** (more features, better for production scaling)
   - [✅] Add dependency: `celery>=5.3.0`
   - [✅] Add `redis>=5.0.0` dependency (already added)

#### 2.1. [✅] Configure Celery
   - [✅] Create `backend/celery_app.py` with Celery configuration
   - [✅] Configure broker (Redis) and result backend
   - [✅] Set task serialization (JSON recommended)
   - [✅] Configure task routing and queue names
   - [✅] Set worker concurrency and prefetch settings
   - [✅] Configure task retry policies and error handling
   - [✅] Add Celery Beat for scheduled tasks (optional)
   - [✅] Test Celery connection and basic task execution

#### 3. [✅] Refactor Crew Runner
   - [✅] Extract `_run_crew_worker()` logic to queue-compatible function (moved to tasks.py)
   - [✅] Remove threading code
   - [✅] Create `run_crew_task(job_id, inputs, bypass_cache)` function
   - [✅] Update `run_crew_async()` to enqueue Celery task
   - [✅] Update `cancel_crew_job()` to use Celery revoke
   - [✅] Test refactored crew runner (all tests passed)

#### 4. [✅] Update Job Submission
   - [✅] Replace `run_crew_async()` with queue enqueue (already done in step 3)
   - [✅] Update `main.py:140` to enqueue job (no changes needed - API compatible)
   - [ ] Test job submission flow with running worker

#### 5. [✅] Create Worker Process
   - [✅] Create worker startup script (`scripts/start_worker.sh`)
   - [✅] Create setup verification script (`scripts/verify_setup.sh`)
   - [✅] Create unified test script (`scripts/test.py` with CLI options)
   - [✅] Update Procfile for Railway deployment (added `worker:` process)
   - [✅] Update `.env.example` with `REDIS_URL` requirement
   - [✅] Update README.md with worker instructions
   - [✅] Organize all scripts into `scripts/` directory
   - [✅] Test worker initialization (verified successfully)

#### 6. [✅] Update Rate Limiting
   - [✅] Make Redis required or highly recommended
   - [✅] Update `rate_limiter.py` to require `REDIS_URL`
   - [✅] Test rate limiting across instances

**Deliverables:**
- ✅ Queue-based job processing implemented (Celery + Redis)
- ✅ Worker startup script and deployment configuration ready
- ✅ Backward-compatible API (no frontend changes needed)
- ✅ All tests passing (refactored runner + Celery config)
- ⏳ Rate limiting using Redis (existing, needs verification)
- ⏳ End-to-end testing with running worker (next step)

**Status:** Steps 1-5 complete! Ready for Phase 2.

**Risk Level:** Medium (core architecture change) - Mitigated through testing and backward compatibility

### Phase 2: Production Hardening (Week 2-3)

**Goal:** Production-ready queue system with error handling

**Tasks:**

#### 7. [ ] Error Handling
   - [ ] Implement job retry logic
   - [ ] Handle worker failures gracefully
   - [ ] Dead letter queue for permanently failed jobs
   - [ ] Improve error messages and logging

#### 8. [ ] Job Cancellation
   - [ ] Update cancellation to work with queue
   - [ ] Test cancellation in various states
   - [ ] Ensure proper cleanup

#### 9. [ ] Connection Management
   - [ ] Verify database connection pooling
   - [ ] Monitor connection usage
   - [ ] Add connection pool configuration if needed

#### 10. [ ] Deployment Configuration
   - [ ] Update deployment scripts/containers
   - [ ] Separate API and worker containers
   - [ ] Update environment variable documentation
   - [ ] Update `Procfile` or deployment config

#### 11. [ ] Monitoring Setup
   - [ ] Add queue monitoring (Flower)
   - [ ] Basic metrics collection
   - [ ] Logging improvements

**Deliverables:**
- Robust error handling
- Production deployment configuration
- Basic monitoring in place
- Documentation updated

**Risk Level:** Low (enhancements to Phase 1)

### Phase 3: Scaling and Optimization (Week 3-4)

**Goal:** Horizontal scaling capabilities

**Tasks:**

#### 12. [ ] Horizontal Scaling Setup
   - [ ] Load balancer configuration for API layer
   - [ ] Multiple worker instances
   - [ ] Auto-scaling policies (if using cloud)

#### 13. [ ] Performance Optimization
   - [ ] Database query optimization
   - [ ] Cache optimization
   - [ ] Connection pool tuning
   - [ ] Worker process optimization

#### 14. [ ] Advanced Features (Optional)
   - [ ] Job priorities
   - [ ] Scheduled jobs
   - [ ] Batch processing
   - [ ] Result backend optimization

#### 15. [ ] Load Testing
   - [ ] Stress testing with multiple workers
   - [ ] Test under various load patterns
   - [ ] Identify and fix bottlenecks
   - [ ] Performance benchmarking

**Deliverables:**
- Scalable deployment
- Load testing results
- Performance benchmarks
- Scaling documentation

**Risk Level:** Low (operational improvements)

---

## 7. Technology Choices

### 7.1 Task Queue: Celery

#### Option: Celery

**Pros:**
- More features (priorities, routing, scheduling)
- Better for complex workflows
- More mature ecosystem
- Better monitoring (Flower)

**Cons:**
- More complex setup and configuration
- Steeper learning curve
- May be overkill for current needs

**Package:** `celery>=5.3.0`


### 7.2 Redis Provider Options

#### Option: Redis Cloud (Recommended for small scale)
- Managed service
- Free tier available
- Easy setup
- Good for getting started

**Recommendation:** Starting with free tier

### 7.3 Deployment Platform Considerations

#### Railway (Current Platform)
- **API Instances:** Can scale horizontally
- **Worker Instances:** Need separate services
- **Redis:** External service required
- **Configuration:** Update Procfile for workers

#### Other Platforms
- **Heroku:** Similar to Railway, separate dynos for workers
- **AWS ECS/Fargate:** Good for containerized deployments
- **Kubernetes:** Most flexible, better for large scale
- **DigitalOcean App Platform:** Simple scaling, good middle ground

---

## 8. Cost Considerations

### 8.1 Infrastructure Costs (Estimated)

#### Current (Single Instance)
- API/Worker: $5-20/month (single instance)
- Database: Supabase free tier or paid
- **Total: ~$10-30/month**

#### Phase 1 (Basic Queue)
- API Instance: $5-10/month
- Worker Instance: $5-10/month
- Redis: $0-10/month (free tier or small instance)
- Database: Same as current
- **Total: ~$15-40/month**

#### Phase 2 (Moderate Scale)
- API Instances (2-3): $15-30/month
- Worker Instances (2-5): $15-50/month
- Redis: $10-30/month
- Database: Supabase paid tier if needed
- **Total: ~$50-150/month**

#### Phase 3 (High Scale)
- API Instances (5-10): $50-150/month
- Worker Instances (10-50): $100-500/month
- Redis: $30-100/month
- Database: Higher tier if needed
- Load Balancer: $10-50/month
- **Total: ~$200-800/month**

### 8.2 Cost Optimization Strategies

1. **Auto-scaling:** Scale workers based on queue depth
2. **Spot Instances:** Use cheaper compute for workers (if supported)
3. **Reserved Instances:** Commit to instances for predictable workloads
4. **Cache Hit Rate:** Maximize cache to reduce worker load
5. **Resource Right-sizing:** Monitor and adjust instance sizes

---

## 9. Monitoring and Metrics

### 9.1 Key Metrics to Track

#### Queue Metrics
- **Queue Depth:** Number of pending jobs
- **Job Duration:** Average and P95/P99 job execution time
- **Job Success Rate:** Percentage of successful completions
- **Job Failure Rate:** Percentage of failed jobs
- **Worker Count:** Active worker instances

#### API Metrics
- **Request Rate:** Requests per second
- **Response Time:** API endpoint latency
- **Error Rate:** 4xx and 5xx error rates
- **Rate Limit Hits:** Number of rate-limited requests

#### Resource Metrics
- **CPU Usage:** Per instance/worker
- **Memory Usage:** Per instance/worker
- **Database Connections:** Active connections
- **Redis Memory:** Memory usage and evictions

### 9.2 Monitoring Tools

#### Queue Monitoring
- **Flower:** Celery monitoring (if using Celery)
- **Custom Dashboard:** Build with queue metrics API

#### Application Monitoring
- **Logging:** Structured logging (already in place)
- **APM:** Consider Sentry, DataDog, or New Relic
- **Uptime Monitoring:** External service (UptimeRobot, Pingdom)

#### Infrastructure Monitoring
- **Platform Monitoring:** Railway/Heroku metrics
- **Redis Monitoring:** Redis Cloud or provider metrics
- **Database Monitoring:** Supabase dashboard

### 9.3 Alerting

**Critical Alerts:**
- Queue depth exceeds threshold (e.g., >100 jobs)
- Worker failure rate > 5%
- API error rate > 1%
- Redis unavailable
- Database connection errors

**Warning Alerts:**
- Queue depth > 50 jobs
- Average job duration increasing
- High memory usage
- Rate limit hit rate > 10%

---

## 10. Risk Assessment

### 10.1 Technical Risks

#### Risk: Queue System Failure
- **Impact:** High - Jobs cannot be processed
- **Probability:** Low - Redis is reliable
- **Mitigation:** Redis high availability, monitoring, backups

#### Risk: Worker Process Crashes
- **Impact:** Medium - Jobs may be lost or delayed
- **Probability:** Medium - Long-running processes can fail
- **Mitigation:** Job retries, worker health checks, auto-restart

#### Risk: Database Connection Exhaustion
- **Impact:** High - API and workers unable to access DB
- **Probability:** Medium - Under high load
- **Mitigation:** Connection pooling, connection limits, monitoring

#### Risk: Redis Memory Exhaustion
- **Impact:** High - Queue operations fail
- **Probability:** Low-Medium - Depends on queue depth
- **Mitigation:** Monitor Redis memory, set eviction policies, scale Redis

#### Risk: Migration Complexity
- **Impact:** Medium - Potential downtime or bugs
- **Probability:** Medium - Significant architecture change
- **Mitigation:** Thorough testing, phased rollout, feature flags

### 10.2 Operational Risks

#### Risk: Increased Operational Complexity
- **Impact:** Medium - More components to manage
- **Probability:** High - More moving parts
- **Mitigation:** Good documentation, automation, monitoring

#### Risk: Cost Overruns
- **Impact:** Medium - Higher infrastructure costs
- **Probability:** Medium - Scaling increases costs
- **Mitigation:** Cost monitoring, auto-scaling, resource optimization

#### Risk: Performance Regression
- **Impact:** High - Slower job processing
- **Probability:** Low - Queue adds minimal overhead
- **Mitigation:** Load testing, performance benchmarks, optimization


---

## 12. Local Development vs Production Deployment

### 12.1 Local Development Setup

**Purpose:** Run the full stack locally for development and testing.

**Architecture:**
```
Terminal 1: API Server (with hot reload)
Terminal 2: Celery Worker (background job processor)
Terminal 3: Frontend Dev Server (React with Vite)
Redis: External service (Redis Cloud) or local Docker
```

**How to Run:**

```bash
# Terminal 1: API Server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Celery Worker
./scripts/start_worker.sh

# Terminal 3: Frontend
cd web && npm run dev
```

**Key Characteristics:**
- **Manual Start:** You manually start each process in separate terminals
- **Hot Reload:** API restarts on code changes (`--reload` flag)
- **Port 8000:** API runs on fixed port 8000 for local testing
- **Visibility:** See all logs in separate terminal windows
- **Environment:** Uses `.env` file for configuration
- **Redis:** Can use Redis Cloud free tier or local Redis in Docker

**When to Use:**
- Active development and debugging
- Running tests with `scripts/test.py`
- Experimenting with new features
- Local testing before pushing to production

---

### 12.2 Production Deployment (Railway)

**Purpose:** Run the full stack in production with automatic process management.

**Architecture:**
```
Railway Service (ScholarSource):
├── web process (from Procfile)
│   └── uvicorn backend.main:app --port $PORT
└── worker process (from Procfile)
    └── celery -A backend.celery_app worker

Redis: External Redis Cloud service
Frontend: Separate Cloudflare Pages deployment
```

**How it Works:**

1. **Procfile Defines Processes:**
   ```
   web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
   worker: celery -A backend.celery_app worker --loglevel=info --queues=crew_jobs,default --concurrency=2
   ```

2. **Railway Auto-starts Both:**
   - Reads Procfile on deployment
   - Starts `web` process automatically (public HTTP endpoint)
   - Starts `worker` process automatically (background, no public port)

3. **Railway Manages:**
   - Assigns dynamic port via `$PORT` environment variable
   - Routes external traffic to the `web` process
   - Restarts processes if they crash
   - Handles scaling (add more instances)

**Key Characteristics:**
- **Automatic Start:** Railway starts both processes from Procfile
- **No Hot Reload:** Restart deployment to pick up code changes
- **Dynamic Port:** Railway assigns port via `$PORT` env var
- **Single View:** Logs combined in Railway dashboard
- **Environment:** Uses Railway environment variables (configured in dashboard)
- **Redis:** Must be external service (Redis Cloud recommended)

**When to Use:**
- Production traffic
- After code is tested locally
- When you need high availability
- When you need to scale horizontally

---

**Note:** Detailed Railway deployment instructions, troubleshooting, and scaling strategies have been moved to `docs/Deployment_Plan.md` (Part 2 and Part 10) to avoid duplication. This document focuses on scaling architecture and implementation phases.

---

## Conclusion

Scaling ScholarSource requires migrating from a thread-based architecture to a queue-based distributed system. The primary changes are:

1. **Task Queue:** Implement Celery for job processing
2. **Worker Separation:** Move job execution to separate worker processes
3. **Redis Integration:** Use Redis for queue and rate limiting
4. **Horizontal Scaling:** Enable independent scaling of API and workers

The recommended approach is to start with **Celery** (chosen), implement in **phases**, and focus on **monitoring** from the beginning. This will enable the system to handle 10-100x more concurrent jobs while maintaining reliability and reasonable costs.

**Estimated Timeline:** 3-4 weeks for full implementation
**Estimated Cost Increase:** $10-50/month for Phase 1, scaling up with usage
**Risk Level:** Medium (significant architecture change, but well-understood patterns)

**Current Status:** Phase 1 Steps 1-5 Complete ✅
- Celery configured and tested
- Worker process created and tested
- Ready for Railway deployment

---

**Document Status:** Implementation in progress - Phase 1 near completion
