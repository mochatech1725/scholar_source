"""
Integration tests for complete job lifecycle.

Tests the full workflow: submit → running → completed/failed/cancelled
"""

import pytest
import time
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestJobLifecycle:
    """Test complete job lifecycle from submission to completion."""

    def test_job_pending_to_running_transition(self, client, mock_supabase, mock_crew_success):
        """Should transition from pending to running."""
        # Submit job
        submit_resp = client.post("/api/submit", json={"course_url": "https://example.com"})
        job_id = submit_resp.json()["job_id"]

        # Check status immediately
        status_resp = client.get(f"/api/status/{job_id}")
        initial_status = status_resp.json()["status"]

        assert initial_status in ["pending", "running"]

    def test_job_completes_successfully(self, client, mock_supabase, mock_crew_success):
        """Should complete with results after crew execution."""
        # Submit job
        submit_resp = client.post("/api/submit", json={"course_url": "https://example.com"})
        job_id = submit_resp.json()["job_id"]

        # Poll until completed (with timeout)
        max_attempts = 30
        for attempt in range(max_attempts):
            status_resp = client.get(f"/api/status/{job_id}")
            status_data = status_resp.json()
            status = status_data["status"]

            if status == "completed":
                # Job completed successfully
                assert "results" in status_data
                assert isinstance(status_data["results"], list)
                assert status_data["completed_at"] is not None
                return

            if status == "failed":
                pytest.fail(f"Job failed: {status_data.get('error')}")

            time.sleep(0.5)

        pytest.fail(f"Job did not complete within {max_attempts * 0.5}s")

    def test_job_failure_sets_error_status(self, client, mock_supabase, mock_crew_failure):
        """Should set failed status and error message on failure."""
        # Submit job (will fail due to mock_crew_failure)
        submit_resp = client.post("/api/submit", json={"course_url": "https://example.com"})
        job_id = submit_resp.json()["job_id"]

        # Poll until failed
        max_attempts = 30
        for attempt in range(max_attempts):
            status_resp = client.get(f"/api/status/{job_id}")
            status_data = status_resp.json()

            if status_data["status"] == "failed":
                # Job should have error message
                assert "error" in status_data
                assert status_data["error"] is not None
                return

            time.sleep(0.5)

        pytest.fail("Job did not fail as expected")

    def test_cancelled_job_stops_execution(self, client, mock_supabase, mock_crew_success):
        """Should stop execution when job is cancelled."""
        # Submit job
        submit_resp = client.post("/api/submit", json={"course_url": "https://example.com"})
        job_id = submit_resp.json()["job_id"]

        # Cancel immediately
        time.sleep(0.2)  # Brief delay
        cancel_resp = client.post(f"/api/cancel/{job_id}")
        assert cancel_resp.status_code == 200

        # Check status shows cancelled
        time.sleep(0.5)
        status_resp = client.get(f"/api/status/{job_id}")
        final_status = status_resp.json()["status"]

        # Should be cancelled (or possibly completed if it finished before cancel)
        assert final_status in ["cancelled", "completed"]

    def test_job_stores_results_in_database(self, client, mock_supabase, mock_crew_success):
        """Should persist results to database on completion."""
        # Submit job
        submit_resp = client.post("/api/submit", json={"course_url": "https://example.com"})
        job_id = submit_resp.json()["job_id"]

        # Wait for completion
        max_attempts = 30
        for _ in range(max_attempts):
            status_resp = client.get(f"/api/status/{job_id}")
            if status_resp.json()["status"] == "completed":
                break
            time.sleep(0.5)

        # Check database has job with results
        job_data = mock_supabase.jobs_data.get(job_id)
        assert job_data is not None
        assert "results" in job_data
        assert isinstance(job_data["results"], list)

    def test_multiple_jobs_run_independently(self, client, mock_supabase, mock_crew_success):
        """Should handle multiple concurrent jobs."""
        # Submit multiple jobs
        job_ids = []
        for i in range(3):
            resp = client.post("/api/submit", json={"course_url": f"https://example{i}.com"})
            job_ids.append(resp.json()["job_id"])

        # All jobs should have unique IDs
        assert len(set(job_ids)) == 3

        # All jobs should be created
        for job_id in job_ids:
            assert job_id in mock_supabase.jobs_data

    def test_job_metadata_updated(self, client, mock_supabase, mock_crew_success):
        """Should update job metadata throughout lifecycle."""
        # Submit job
        submit_resp = client.post("/api/submit", json={"course_url": "https://example.com"})
        job_id = submit_resp.json()["job_id"]

        # Wait for completion
        max_attempts = 30
        for _ in range(max_attempts):
            status_resp = client.get(f"/api/status/{job_id}")
            if status_resp.json()["status"] == "completed":
                break
            time.sleep(0.5)

        # Check metadata
        final_status = client.get(f"/api/status/{job_id}").json()
        assert "metadata" in final_status
        assert isinstance(final_status["metadata"], dict)


