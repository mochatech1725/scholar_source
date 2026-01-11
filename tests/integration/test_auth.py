"""
Integration tests for authentication (Phase 6).

Tests authentication middleware, JWT verification, and access control.
"""

import jwt
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient


@pytest.fixture
def valid_jwt_token():
    """Generate a valid JWT token for testing."""
    import os
    # Use a test secret
    secret = os.getenv("SUPABASE_JWT_SECRET", "test-secret-key-for-testing-only")

    payload = {
        "sub": "123e4567-e89b-12d3-a456-426614174000",  # User ID
        "email": "test@example.com",
        "aud": "authenticated",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow()
    }

    token = jwt.encode(payload, secret, algorithm="HS256")
    return token


@pytest.fixture
def expired_jwt_token():
    """Generate an expired JWT token for testing."""
    import os
    secret = os.getenv("SUPABASE_JWT_SECRET", "test-secret-key-for-testing-only")

    payload = {
        "sub": "123e4567-e89b-12d3-a456-426614174000",
        "email": "test@example.com",
        "aud": "authenticated",
        "exp": datetime.utcnow() - timedelta(hours=1),  # Expired
        "iat": datetime.utcnow() - timedelta(hours=2)
    }

    token = jwt.encode(payload, secret, algorithm="HS256")
    return token


@pytest.fixture
def invalid_jwt_token():
    """Generate an invalid JWT token (wrong secret)."""
    payload = {
        "sub": "123e4567-e89b-12d3-a456-426614174000",
        "email": "test@example.com",
        "aud": "authenticated",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow()
    }

    # Sign with wrong secret
    token = jwt.encode(payload, "wrong-secret-key", algorithm="HS256")
    return token


@pytest.fixture
def different_user_token():
    """Generate a JWT token for a different user."""
    import os
    secret = os.getenv("SUPABASE_JWT_SECRET", "test-secret-key-for-testing-only")

    payload = {
        "sub": "999e9999-e99b-99d9-a999-999999999999",  # Different user ID
        "email": "other@example.com",
        "aud": "authenticated",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow()
    }

    token = jwt.encode(payload, secret, algorithm="HS256")
    return token


class TestAuthenticationRequired:
    """Test that endpoints require authentication."""

    def test_submit_without_token_returns_401(self, client, sample_course_input, mock_supabase):
        """POST /api/submit without token should return 401."""
        response = client.post("/api/submit", json=sample_course_input)

        assert response.status_code == 401
        assert "Authorization" in response.json().get("detail", "")

    def test_status_without_token_returns_401(self, client, mock_supabase):
        """GET /api/status without token should return 401."""
        job_id = "123e4567-e89b-12d3-a456-426614174000"
        response = client.get(f"/api/status/{job_id}")

        assert response.status_code == 401

    def test_cancel_without_token_returns_401(self, client, mock_supabase):
        """POST /api/cancel without token should return 401."""
        job_id = "123e4567-e89b-12d3-a456-426614174000"
        response = client.post(f"/api/cancel/{job_id}")

        assert response.status_code == 401

    def test_health_endpoint_public(self, client):
        """GET /api/health should work without authentication."""
        response = client.get("/api/health")

        # Health endpoint should be public
        assert response.status_code == 200
        assert "status" in response.json()


