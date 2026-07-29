"""
Rate Limiting Configuration

Implements rate limiting for API endpoints using slowapi.
Uses Redis for distributed rate limiting across multiple instances.

⚠️  IMPORTANT: In-memory storage only works for single-instance deployments!
    For production/scaling, REDIS_URL is required.
    In-memory mode is only allowed when ALLOW_IN_MEMORY_RATE_LIMIT is explicitly set.
"""

import os

from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from backend.env_loader import load_environment

# Load environment variables
load_environment()

# Check for Redis connection string (required for production/scaling)
REDIS_URL = os.getenv("REDIS_URL")
SYNC_MODE = os.getenv("SYNC_MODE", "false").lower() in ("true", "1", "yes")
ALLOW_IN_MEMORY = os.getenv("ALLOW_IN_MEMORY_RATE_LIMIT", "false").lower() in ("true", "1", "yes")

# In sync mode, automatically allow in-memory rate limiting
if SYNC_MODE:
    ALLOW_IN_MEMORY = True

if REDIS_URL:
    # Production: Use Redis for shared rate limiting across instances
    limiter = Limiter(key_func=get_remote_address, storage_uri=REDIS_URL, default_limits=["1000/hour"])
    print("✅ Rate limiting: Redis (multi-instance mode)")
elif ALLOW_IN_MEMORY:
    # Development/Testing: Use in-memory storage (only when explicitly allowed or in SYNC_MODE)
    limiter = Limiter(key_func=get_remote_address, default_limits=["1000/hour"])
    if SYNC_MODE:
        print("⚠️  Rate limiting: In-memory (SYNC_MODE - single instance)")
    else:
        print("⚠️  Rate limiting: In-memory (development mode only - single instance)")
else:
    # Production without Redis: Raise error
    raise ValueError(
        "REDIS_URL environment variable is required for rate limiting. "
        "Set REDIS_URL to your Redis connection string, or set "
        "SYNC_MODE=true or ALLOW_IN_MEMORY_RATE_LIMIT=true for local development/testing only."
    )


def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom handler for rate limit exceeded errors.

    Returns a user-friendly JSON response with retry information.

    Args:
        request: The FastAPI request object
        exc: The RateLimitExceeded exception

    Returns:
        JSONResponse with 429 status and helpful error message
    """
    # Calculate retry_after based on the limit
    # Extract time window from limit string (e.g., "2 per 1 minute")
    limit_str = str(exc.limit.limit) if exc.limit else exc.detail

    # Simple retry_after calculation based on common patterns
    retry_after = 60  # Default to 60 seconds
    if "minute" in limit_str:
        retry_after = 60
    elif "hour" in limit_str:
        retry_after = 3600
    elif "second" in limit_str:
        retry_after = 1

    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "message": f"Too many requests. Please try again in {retry_after} seconds.",
            "retry_after": retry_after,
            "limit": exc.detail,
        },
        headers={"Retry-After": str(retry_after)},
    )
