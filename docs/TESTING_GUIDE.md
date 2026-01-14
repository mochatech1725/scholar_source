# ScholarSource Testing Guide

Comprehensive guide for running, writing, and maintaining tests for the ScholarSource application.

---

## Table of Contents

1. [Quick Start](#-quick-start)
2. [Overview](#-overview)
3. [Testing Stack](#-testing-stack)
4. [Test Suite Overview](#-test-suite-overview)
5. [Backend Testing](#-backend-testing)
6. [Frontend Testing](#-frontend-testing)
7. [Running Tests](#-running-tests)
8. [Installation & Setup](#-installation--setup)
9. [CI/CD Integration](#-cicd-integration)
10. [Watch Mode](#-watch-mode)
11. [What Was Created](#-what-was-created)
12. [Cache Testing](#-cache-testing)
13. [Remaining Tasks](#-remaining-tasks)
14. [Next Steps](#-next-steps)
15. [Resources](#-resources)
16. [Summary](#-summary)

---

## 🚀 Quick Start

```bash
# Install backend test dependencies
pip install -r requirements-dev.txt

# Install frontend test dependencies
cd web
npm install -D vitest @vitest/ui @testing-library/react \
  @testing-library/jest-dom @testing-library/user-event jsdom msw

# Add test scripts to web/package.json (see section below)

# Run all tests
cd ..
./scripts/test-all.sh
```

---

## 📋 Overview

This document provides a comprehensive testing strategy and practical guide for the ScholarSource application, covering both backend (FastAPI/Python) and frontend (React/Vite) components.

**Current State:** 155+ test cases implemented
**Goal:** Maintain robust automated testing with unit tests, integration tests, and E2E tests

---

## 🧬 Testing Stack

### Backend (Python/FastAPI)

| Tool | Version | Purpose | Why |
|------|---------|---------|-----|
| **pytest** | ≥7.4.0 | Test runner and framework | Industry standard, fixture support, parametrization |
| **pytest-asyncio** | ≥0.21.0 | Async test support | FastAPI uses async endpoints |
| **pytest-mock** | ≥3.11.0 | Mocking external dependencies | Mock external dependencies (OpenAI, CrewAI) |
| **httpx** | ≥0.24.0 | HTTP client for testing FastAPI | Official recommendation for testing FastAPI |
| **fakeredis** | ≥2.19.0 | Mock Redis for rate limiting | Test rate limiting without real Redis |
| **faker** | ≥20.0.0 | Generate fake test data | Generate realistic test data |

**Installation:**
```bash
pip install -r requirements-dev.txt
```

### Frontend (React/Vite)

| Tool | Version | Purpose | Why |
|------|---------|---------|-----|
| **Vitest** | ≥1.0.0 | Fast, Vite-native test runner | Vite-native, fast, Jest-compatible API |
| **@vitest/ui** | ≥1.0.0 | Visual test runner UI | Visual test runner (optional) |
| **@testing-library/react** | ≥14.0.0 | User-centric component testing | User-centric testing approach |
| **@testing-library/jest-dom** | ≥6.1.0 | Custom DOM matchers | Better assertions for DOM testing |
| **@testing-library/user-event** | ≥14.5.0 | User interaction simulation | User interaction simulation |
| **MSW** | ≥2.0.0 | Mock Service Worker for API mocking | Intercept network requests |
| **jsdom** | ≥23.0.0 | DOM implementation for Node.js | DOM implementation for Node.js |

**Installation:**
```bash
cd web
npm install -D vitest @vitest/ui @testing-library/react \
  @testing-library/jest-dom @testing-library/user-event \
  jsdom msw
```

---

## 📁 Test Suite Overview

### Backend Tests (120+ test cases)

```
tests/
├── conftest.py                     # Shared fixtures and mocks
├── unit/                           # Unit tests (fast, isolated)
│   ├── test_markdown_parser.py     # Markdown parsing (60+ tests)
│   ├── test_models.py              # Pydantic validation
│   ├── test_cache.py               # Cache functionality
│   └── test_rate_limiter.py        # Rate limiting
├── integration/                    # Integration tests
│   ├── test_api_endpoints.py       # API endpoint tests (40+ tests)
│   └── test_job_lifecycle.py       # Job workflow tests
└── e2e/                            # End-to-end tests (future)
```

### Frontend Tests (35+ test cases)

```
web/src/
├── test/
│   ├── setup.js                    # Vitest configuration
│   └── mocks/
│       ├── handlers.js             # MSW API handlers
│       └── server.js               # MSW server setup
├── components/
│   ├── ResultCard.test.jsx         # Component tests
│   ├── StatusMessage.test.jsx
│   ├── ConfirmDialog.test.jsx
│   └── Hero.test.jsx
└── api/
    └── client.test.js              # API client tests
```

### Test Statistics
- **Total Tests**: 155+ test cases
- **Mock Systems**: Complete Supabase and CrewAI mocks, MSW for API

---

## 🔧 Backend Testing

### Test Structure

**Backend Test Directory Organization:**

- `tests/` - Root test directory
  - `conftest.py` - Shared fixtures
  - `unit/` - Unit tests
    - `test_markdown_parser.py` - Markdown parsing logic
    - `test_models.py` - Pydantic model validation
    - `test_cache.py` - Cache key generation, storage
    - `test_rate_limiter.py` - Rate limit logic (with fakeredis)
  - `integration/` - Integration tests
    - `test_api_endpoints.py` - FastAPI endpoint tests
    - `test_job_lifecycle.py` - Submit → Poll → Complete flow
    - `test_crew_runner.py` - Crew execution (mocked)
  - `e2e/` - End-to-end tests
    - `test_full_workflow.py` - End-to-end scenarios

### Unit Tests

#### `tests/unit/test_markdown_parser.py`

**What to test:**
- ✅ Parse numbered resources correctly
- ✅ Parse link sections correctly
- ✅ Filter out ERROR resources
- ✅ Filter out excluded domains
- ✅ Extract textbook information
- ✅ Handle malformed markdown gracefully

Tests should cover parsing numbered resources, filtering error resources, excluding domains, extracting textbook information, and detecting error indicators using parameterized tests. The test class `TestMarkdownParser` should verify that `parse_markdown_to_resources` correctly extracts resources from various markdown formats, filters out resources with "ERROR" in their fields, respects excluded domains, and extracts textbook metadata.

#### `tests/unit/test_models.py`

**What to test:**
- ✅ Pydantic model validation
- ✅ Empty string → None conversion
- ✅ Invalid inputs rejected
- ✅ Optional field handling

Tests should verify that `CourseInputRequest` accepts valid course URLs, converts empty strings to None, accepts lists of desired resource types, and that optional fields default to None. The `TestResourceModel` class should verify that valid resources can be created with all required fields, and that missing required fields raise Pydantic ValidationError.

#### `tests/unit/test_cache.py`

**What to test:**
- ✅ Cache key generation
- ✅ Cache storage and retrieval
- ✅ TTL expiration logic
- ✅ Cache invalidation

#### `tests/unit/test_rate_limiter.py`

**What to test:**
- ✅ Rate limit enforcement
- ✅ In-memory vs Redis storage selection
- ✅ Error response format
- ✅ Rate limit headers

Tests should verify that the rate limiter uses in-memory storage by default when REDIS_URL is not set, and that rate limit error responses return proper 429 status codes with retry_after information. The `TestRateLimiter` class should test rate limiting logic including error response format.

### Integration Tests

#### `tests/integration/test_api_endpoints.py`

**What to test:**
- ✅ All API endpoints respond correctly
- ✅ Request/response contracts
- ✅ Error handling (400, 404, 429, 500)
- ✅ Rate limiting enforcement

Tests should verify that all API endpoints respond correctly, including the health check endpoint returning 200 with healthy status, the submit endpoint accepting valid course URLs and returning job_id, rejecting empty payloads with 400, rejecting invalid URL formats with 422, and enforcing rate limits. The status endpoint should return pending/running status for new jobs and 404 for nonexistent jobs. The cancel endpoint should successfully cancel running jobs.

#### `tests/integration/test_job_lifecycle.py`

**What to test:**
- ✅ Full job lifecycle (submit → running → completed)
- ✅ Job state transitions
- ✅ Cancellation during execution

Tests should verify the complete job lifecycle, including that jobs progress through states (pending → running → completed) when crew execution is mocked to return quickly, and that cancelled jobs stop execution and show cancelled status. Tests should poll status until completion with appropriate timeouts.

### Fixtures (`tests/conftest.py`)

**Shared test fixtures:**

The `conftest.py` file should include fixtures for setting up test environment variables (suppressing logs, using in-memory storage), creating FastAPI test clients, and mocking successful and failed crew executions. Fixtures should use appropriate scopes (session for environment setup, function for test clients).

**Available Fixtures:**
- `mock_supabase` - Complete Supabase client mock
- `mock_crew_success` - CrewAI returns valid markdown
- `mock_crew_failure` - CrewAI raises exception
- `mock_crew_with_errors` - CrewAI returns markdown with errors

---

## 🎨 Frontend Testing

### Test Structure

**Frontend Test File Organization:**

- `web/src/components/` - Component test files
  - `Hero.test.jsx`, `ResultCard.test.jsx`, `InlineSearchStatus.test.jsx`
  - `ui/Button.test.jsx`, `ui/TextInput.test.jsx`
- `web/src/pages/` - Page tests
  - `HomePage.test.jsx`
- `web/src/api/` - API client tests
  - `client.test.js`
- `web/src/test/` - Test configuration and mocks
  - `setup.js` - Test configuration
  - `mocks/handlers.js` - MSW API mock handlers
- `web/vitest.config.js` - Vitest configuration
- `web/package.json` - Package dependencies

### Test Configuration

#### `web/vitest.config.js`

The Vitest configuration should include React plugin, set globals to true, use jsdom environment, and specify setup files.

#### `web/src/test/setup.js`

The test setup file should extend Vitest's expect with jest-dom matchers, clean up after each test, and mock window.matchMedia for responsive tests. The setup file is imported by Vitest before running tests.

---

## 🧪 Running Tests

### All Tests

```bash
# Run both backend and frontend tests
./scripts/test-all.sh
```

### Backend Tests

```bash
# Run all backend tests
./scripts/test-backend.sh

# Or directly with pytest
pytest

# Run specific test file
pytest tests/unit/test_markdown_parser.py

# Run specific test
pytest tests/unit/test_models.py::TestCourseInputRequest::test_valid_course_url_input

# Run with verbose output
pytest -v

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run tests matching pattern
pytest -k "test_parse"

# Run only fast tests (skip slow integration tests)
pytest -m "not slow"
```

### Frontend Tests

```bash
# Run all frontend tests
./scripts/test-frontend.sh

# Or directly with npm
cd web
npm test

# Run with UI
npm run test:ui

# Watch mode
npm test -- --watch

# Run specific test file
npm test -- ResultCard.test.jsx
```

---

## 📦 Installation & Setup

### 1. Install Dependencies

**Backend:**
```bash
pip install -r requirements-dev.txt
```

**Frontend:**
```bash
cd web
npm install -D vitest @vitest/ui @testing-library/react \
  @testing-library/jest-dom @testing-library/user-event \
  jsdom msw
```

### 2. Add Scripts to package.json

Add these scripts to `web/package.json`:

```json
{
  "scripts": {
    "test": "vitest",
    "test:ui": "vitest --ui",
    "test:run": "vitest run"
  }
}
```

### 3. Make Scripts Executable

```bash
chmod +x scripts/*.sh
```

---
## 🚦 Continuous Integration

### GitHub Actions Workflows

Tests run automatically on every push and pull request. DISABLED FOR NOW

**`.github/workflows/test.yml`:**
- Backend tests (Python 3.12)
- Frontend tests (Node.js 18)
- Linting (black, isort, flake8, ESLint)

The GitHub Actions workflow should trigger on pushes and pull requests to main branch. It should include two jobs: backend-tests (set up Python 3.12, install dependencies, run pytest) and frontend-tests (set up Node.js 18, install dependencies, run tests). Both jobs should run on ubuntu-latest.

---

## 📈 Watch Mode

### Backend (pytest-watch)

```bash
# Install pytest-watch
pip install pytest-watch

# Run in watch mode
ptw
```

### Frontend (Vitest)

```bash
cd web
npm test -- --watch
```

---


## 📚 What Was Created

### Scripts & CI/CD (5 files)
- `scripts/test-backend.sh` - Backend runner
- `scripts/test-frontend.sh` - Frontend runner
- `scripts/test-all.sh` - Run all tests
- `.github/workflows/test.yml` - Main CI workflow
- `TESTING_GUIDE.md` - This file

**Total: 25 files, 155+ test cases**

---

## 🗄️ Cache Testing

This section covers testing strategies for the cache implementation. The cache system stores course analysis results to speed up subsequent requests for the same course.

### Test Plan

#### Test Cache Hit/Miss

1. Submit a course URL (e.g., Northwestern Engineering Mechanics page)
2. Wait for completion - should take ~1-2 minutes (cache miss)
3. Submit the SAME course URL again
4. Should complete much faster if using cached analysis

#### Test Force Refresh

1. Submit a course URL with "Force refresh" unchecked
2. Wait for completion
3. Submit SAME course URL with "Force refresh" CHECKED
4. Should bypass cache and run fresh analysis

#### Test Config Invalidation

1. Submit a course URL
2. Wait for completion (creates cache entry)
3. Modify `agents.yaml` or `tasks.yaml` (add a comment)
4. Submit SAME course URL again
5. Should be cache miss (config hash changed)

#### Test Cache Stats

```python
from backend.cache import get_cache_stats

stats = get_cache_stats()
print(stats)
# Expected output:
# {
#   'total_entries': 5,
#   'valid_entries': 5,  # All match current config hash
#   'stale_entries': 0,
#   'config_hash': 'a7f3c2e1...',
#   'by_type': {
#     'analysis': 5,
#     'full': 0
#   }
# }
```

### Testing Checklist

- [✅] Test cache hit scenario
- [ ] Test cache miss scenario
- [ ] Test force refresh functionality
- [ ] Test config invalidation
- [ ] Test cache stats function
- [ ] Verify TTL expiration works correctly

---

## 📋 Remaining Tasks

The following tasks from the original testing plan are still pending:

### High Priority
- [ ] **Add HomePage integration test** - Test the full user flow from form submission to results display
  - Location: `web/src/pages/HomePage.test.jsx`
  - Should test: Form validation, job submission, status polling, results rendering, error handling

### Medium Priority
- [ ] **Add E2E test** - Full workflow test (submit → poll → results)
  - Location: `tests/e2e/test_full_workflow.py`
  - Should test: Complete end-to-end flow without mocks (or minimal mocks)
  - Consider using Playwright or Cypress for browser-based E2E tests

### Low Priority

---

## 🎓 Next Steps

1. **Run Tests**: `./scripts/test-all.sh`
2. **Complete Remaining Tasks**: See [Remaining Tasks](#-remaining-tasks) section above
3. **Add More Tests**: Expand test coverage for edge cases
4. **E2E Tests**: Implement full workflow E2E test
5. **Visual Tests**: Consider adding visual regression testing
6. **Performance**: Benchmark critical paths

---

## 📖 Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [MSW Documentation](https://mswjs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)

---

## ✅ Summary

This comprehensive testing suite provides:

✅ **155+ test cases** covering backend and frontend
✅ **Complete mock systems** for Supabase, CrewAI, and API endpoints
✅ **CI/CD integration** with GitHub Actions
✅ **Best practices** for maintainable, reliable tests

By following this guide, you'll have:
- Confidence in code changes (catch regressions early)
- Faster development (tests document expected behavior)
- Better code quality (tests encourage modular design)
- Easier onboarding (tests serve as documentation)

**Next Steps:** Review this guide, then run tests and continue adding more test cases! 🚀