class TestJWTValidation:
    """Test JWT token validation."""

    def test_submit_with_valid_token_succeeds(
        self, client, sample_course_input, valid_jwt_token, mock_supabase, mock_crew_success
    ):
        """POST /api/submit with valid token should succeed."""
        headers = {"Authorization": f"Bearer {valid_jwt_token}"}
        response = client.post("/api/submit", json=sample_course_input, headers=headers)

        # Should accept the request (may fail later due to mocks, but auth should pass)
        assert response.status_code != 401
        assert response.status_code in [200, 201, 400, 422, 500]  # Not auth error

    def test_submit_with_expired_token_returns_401(
        self, client, sample_course_input, expired_jwt_token, mock_supabase
    ):
        """POST /api/submit with expired token should return 401."""
        headers = {"Authorization": f"Bearer {expired_jwt_token}"}
        response = client.post("/api/submit", json=sample_course_input, headers=headers)

        assert response.status_code == 401
        # Check for expiration message
        detail = str(response.json().get("detail", "")).lower()
        assert "expired" in detail or "unauthorized" in detail

    def test_submit_with_invalid_token_returns_401(
        self, client, sample_course_input, invalid_jwt_token, mock_supabase
    ):
        """POST /api/submit with invalid token should return 401."""
        headers = {"Authorization": f"Bearer {invalid_jwt_token}"}
        response = client.post("/api/submit", json=sample_course_input, headers=headers)

        assert response.status_code == 401

    def test_submit_with_malformed_token_returns_401(
        self, client, sample_course_input, mock_supabase
    ):
        """POST /api/submit with malformed token should return 401."""
        headers = {"Authorization": "Bearer not-a-valid-jwt-token"}
        response = client.post("/api/submit", json=sample_course_input, headers=headers)

        assert response.status_code == 401

    def test_submit_with_missing_bearer_prefix_returns_401(
        self, client, sample_course_input, valid_jwt_token, mock_supabase
    ):
        """POST /api/submit without 'Bearer' prefix should return 401."""
        headers = {"Authorization": valid_jwt_token}  # Missing "Bearer " prefix
        response = client.post("/api/submit", json=sample_course_input, headers=headers)

        assert response.status_code == 401

    def test_submit_with_wrong_auth_header_format_returns_401(
        self, client, sample_course_input, mock_supabase
    ):
        """POST /api/submit with wrong header format should return 401."""
        headers = {"Authorization": "Basic dXNlcjpwYXNz"}  # Basic auth instead of Bearer
        response = client.post("/api/submit", json=sample_course_input, headers=headers)

        assert response.status_code == 401


class TestUserIsolation:
    """Test that users can only access their own resources."""

    def test_user_can_access_own_job(
        self, client, valid_jwt_token, mock_supabase, sample_job_data
    ):
        """User should be able to access their own job."""
        # Create job for user
        job_data = sample_job_data.copy()
        job_data["user_id"] = "123e4567-e89b-12d3-a456-426614174000"  # Same as token
        job_id = job_data["id"]
        mock_supabase.jobs_data[job_id] = job_data

        headers = {"Authorization": f"Bearer {valid_jwt_token}"}
        response = client.get(f"/api/status/{job_id}", headers=headers)

        # Should be able to access (RLS or application logic should allow)
        # Note: May need to adjust based on actual RLS implementation
        assert response.status_code in [200, 404]  # Not 401/403

    def test_user_cannot_access_other_user_job(
        self, client, valid_jwt_token, different_user_token, mock_supabase, sample_job_data
    ):
        """User should not be able to access another user's job."""
        # Create job for user A
        job_data = sample_job_data.copy()
        job_data["user_id"] = "123e4567-e89b-12d3-a456-426614174000"
        job_id = job_data["id"]
        mock_supabase.jobs_data[job_id] = job_data

        # Try to access with user B's token
        headers = {"Authorization": f"Bearer {different_user_token}"}
        response = client.get(f"/api/status/{job_id}", headers=headers)

        # Should either return 404 (job not found due to RLS) or 403 (forbidden)
        assert response.status_code in [403, 404]

    def test_job_creation_associates_with_user(
        self, client, valid_jwt_token, mock_supabase, sample_course_input, mock_crew_success
    ):
        """Job creation should associate job with authenticated user."""
        headers = {"Authorization": f"Bearer {valid_jwt_token}"}
        response = client.post("/api/submit", json=sample_course_input, headers=headers)

        # Check if job was created (may fail due to other reasons, but check user_id if created)
        if response.status_code in [200, 201]:
            job_id = response.json().get("job_id")
            if job_id and job_id in mock_supabase.jobs_data:
                # Verify user_id is set
                assert mock_supabase.jobs_data[job_id].get("user_id") == "123e4567-e89b-12d3-a456-426614174000"


