"""
Error transformation utilities for user-friendly error messages.
Converts technical exceptions into messages safe to display to end users.
"""

import re

from pydantic import ValidationError


def transform_error_for_user(exception: Exception) -> tuple[str, str]:
    """
    Transform technical exceptions into user-friendly error messages.

    Args:
        exception: The original exception

    Returns:
        Tuple of (user_message, technical_details)
        - user_message: Safe, friendly message to show to users
        - technical_details: Technical error type for logging/debugging
    """
    error_type = type(exception).__name__
    error_str = str(exception)

    # Handle validation errors from Pydantic with suspicious patterns
    if isinstance(exception, ValueError) and "suspicious" in error_str.lower():
        return (
            "Your input contains patterns that may interfere with processing. "
            "Please remove any special formatting, instructions, or unusual characters and try again.",
            "ValidationError",
        )

    # Handle Pydantic validation errors
    if isinstance(exception, ValidationError):
        return _handle_pydantic_error(exception)

    # Handle environment variable errors
    if "environment variable" in error_str.lower() or "env var" in error_str.lower():
        return _handle_env_var_error(error_str, error_type)

    # Handle API key errors
    if any(key in error_str.lower() for key in ["api key", "api_key", "apikey", "authentication"]):
        return _handle_api_key_error(error_str, error_type)

    # Handle network/connection errors
    if any(term in error_str.lower() for term in ["connection", "timeout", "network", "unreachable"]):
        return ("Unable to connect to required services. Please try again later.", error_type)

    # Handle rate limiting errors
    if any(term in error_str.lower() for term in ["rate limit", "too many requests", "quota"]):
        return ("Service rate limit exceeded. Please try again in a few minutes.", error_type)

    # Handle file/resource not found
    if any(term in error_str.lower() for term in ["not found", "does not exist", "no such file"]):
        return ("The requested resource could not be found. Please check your input and try again.", error_type)

    # Handle permission errors
    if any(term in error_str.lower() for term in ["permission denied", "forbidden", "unauthorized"]):
        return ("Access to the requested resource was denied.", error_type)

    # Handle database errors
    if any(term in error_str.lower() for term in ["database", "supabase", "postgres", "sql"]):
        return ("A database error occurred. Please try again later.", error_type)

    # Handle task/worker errors
    if any(term in error_str.lower() for term in ["celery", "worker", "task"]):
        return ("A processing error occurred. Please try again.", error_type)

    # Generic fallback for unknown errors
    # Avoid exposing technical details like stack traces, class names, or internal paths
    return ("An unexpected error occurred while processing your request. Please try again later.", error_type)


def _handle_pydantic_error(error: ValidationError) -> tuple[str, str]:
    """Handle Pydantic validation errors specifically."""
    try:
        # Extract the first error from the validation error
        errors = error.errors()
        if not errors:
            return ("A configuration error occurred. Please contact support.", "ValidationError")

        first_error = errors[0]
        error_msg = first_error.get("msg", "")

        # Check for specific validation error types
        if "environment variable" in error_msg.lower():
            return _handle_env_var_error(error_msg, "ValidationError")

        if any(key in error_msg.lower() for key in ["api key", "api_key"]):
            return _handle_api_key_error(error_msg, "ValidationError")

        # Generic validation error
        return ("A configuration error occurred. Please contact support if this persists.", "ValidationError")

    except Exception:
        # Fallback if we can't parse the validation error
        return ("A configuration error occurred. Please contact support.", "ValidationError")


def _handle_env_var_error(error_msg: str, error_type: str) -> tuple[str, str]:
    """Handle environment variable related errors."""
    # Try to extract which env var is missing, but don't expose it to users
    # Just use it for technical logging
    return ("A required service configuration is missing. Please contact support.", error_type)


def _handle_api_key_error(error_msg: str, error_type: str) -> tuple[str, str]:
    """Handle API key related errors."""
    return ("A required service authentication is not configured. Please contact support.", error_type)


def sanitize_error_message(message: str) -> str:
    """
    Remove sensitive information from error messages.

    Args:
        message: The original error message

    Returns:
        Sanitized error message
    """
    # Remove JWT tokens (format: eyJ...eyJ...signature)
    message = re.sub(r"eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*", "[JWT_TOKEN]", message)

    # Remove Supabase keys (format: sb-...)
    message = re.sub(r"sb-[a-zA-Z0-9-]+", "[SUPABASE_KEY]", message)

    # Remove file paths
    message = re.sub(r"(/[\w/.-]+|[A-Z]:\\[\w\\.-]+)", "[PATH]", message)

    # Remove API keys or tokens (common patterns)
    message = re.sub(r'["\']?[A-Za-z0-9_-]{20,}["\']?', "[REDACTED]", message)

    # Remove environment variable values
    message = re.sub(r'=["\']?[^,\s]+["\']?', "=[REDACTED]", message)

    # Remove URLs with potential sensitive info
    message = re.sub(r"https?://[^\s]+", "[URL]", message)

    return message


def create_user_error_response(exception: Exception) -> dict:
    """
    Create a standardized error response for API endpoints.

    Args:
        exception: The original exception

    Returns:
        Dictionary with error and message fields suitable for HTTPException detail
    """
    user_message, error_type = transform_error_for_user(exception)

    return {"error": "processing_error", "message": user_message}
