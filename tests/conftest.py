"""
Shared pytest fixtures for ScholarSource tests.

This module provides common test fixtures, mocks, and utilities
used across unit, integration, and E2E tests.
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient


# ==============================================================================
# Environment Setup
# ==============================================================================

@pytest.fixture(scope="session", autouse=True)
def test_env():
    """Set up test environment variables."""
    # Suppress logs during tests
    os.environ["LOG_LEVEL"] = "ERROR"

    # Use in-memory rate limiting for tests (not Redis)
    os.environ.pop("REDIS_URL", None)
    os.environ["ALLOW_IN_MEMORY_RATE_LIMIT"] = "true"

    # Set test Supabase credentials (mocked, not real)
    os.environ["SUPABASE_URL"] = "https://test.supabase.co"
    os.environ["SUPABASE_ANON_KEY"] = "test-anon-key"

    # Set test API keys
    os.environ["OPENAI_API_KEY"] = "test-openai-key"
    os.environ["SERPER_API_KEY"] = "test-serper-key"

    # Crew configuration
    os.environ["MAX_CREW_ITERATIONS"] = "5"

    yield

    # Cleanup (optional)


# ==============================================================================
# FastAPI Test Client
# ==============================================================================

@pytest.fixture
def client():
    """FastAPI test client."""
    from backend.main import app
    return TestClient(app)


# ==============================================================================
# Mock Supabase Client
# ==============================================================================

class MockSupabaseClient:
    """Mock Supabase client for testing."""

    def __init__(self):
        self.jobs_data: Dict[str, Dict[str, Any]] = {}

    def table(self, table_name: str):
        """Return table mock."""
        if table_name == "jobs":
            return MockJobsTable(self.jobs_data)
        else:
            raise ValueError(f"Unknown table: {table_name}")


class MockJobsTable:
    """Mock jobs table."""

    def __init__(self, data: Dict[str, Dict[str, Any]]):
        self.data = data

    def insert(self, values: Dict[str, Any]):
        """Insert job."""
        job_id = values.get("id") or str(uuid.uuid4())
        values["id"] = job_id
        self.data[job_id] = values
        return MockExecute({"data": [values], "error": None})

    def select(self, *args):
        """Select query."""
        return MockSelectQuery(self.data)

    def update(self, values: Dict[str, Any]):
        """Update query."""
        return MockUpdateQuery(self.data, values)


class MockSelectQuery:
    """Mock select query."""

    def __init__(self, data: Dict[str, Dict[str, Any]]):
        self.data = data
        self.filters = {}

    def eq(self, column: str, value: Any):
        """Filter by equality."""
        self.filters[column] = value
        return self

    def single(self):
        """Execute single result query."""
        for item in self.data.values():
            match = all(item.get(k) == v for k, v in self.filters.items())
            if match:
                return MockExecute({"data": item, "error": None})
        return MockExecute({"data": None, "error": {"message": "Not found"}})

    def execute(self):
        """Execute query."""
        results = [
            item for item in self.data.values()
            if all(item.get(k) == v for k, v in self.filters.items())
        ]
        return MockExecute({"data": results, "error": None})


class MockUpdateQuery:
    """Mock update query."""

    def __init__(self, data: Dict[str, Dict[str, Any]], values: Dict[str, Any]):
        self.data = data
        self.values = values
        self.filters = {}

    def eq(self, column: str, value: Any):
        """Filter by equality."""
        self.filters[column] = value
        return self

    def execute(self):
        """Execute update."""
        for item in self.data.values():
            match = all(item.get(k) == v for k, v in self.filters.items())
            if match:
                item.update(self.values)
                return MockExecute({"data": [item], "error": None})
        return MockExecute({"data": [], "error": {"message": "Not found"}})


class MockExecute:
    """Mock query execution result."""

    def __init__(self, result: Dict[str, Any]):
        self.data = result.get("data")
        self.error = result.get("error")


@pytest.fixture
def mock_supabase(mocker):
    """Mock Supabase client."""
    mock_client = MockSupabaseClient()
    mocker.patch("backend.database.get_supabase_client", return_value=mock_client)
    return mock_client


# ==============================================================================
# Mock CrewAI
# ==============================================================================

@pytest.fixture
def mock_crew_success(mocker):
    """Mock successful CrewAI execution."""
    mock_result = Mock()
    mock_result.raw = """
**Textbook:** Introduction to Algorithms, 4th ed., by Cormen, Leiserson, Rivest, and Stein

