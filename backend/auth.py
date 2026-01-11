"""
Authentication middleware for ScholarSource API.

This module provides JWT token verification using Supabase Auth.
All protected endpoints must include a valid JWT token in the Authorization header.
"""

import os
import jwt
from typing import Optional, Dict
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

load_dotenv()

# Supabase JWT secret from environment
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

if not SUPABASE_JWT_SECRET:
    raise ValueError("SUPABASE_JWT_SECRET environment variable is required")

# JWT bearer scheme
security = HTTPBearer()


class AuthenticationError(HTTPException):
    """Custom exception for authentication failures."""

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_jwt_token(token: str) -> Dict:
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
        # Decode and verify the JWT token
        # Supabase uses HS256 algorithm by default
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.InvalidAudienceError:
        raise AuthenticationError("Invalid token audience")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token")
    except Exception as e:
        raise AuthenticationError(f"Token verification failed: {str(e)}")


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
    credentials: HTTPAuthorizationCredentials = None
) -> Dict:
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
        credentials: HTTP bearer credentials (automatically extracted)

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
    }