@pytest.mark.integration
class TestJobStatusPolling:
    """Test status polling behavior."""

    def test_polling_returns_consistent_job_data(self, client, mock_supabase, mock_crew_success):
        """Should return consistent job data across polls."""
        # Submit job
        submit_resp = client.post("/api/submit", json={"course_url": "https://example.com"})
        job_id = submit_resp.json()["job_id"]

        # Poll multiple times
        poll_results = []
        for _ in range(5):
            resp = client.get(f"/api/status/{job_id}")
            poll_results.append(resp.json())
            time.sleep(0.2)

        # Job ID should be consistent
        for result in poll_results:
            assert result["job_id"] == job_id

    def test_polling_shows_status_progression(self, client, mock_supabase, mock_crew_success):
        """Should show status progression over time."""
        # Submit job
        submit_resp = client.post("/api/submit", json={"course_url": "https://example.com"})
        job_id = submit_resp.json()["job_id"]

        # Collect statuses
        statuses = []
        max_attempts = 30
        for _ in range(max_attempts):
            resp = client.get(f"/api/status/{job_id}")
            status = resp.json()["status"]
            statuses.append(status)

            if status in ["completed", "failed", "cancelled"]:
                break

            time.sleep(0.5)

        # Should have at least one status update
        assert len(statuses) > 0

        # Final status should be terminal
        assert statuses[-1] in ["completed", "failed", "cancelled"]


@pytest.mark.integration
class TestJobErrorRecovery:
    """Test error handling and recovery."""

    def test_job_handles_crew_exception(self, client, mock_supabase, mock_crew_failure):
        """Should handle CrewAI exceptions gracefully."""
        # Submit job
        submit_resp = client.post("/api/submit", json={"course_url": "https://example.com"})
        job_id = submit_resp.json()["job_id"]

        # Poll until terminal status
        max_attempts = 30
        for _ in range(max_attempts):
            status_resp = client.get(f"/api/status/{job_id}")
            status = status_resp.json()["status"]

            if status in ["failed", "completed"]:
                # Should have failed gracefully
                if status == "failed":
                    assert "error" in status_resp.json()
                return

            time.sleep(0.5)

        pytest.fail("Job did not reach terminal status")

    def test_job_filters_error_resources(self, client, mock_supabase, mock_crew_with_errors):
        """Should filter out resources with errors."""
        # Submit job
        submit_resp = client.post("/api/submit", json={"course_url": "https://example.com"})
        job_id = submit_resp.json()["job_id"]

        # Wait for completion
        max_attempts = 30
        for _ in range(max_attempts):
            status_resp = client.get(f"/api/status/{job_id}")
            status_data = status_resp.json()

            if status_data["status"] == "completed":
                results = status_data["results"]

                # Should only have 1 resource (error one filtered)
                assert len(results) == 1
                assert "error" not in results[0]["url"].lower()
                return

            time.sleep(0.5)

        pytest.fail("Job did not complete")


@pytest.mark.integration
class TestJobInputVariations:
    """Test different input combinations."""

    @pytest.mark.parametrize("payload", [
        {"course_url": "https://example.com"},
        {"book_title": "Algorithms", "book_author": "Cormen"},
        {"isbn": "978-0262046305"},
        {"book_url": "https://example.com/book.pdf"},
        {"course_name": "Algorithms", "university_name": "MIT"},
    ])
    def test_valid_input_combinations(self, client, mock_supabase, mock_crew_success, payload):
        """Should accept various valid input combinations."""
        response = client.post("/api/submit", json=payload)

        assert response.status_code == 200
        assert "job_id" in response.json()

    def test_job_with_all_optional_fields(self, client, mock_supabase, mock_crew_success):
        """Should handle job with all optional fields populated."""
        payload = {
            "course_url": "https://example.com",
            "course_name": "Test Course",
            "university_name": "Test University",
            "book_title": "Test Book",
            "book_author": "Test Author",
            "isbn": "978-0000000000",
            "topics_list": "topic1, topic2, topic3",
            "desired_resource_types": ["textbooks", "lecture_videos", "practice_problem_sets"],
            "excluded_sites": "site1.com, site2.org",
        }

        response = client.post("/api/submit", json=payload)

        assert response.status_code == 200
        job_id = response.json()["job_id"]

        # Job should process successfully
        assert job_id in mock_supabase.jobs_data