**1. MIT OpenCourseWare - Algorithm Design** (Type: Lecture Notes)
- **Link:** https://ocw.mit.edu/courses/algorithms
- **Source:** MIT OpenCourseWare
- **What it covers:** Comprehensive algorithm design and analysis

**2. VisuAlgo - Algorithm Visualizations** (Type: Interactive Tool)
- **Link:** https://visualgo.net/en
- **Source:** National University of Singapore
- **What it covers:** Visual learning of data structures and algorithms
"""

    mock_crew_class = mocker.patch("backend.crew_runner.ScholarSource")
    mock_crew_instance = Mock()
    mock_crew_instance.crew().kickoff_async = AsyncMock(return_value=mock_result)
    mock_crew_class.return_value = mock_crew_instance

    return mock_crew_class


@pytest.fixture
def mock_crew_failure(mocker):
    """Mock failed CrewAI execution."""
    mock_crew_class = mocker.patch("backend.crew_runner.ScholarSource")
    mock_crew_instance = Mock()
    mock_crew_instance.crew().kickoff_async = AsyncMock(
        side_effect=Exception("CrewAI execution failed")
    )
    mock_crew_class.return_value = mock_crew_instance

    return mock_crew_class


@pytest.fixture
def mock_crew_with_errors(mocker):
    """Mock CrewAI execution with error resources."""
    mock_result = Mock()
    mock_result.raw = """
**1. Valid Resource**
- **Link:** https://example.com/valid
- **What it covers:** Good content

**2. Error Resource**
- **Link:** https://broken.com/error
- **What it covers:** ERROR: Could not fetch https://broken.com/error
"""

    mock_crew_class = mocker.patch("backend.crew_runner.ScholarSource")
    mock_crew_instance = Mock()
    mock_crew_instance.crew().kickoff_async = AsyncMock(return_value=mock_result)
    mock_crew_class.return_value = mock_crew_instance

    return mock_crew_class


# ==============================================================================
# Sample Test Data
# ==============================================================================

@pytest.fixture
def sample_course_input():
    """Sample course input data."""
    return {
        "course_url": "https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-fall-2011/",
        "course_name": "Introduction to Algorithms",
        "university_name": "MIT",
        "desired_resource_types": ["textbooks", "lecture_notes"]
    }


@pytest.fixture
def sample_book_input():
    """Sample book input data."""
    return {
        "book_title": "Introduction to Algorithms",
        "book_author": "Cormen, Leiserson, Rivest, Stein",
        "isbn": "978-0262046305",
        "topics_list": "sorting, graphs, dynamic programming"
    }


@pytest.fixture
def sample_job_data():
    """Sample job data."""
    job_id = str(uuid.uuid4())
    return {
        "id": job_id,
        "status": "pending",
        "inputs": {
            "course_url": "https://ocw.mit.edu/courses/algorithms",
            "course_name": "Algorithms"
        },
        "search_title": "Algorithms - MIT",
        "results": [],
        "raw_output": None,
        "error": None,
        "status_message": "Job created",
        "metadata": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None
    }


@pytest.fixture
def sample_resources():
    """Sample resource data."""
    return [
        {
            "type": "Textbook",
            "title": "Introduction to Algorithms",
            "source": "MIT Press",
            "url": "https://mitpress.mit.edu/books/introduction-algorithms",
            "description": "Comprehensive algorithms textbook"
        },
        {
            "type": "Lecture Notes",
            "title": "MIT 6.006 Lecture Notes",
            "source": "MIT OpenCourseWare",
            "url": "https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-fall-2011/",
            "description": "Complete lecture notes from MIT course"
        }
    ]


@pytest.fixture
def sample_markdown():
    """Sample markdown output from CrewAI."""
    return """
**Textbook:** Introduction to Algorithms, 4th ed., by Cormen, Leiserson, Rivest, and Stein

**1. MIT OpenCourseWare - Introduction to Algorithms** (Type: Lecture Notes)
- **Link:** https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-fall-2011/
- **Source:** MIT OpenCourseWare
- **What it covers:** Complete course materials including lecture videos, notes, and problem sets

**2. Algorithm Visualizer** (Type: Interactive Tool)
- **Link:** https://algorithm-visualizer.org/
- **Source:** Algorithm Visualizer
- **What it covers:** Interactive visualization of algorithms and data structures

**3. LeetCode** (Type: Practice Problems)
- **Link:** https://leetcode.com/problemset/algorithms/
- **Source:** LeetCode
- **What it covers:** Thousands of algorithm practice problems with solutions
"""
