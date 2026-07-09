"""
Authentication middleware for ScholarSource API.

This module provides JWT token verification using Supabase Auth.
All protected endpoints must include a valid JWT token in the Authorization header.
"""

import os

import jwt
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer
from jwt import PyJWKClient

from backend.env_loader import load_environment

# Load environment variables
load_environment()

# Supabase JWT secret from environment (used for legacy HS256 tokens)
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")

if not SUPABASE_JWT_SECRET:
    raise ValueError("SUPABASE_JWT_SECRET environment variable is required")

# JWT bearer scheme
security = HTTPBearer()

# Lazily-initialised JWKS client for ES256/RS256 tokens (new Supabase projects).
# Cached at module level so keys are not re-fetched on every request.
_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        jwks_url = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True)
    return _jwks_client


class AuthenticationError(HTTPException):
    """Custom exception for authentication failures."""

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_jwt_token(token: str) -> dict:
    """
    Verify a Supabase JWT token and return the decoded payload.

    Args:
        token: The JWT token string

    Returns:
        The decoded JWT payload containing user information

    Raises:
        AuthenticationError: If token is invalid, expired, or malformed
    """
    try:
        alg = jwt.get_unverified_header(token).get("alg", "HS256")

        if alg == "HS256":
            # Legacy Supabase projects — symmetric secret
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
        else:
            # New Supabase projects — asymmetric signing key (ES256 / RS256)
            signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256", "RS256"],
                audience="authenticated",
            )

        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired") from None
    except jwt.InvalidAudienceError:
        raise AuthenticationError("Invalid token audience") from None
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token") from None
    except Exception as e:
        raise AuthenticationError(f"Token verification failed: {str(e)}") from e


def get_user_id_from_token(token: str) -> str:
    """
    Extract user ID from a verified JWT token.

    Args:
        token: The JWT token string

    Returns:
        The user ID (UUID) from the token

    Raises:
        AuthenticationError: If token is invalid or user ID is missing
    """
    payload = verify_jwt_token(token)

    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Token does not contain user ID")

    return user_id


async def get_current_user(
    request: Request,
) -> dict:
    """
    FastAPI dependency to extract and verify the current user from the request.

    This function should be used as a dependency in protected endpoints:

    Example:
        @app.post("/api/submit")
        async def submit_job(
            request: Request,
            current_user: dict = Depends(get_current_user)
        ):
            user_id = current_user["id"]
            # ... rest of endpoint

    Args:
        request: The FastAPI request object
    Returns:
        Dictionary containing user information:
        - id: User ID (UUID)
        - email: User email (if available)
        - payload: Full JWT payload

    Raises:
        AuthenticationError: If no token is provided or token is invalid
    """
    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        raise AuthenticationError("Missing Authorization header")

    # Expected format: "Bearer <token>"
    parts = auth_header.split()

    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError("Invalid Authorization header format. Expected: Bearer <token>")

    token = parts[1]

    # Verify token and extract payload
    payload = verify_jwt_token(token)

    # Extract user information
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Token does not contain user ID")

    # Return user information
    return {
        "id": user_id,
        "email": payload.get("email"),
        "payload": payload,
        "access_token": token,  # Include token for RLS authentication
    }
