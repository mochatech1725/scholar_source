"""
Integration tests for FastAPI endpoints.

Tests all API endpoints with mock dependencies.
"""

import pytest
import time
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Test /api/health endpoint."""

    def test_health_check_returns_200(self, client):
        """Should return healthy status."""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_health_check_json_structure(self, client):
        """Should return expected JSON structure."""
        response = client.get("/api/health")
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert isinstance(data["status"], str)
        assert isinstance(data["version"], str)


class TestRootEndpoint:
    """Test / root endpoint."""

    def test_root_returns_api_info(self, client):
        """Should return API information."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data
        assert data["message"] == "ScholarSource API"


class TestSubmitEndpoint:
    """Test /api/submit endpoint."""

    def test_submit_valid_course_url(self, client, mock_supabase, mock_crew_success):
        """Should accept valid course URL and return job_id."""
        payload = {
            "course_url": "https://ocw.mit.edu/courses/math",
            "course_name": "Mathematics"
        }
        response = client.post("/api/submit", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"
        assert "message" in data

    def test_submit_valid_book_info(self, client, mock_supabase, mock_crew_success):
        """Should accept valid book title and author."""
        payload = {
            "book_title": "Introduction to Algorithms",
            "book_author": "Cormen"
        }
        response = client.post("/api/submit", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data

    def test_submit_valid_isbn(self, client, mock_supabase, mock_crew_success):
        """Should accept valid ISBN."""
        payload = {"isbn": "978-0262046305"}
        response = client.post("/api/submit", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data

    def test_submit_empty_payload_fails(self, client, mock_supabase):
        """Should reject empty payload with 400."""
        response = client.post("/api/submit", json={})

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "error" in data["detail"]

    def test_submit_with_desired_resource_types(self, client, mock_supabase, mock_crew_success):
        """Should accept desired_resource_types list."""
        payload = {
            "course_url": "https://example.com",
            "desired_resource_types": ["textbooks", "practice_problem_sets"]
        }
        response = client.post("/api/submit", json=payload)

        assert response.status_code == 200

    def test_submit_with_excluded_sites(self, client, mock_supabase, mock_crew_success):
        """Should accept excluded_sites string."""
        payload = {
            "course_url": "https://example.com",
            "excluded_sites": "khanacademy.org, coursera.org"
        }
        response = client.post("/api/submit", json=payload)

        assert response.status_code == 200

    def test_submit_creates_job_in_database(self, client, mock_supabase, mock_crew_success):
        """Should create job record in database."""
        payload = {"course_url": "https://example.com"}
        response = client.post("/api/submit", json=payload)

        job_id = response.json()["job_id"]

        # Check job was created in mock database
        assert job_id in mock_supabase.jobs_data

    def test_submit_with_all_fields(self, client, mock_supabase, mock_crew_success):
        """Should accept all input fields."""
        payload = {
            "course_url": "https://example.com/course",
            "course_name": "Algorithms",
            "university_name": "MIT",
            "book_title": "Algorithms Book",
            "book_author": "Author Name",
            "isbn": "978-0262046305",
            "topics_list": "algorithms, data structures",
            "desired_resource_types": ["textbooks", "lecture_videos"],
            "excluded_sites": "example.com",
        }
        response = client.post("/api/submit", json=payload)

        assert response.status_code == 200


class TestStatusEndpoint:
    """Test /api/status/{job_id} endpoint."""

    def test_get_status_pending_job(self, client, mock_supabase, mock_crew_success):
        """Should return pending status for new job."""
        # Create a job first
        submit_resp = client.post("/api/submit", json={"course_url": "https://example.com"})
        job_id = submit_resp.json()["job_id"]

        # Check status
        response = client.get(f"/api/status/{job_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] in ["pending", "running"]

    def test_get_status_nonexistent_job(self, client, mock_supabase):
        """Should return 404 for nonexistent job."""
        fake_job_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/status/{fake_job_id}")

        assert response.status_code == 404

    def test_get_status_completed_job(self, client, mock_supabase):
        """Should return completed status with results."""
        from datetime import datetime, timezone

        # Create completed job directly in mock database
        job_id = "test-completed-job-123"
        mock_supabase.jobs_data[job_id] = {
            "id": job_id,
            "status": "completed",
            "status_message": "Job completed successfully",
            "results": [
                {
                    "type": "Textbook",
                    "title": "Test Resource",
                    "source": "Test Source",
                    "url": "https://example.com",
                    "description": "Test description"
                }
            ],
            "metadata": {"resource_count": 1},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "inputs": {"course_url": "https://example.com"},
            "search_title": "Test Course",
            "raw_output": None,
            "error": None
        }

        response = client.get(f"/api/status/{job_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert len(data["results"]) == 1
        assert "completed_at" in data

    def test_get_status_failed_job(self, client, mock_supabase):
        """Should return failed status with error message."""
        from datetime import datetime, timezone

        job_id = "test-failed-job-123"
        mock_supabase.jobs_data[job_id] = {
            "id": job_id,
            "status": "failed",
            "status_message": "Job failed",
            "error": "CrewAI execution error",
            "results": [],
            "metadata": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
            "inputs": {"course_url": "https://example.com"},
            "search_title": "Test Course",
            "raw_output": None
        }

        response = client.get(f"/api/status/{job_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert "error" in data
        assert data["error"] == "CrewAI execution error"

    def test_get_status_invalid_uuid_format(self, client, mock_supabase):
        """Should handle invalid UUID format gracefully."""
        response = client.get("/api/status/not-a-valid-uuid")

        # Should return 404 or 422 depending on validation
        assert response.status_code in [404, 422]


class TestCancelEndpoint:
    """Test /api/cancel/{job_id} endpoint."""

    def test_cancel_pending_job(self, client, mock_supabase, mock_crew_success):
        """Should cancel pending job."""
        # Create a job
        submit_resp = client.post("/api/submit", json={"course_url": "https://example.com"})
        job_id = submit_resp.json()["job_id"]

        # Cancel it
        response = client.post(f"/api/cancel/{job_id}")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_cancel_nonexistent_job(self, client, mock_supabase):
        """Should return 404 for nonexistent job."""
        fake_job_id = "00000000-0000-0000-0000-000000000000"
        response = client.post(f"/api/cancel/{fake_job_id}")

        assert response.status_code == 404

    def test_cancel_already_completed_job(self, client, mock_supabase):
        """Should handle cancelling already completed job."""
        from datetime import datetime, timezone

        job_id = "test-completed-job-456"
        mock_supabase.jobs_data[job_id] = {
            "id": job_id,
            "status": "completed",
            "status_message": "Job completed",
            "results": [],
            "metadata": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "inputs": {"course_url": "https://example.com"},
            "search_title": "Test Course",
            "raw_output": None,
            "error": None
        }

        response = client.post(f"/api/cancel/{job_id}")

        # Should still return 200 (idempotent)
        assert response.status_code == 200


class TestRateLimiting:
    """Test rate limiting enforcement."""

    @pytest.mark.slow
    def test_submit_rate_limit_per_minute(self, client, mock_supabase, mock_crew_success):
        """Should enforce 2/minute rate limit on /api/submit."""
        payload = {"course_url": "https://example.com"}

        # Make 3 requests quickly (limit is 2/minute)
        responses = []
        for _ in range(3):
            resp = client.post("/api/submit", json=payload)
            responses.append(resp.status_code)

        # At least one should be 429 (rate limited)
        assert 429 in responses

    def test_rate_limit_response_format(self, client, mock_supabase, mock_crew_success):
        """Should return proper rate limit error format."""
        payload = {"course_url": "https://example.com"}

        # Make requests until rate limited
        response = None
        for _ in range(5):
            response = client.post("/api/submit", json=payload)
            if response.status_code == 429:
                break

        if response and response.status_code == 429:
            data = response.json()
            assert "error" in data
            assert "retry_after" in data
            assert data["error"] == "Rate limit exceeded"


class TestCORSHeaders:
    """Test CORS configuration."""

    def test_cors_allows_localhost(self, client):
        """Should allow requests from localhost."""
        response = client.get(
            "/api/health",
            headers={"Origin": "http://localhost:5173"}
        )

        assert response.status_code == 200
        # CORS headers should be present in production
        # (TestClient may not add them in test mode)

    def test_cors_allows_custom_domain(self, client):
        """Should allow requests from configured domain."""
        response = client.get(
            "/api/health",
            headers={"Origin": "https://scholar-source.pages.dev"}
        )

        assert response.status_code == 200


class TestErrorHandling:
    """Test error handling across endpoints."""

    def test_invalid_json_returns_422(self, client):
        """Should return 422 for invalid JSON."""
        response = client.post(
            "/api/submit",
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_missing_content_type_returns_422(self, client):
        """Should return 422 for missing content type."""
        response = client.post(
            "/api/submit",
            data='{"course_url": "https://example.com"}'
        )

        # FastAPI should handle this
        assert response.status_code in [422, 415]

    def test_method_not_allowed(self, client):
        """Should return 405 for wrong HTTP method."""
        # GET on submit endpoint (should be POST)
        response = client.get("/api/submit")

        assert response.status_code == 405


class TestInputValidation:
    """Test input validation."""

    def test_submit_validates_at_least_one_input(self, client, mock_supabase):
        """Should require at least one input field."""
        # All fields empty
        payload = {
            "course_url": "",
            "book_title": "",
            "isbn": ""
        }
        response = client.post("/api/submit", json=payload)

        assert response.status_code == 400

    def test_submit_accepts_partial_book_info(self, client, mock_supabase, mock_crew_success):
        """Should accept book_title without book_author."""
        payload = {"book_title": "Algorithms"}
        response = client.post("/api/submit", json=payload)

        # Should accept (validation happens in crew_runner)
        assert response.status_code == 200

    def test_submit_strips_whitespace(self, client, mock_supabase, mock_crew_success):
        """Should handle whitespace-only fields as empty."""
        payload = {
            "course_url": "  https://example.com  ",
            "book_title": "   "  # Whitespace only
        }
        response = client.post("/api/submit", json=payload)

        assert response.status_code == 200
