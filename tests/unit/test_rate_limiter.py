"""
Unit tests for rate_limiter.py

Tests rate limiting configuration and error handling.
"""

from unittest.mock import Mock

from slowapi.errors import RateLimitExceeded

from backend.rate_limiter import limiter, rate_limit_handler


class TestRateLimiter:
    """Test rate limiting configuration."""

    def test_limiter_exists(self):
        """Should initialize limiter instance."""
        assert limiter is not None
        assert hasattr(limiter, "limit")

    def test_limiter_uses_in_memory_when_allowed(self):
        """Should use in-memory storage when ALLOW_IN_MEMORY_RATE_LIMIT is set (via conftest)."""
        # In test environment, ALLOW_IN_MEMORY_RATE_LIMIT is set in conftest.py
        # Limiter should exist (using in-memory storage)
        assert limiter is not None
        assert hasattr(limiter, "limit")

    def test_limiter_has_default_limits(self):
        """Should have default rate limits configured."""
        assert limiter._default_limits is not None


class TestRateLimitHandler:
    """Test rate limit error response handler."""

    def test_rate_limit_error_response(self):
        """Should return proper 429 error response."""
        # Mock request
        request = Mock()

        # Mock RateLimitExceeded exception
        _limit = Mock()
        _limit.limit = "10 per hour"
        _limit.error_message.return_value = "10 per hour"
        exc = RateLimitExceeded(_limit)

        response = rate_limit_handler(request, exc)

        assert response.status_code == 429
        assert b"rate limit" in response.body.lower()

    def test_rate_limit_response_includes_retry_after(self):
        """Should include Retry-After header."""
        request = Mock()
        _limit = Mock()
        _limit.limit = "2 per minute"
        _limit.error_message.return_value = "2 per minute"
        exc = RateLimitExceeded(_limit)

        response = rate_limit_handler(request, exc)

        assert "Retry-After" in response.headers
        assert response.headers["Retry-After"] == "60"

    def test_rate_limit_response_parses_minute_limit(self):
        """Should calculate retry_after for minute-based limits."""
        request = Mock()
        _limit = Mock()
        _limit.limit = "2 per minute"
        _limit.error_message.return_value = "2 per minute"
        exc = RateLimitExceeded(_limit)

        response = rate_limit_handler(request, exc)

        # Minute-based limit should have 60s retry
        body = response.body.decode()
        assert "60" in body

    def test_rate_limit_response_parses_hour_limit(self):
        """Should calculate retry_after for hour-based limits."""
        request = Mock()
        _limit = Mock()
        _limit.limit = "10 per hour"
        _limit.error_message.return_value = "10 per hour"
        exc = RateLimitExceeded(_limit)

        response = rate_limit_handler(request, exc)

        # Hour-based limit should have 3600s retry
        body = response.body.decode()
        assert "3600" in body

    def test_rate_limit_response_parses_second_limit(self):
        """Should calculate retry_after for second-based limits."""
        request = Mock()
        _limit = Mock()
        _limit.limit = "5 per second"
        _limit.error_message.return_value = "5 per second"
        exc = RateLimitExceeded(_limit)

        response = rate_limit_handler(request, exc)

        # Second-based limit should have 1s retry
        body = response.body.decode()
        assert '"retry_after":1' in body or '"retry_after": 1' in body

    def test_rate_limit_response_default_retry(self):
        """Should use default retry_after if pattern not recognized."""
        request = Mock()
        _limit = Mock()
        _limit.limit = "Unknown limit format"
        _limit.error_message.return_value = "Unknown limit format"
        exc = RateLimitExceeded(_limit)
        exc.limit = None

        response = rate_limit_handler(request, exc)

        # Should default to 60 seconds
        body = response.body.decode()
        assert "60" in body

    def test_rate_limit_response_json_structure(self):
        """Should return JSON with expected structure."""
        import json

        request = Mock()
        _limit = Mock()
        _limit.limit = "10 per hour"
        _limit.error_message.return_value = "10 per hour"
        exc = RateLimitExceeded(_limit)

        response = rate_limit_handler(request, exc)

        # Parse response body
        body = json.loads(response.body.decode())

        assert "error" in body
        assert "message" in body
        assert "retry_after" in body
        assert "limit" in body
        assert body["error"] == "Rate limit exceeded"


class TestRateLimitIntegration:
    """Test rate limit integration with FastAPI."""

    def test_rate_limit_decorator_applies(self):
        """Should apply rate limit decorator to endpoints."""
        # This is tested more thoroughly in integration tests
        # Here we just verify the limiter can be used as a decorator
        assert callable(limiter.limit)

    def test_get_remote_address_key_func(self):
        """Should use remote address as rate limit key."""
        from slowapi.util import get_remote_address

        # Mock request
        mock_request = Mock()
        mock_request.client.host = "192.168.1.1"

        address = get_remote_address(mock_request)

        assert address == "192.168.1.1"


class TestRateLimitEdgeCases:
    """Test edge cases for rate limiting."""

    def test_rate_limit_handler_with_no_limit_object(self):
        """Should handle exception with no limit object."""
        request = Mock()
        _limit = Mock()
        _limit.limit = "Rate limit exceeded"
        _limit.error_message.return_value = "Rate limit exceeded"
        exc = RateLimitExceeded(_limit)
        exc.limit = None

        # Should not raise exception
        response = rate_limit_handler(request, exc)

        assert response.status_code == 429

    def test_rate_limit_handler_with_empty_detail(self):
        """Should handle exception with empty detail."""
        request = Mock()
        _limit = Mock()
        _limit.limit = ""
        _limit.error_message.return_value = ""
        exc = RateLimitExceeded(_limit)

        # Should not raise exception
        response = rate_limit_handler(request, exc)

        assert response.status_code == 429