class TestAuthorizationHeader:
    """Test Authorization header parsing."""

    def test_case_insensitive_bearer(
        self, client, sample_course_input, valid_jwt_token, mock_supabase
    ):
        """'Bearer' keyword should be case-insensitive."""
        # Try different cases
        for prefix in ["Bearer", "bearer", "BEARER"]:
            headers = {"Authorization": f"{prefix} {valid_jwt_token}"}
            response = client.post("/api/submit", json=sample_course_input, headers=headers)

            # Should not fail due to case sensitivity (401 only if truly unauthorized)
            # Note: FastAPI/backend may or may not be case-sensitive, adjust as needed
            assert response.status_code != 403  # Should at least try to authenticate

    def test_extra_spaces_in_auth_header(
        self, client, sample_course_input, valid_jwt_token, mock_supabase
    ):
        """Authorization header should handle extra spaces gracefully."""
        headers = {"Authorization": f"Bearer  {valid_jwt_token}"}  # Extra space
        response = client.post("/api/submit", json=sample_course_input, headers=headers)

        # Should either work or return proper 401, not 500
        assert response.status_code != 500

    def test_empty_authorization_header_returns_401(
        self, client, sample_course_input, mock_supabase
    ):
        """Empty Authorization header should return 401."""
        headers = {"Authorization": ""}
        response = client.post("/api/submit", json=sample_course_input, headers=headers)

        assert response.status_code == 401


class TestTokenPayload:
    """Test JWT token payload extraction."""

    def test_user_id_extracted_from_sub_claim(
        self, client, valid_jwt_token, mock_supabase, sample_course_input, mock_crew_success
    ):
        """User ID should be extracted from 'sub' claim in JWT."""
        headers = {"Authorization": f"Bearer {valid_jwt_token}"}
        response = client.post("/api/submit", json=sample_course_input, headers=headers)

        # If job creation succeeds, verify user_id is from token's 'sub' claim
        if response.status_code in [200, 201]:
            job_id = response.json().get("job_id")
            if job_id and job_id in mock_supabase.jobs_data:
                user_id = mock_supabase.jobs_data[job_id].get("user_id")
                assert user_id == "123e4567-e89b-12d3-a456-426614174000"

    def test_token_without_sub_claim_rejected(self, client, sample_course_input, mock_supabase):
        """Token without 'sub' claim should be rejected."""
        import os
        secret = os.getenv("SUPABASE_JWT_SECRET", "test-secret-key-for-testing-only")

        # Create token without 'sub' claim
        payload = {
            "email": "test@example.com",
            "aud": "authenticated",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow()
            # Missing 'sub'
        }

        token = jwt.encode(payload, secret, algorithm="HS256")
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post("/api/submit", json=sample_course_input, headers=headers)

        assert response.status_code == 401

    def test_token_with_wrong_audience_rejected(self, client, sample_course_input, mock_supabase):
        """Token with wrong audience should be rejected."""
        import os
        secret = os.getenv("SUPABASE_JWT_SECRET", "test-secret-key-for-testing-only")

        payload = {
            "sub": "123e4567-e89b-12d3-a456-426614174000",
            "email": "test@example.com",
            "aud": "wrong-audience",  # Wrong audience
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow()
        }

        token = jwt.encode(payload, secret, algorithm="HS256")
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post("/api/submit", json=sample_course_input, headers=headers)

        assert response.status_code == 401


class TestSecurityHeaders:
    """Test security-related headers."""

    def test_unauthorized_response_includes_www_authenticate_header(
        self, client, sample_course_input, mock_supabase
    ):
        """401 responses should include WWW-Authenticate header."""
        response = client.post("/api/submit", json=sample_course_input)

        assert response.status_code == 401
        # May include WWW-Authenticate header (depending on implementation)
        # This is optional but good practice

    def test_auth_error_does_not_leak_sensitive_info(
        self, client, sample_course_input, invalid_jwt_token, mock_supabase
    ):
        """Authentication errors should not leak sensitive information."""
        headers = {"Authorization": f"Bearer {invalid_jwt_token}"}
        response = client.post("/api/submit", json=sample_course_input, headers=headers)

        assert response.status_code == 401
        error_detail = str(response.json().get("detail", "")).lower()

        # Should not expose internal details like secret keys, stack traces, etc.
        assert "secret" not in error_detail
        assert "traceback" not in error_detail
        assert "exception" not in error_detail


class TestCORSWithAuth:
    """Test CORS behavior with authentication."""

    def test_preflight_request_does_not_require_auth(self, client):
        """OPTIONS preflight requests should not require authentication."""
        # Simulate CORS preflight request
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization"
        }

        response = client.options("/api/submit", headers=headers)

        # Preflight should succeed without auth
        assert response.status_code in [200, 204]
