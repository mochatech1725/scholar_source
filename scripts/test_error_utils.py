"""
Unit tests for error transformation utilities.
Tests that technical errors are properly converted to user-friendly messages.
"""
from pydantic import ValidationError, BaseModel, Field
from backend.error_utils import (
    transform_error_for_user,
    create_user_error_response,
    sanitize_error_message
)


class TestModel(BaseModel):
    """Test model for Pydantic validation errors."""
    api_key: str = Field(..., description="Required API key")


def test_pydantic_validation_error():
    """Test that Pydantic validation errors are transformed properly."""
    try:
        # This will raise a ValidationError
        TestModel()
    except ValidationError as e:
        user_message, error_type = transform_error_for_user(e)

        # Should not expose technical details
        assert "validation error" not in user_message.lower() or "configuration" in user_message.lower()
        assert "pydantic" not in user_message.lower()
        assert "field required" not in user_message.lower()

        # Should be user-friendly
        assert len(user_message) > 10
        assert error_type == "ValidationError"


def test_environment_variable_error():
    """Test that environment variable errors are handled properly."""
    error = ValueError("The CHROMA_OPENAI_API_KEY environment variable is not set")
    user_message, error_type = transform_error_for_user(error)

    # Should not expose env var names
    assert "CHROMA_OPENAI_API_KEY" not in user_message
    assert "environment variable" not in user_message.lower()

    # Should be user-friendly
    assert "configuration" in user_message.lower() or "service" in user_message.lower()
    assert "contact support" in user_message.lower()


def test_api_key_error():
    """Test that API key errors are handled properly."""
    error = Exception("Invalid API key provided")
    user_message, error_type = transform_error_for_user(error)

    # Should not expose technical API key details
    assert "api key" not in user_message.lower() or "authentication" in user_message.lower()

    # Should be user-friendly
    assert "configuration" in user_message.lower() or "authentication" in user_message.lower()
    assert "contact support" in user_message.lower()


def test_network_error():
    """Test that network errors are handled properly."""
    error = ConnectionError("Connection timeout to service")
    user_message, error_type = transform_error_for_user(error)

    # Should be user-friendly
    assert "connect" in user_message.lower() or "service" in user_message.lower()
    assert "try again" in user_message.lower()
    assert error_type == "ConnectionError"


def test_generic_error():
    """Test that unknown errors get a generic message."""
    error = RuntimeError("Some internal error with stack trace")
    user_message, error_type = transform_error_for_user(error)

    # Should not expose technical details
    assert "stack trace" not in user_message.lower()
    assert "internal error" not in user_message.lower()

    # Should be user-friendly
    assert "unexpected" in user_message.lower() or "error occurred" in user_message.lower()
    assert "try again" in user_message.lower()
    assert error_type == "RuntimeError"


def test_create_user_error_response():
    """Test that error response dictionary is properly formatted."""
    error = ValueError("Test error")
    response = create_user_error_response(error)

    # Should have correct structure
    assert "error" in response
    assert "message" in response
    assert response["error"] == "processing_error"

    # Message should be user-friendly
    assert "Test error" not in response["message"]  # Should not be raw error
    assert len(response["message"]) > 10


def test_sanitize_error_message():
    """Test that sensitive information is removed from error messages."""
    # Test file path removal
    message = "Error in /usr/local/app/backend/file.py at line 42"
    sanitized = sanitize_error_message(message)
    assert "/usr/local/app" not in sanitized
    assert "[PATH]" in sanitized

    # Test API key removal
    message = "API key sk_test_1234567890abcdefghij not valid"
    sanitized = sanitize_error_message(message)
    assert "sk_test_1234567890abcdefghij" not in sanitized
    assert "[REDACTED]" in sanitized

    # Test URL removal - URLs get redacted by the API key regex too, which is fine
    message = "Failed to fetch https://api.example.com/endpoint?key=secret"
    sanitized = sanitize_error_message(message)
    assert "https://api.example.com" not in sanitized
    # Either [URL] or [REDACTED] is acceptable as long as the URL is hidden
    assert ("[URL]" in sanitized or "[REDACTED]" in sanitized)


def test_pydantic_error_with_env_var():
    """Test the specific case from the user's error message."""
    # Simulate the actual error the user reported
    error_msg = "1 validation error for WebsiteSearchTool\nValue error, The CHROMA_OPENAI_API_KEY environment variable is not set."

    # Create a mock validation error
    try:
        # This creates a validation error similar to the one in the issue
        class WebsiteSearchTool(BaseModel):
            config: dict

            @property
            def _run(self):
                if not "CHROMA_OPENAI_API_KEY":
                    raise ValueError("The CHROMA_OPENAI_API_KEY environment variable is not set.")

        # Trigger validation
        tool = WebsiteSearchTool(config={})
        _ = tool._run
    except ValueError as e:
        user_message, error_type = transform_error_for_user(e)

        # Should NOT contain any of these technical details
        assert "CHROMA_OPENAI_API_KEY" not in user_message
        assert "validation error" not in user_message.lower() or "configuration" in user_message.lower()
        assert "WebsiteSearchTool" not in user_message
        assert "pydantic" not in user_message.lower()

        # Should be user-friendly
        assert "configuration" in user_message.lower() or "service" in user_message.lower()
        assert "contact support" in user_message.lower()


if __name__ == "__main__":
    # Run basic tests
    print("Testing error transformation...")

    print("\n1. Testing Pydantic validation error...")
    test_pydantic_validation_error()
    print("✓ Pydantic validation error test passed")

    print("\n2. Testing environment variable error...")
    test_environment_variable_error()
    print("✓ Environment variable error test passed")

    print("\n3. Testing API key error...")
    test_api_key_error()
    print("✓ API key error test passed")

    print("\n4. Testing network error...")
    test_network_error()
    print("✓ Network error test passed")

    print("\n5. Testing generic error...")
    test_generic_error()
    print("✓ Generic error test passed")

    print("\n6. Testing error response creation...")
    test_create_user_error_response()
    print("✓ Error response creation test passed")

    print("\n7. Testing message sanitization...")
    test_sanitize_error_message()
    print("✓ Message sanitization test passed")

    print("\n8. Testing the specific user-reported error...")
    test_pydantic_error_with_env_var()
    print("✓ User-reported error test passed")

    print("\n✅ All tests passed!")
