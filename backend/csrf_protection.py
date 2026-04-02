"""
CSRF Protection Module

Provides Origin header validation for state-changing requests.
This is a defense-in-depth measure to prevent cross-origin POST requests
even without authentication/session management.
"""

from fastapi import Request, HTTPException
from backend.logging_config import get_logger
from backend.origins import allowed_origins

logger = get_logger(__name__)


def validate_origin(request: Request) -> None:
    """
    Validate Origin header for state-changing requests.

    This prevents cross-origin POST requests by checking that the Origin
    header matches one of the allowed origins. This is a defense-in-depth
    measure that works even without authentication.

    Why Origin only (not Referer):
      - The Origin header is set by browsers on every cross-origin request and
        cannot be overridden by page-level JavaScript, making it trustworthy.
      - The Referer header can be suppressed by browser privacy settings,
        Referrer-Policy headers, or HTTPS→HTTP transitions, creating false
        negatives. It can also be spoofed by non-browser clients, so it adds
        no real security benefit over Origin alone.

    Why GET/OPTIONS/HEAD are skipped:
      - These methods are defined as "safe" by RFC 7231 — they must not cause
        side effects. CSRF attacks require a state-changing request (POST, PUT,
        DELETE, PATCH), so checking read-only methods would only cause friction
        for legitimate clients (e.g. curl health checks, browser preflight).

    Why trailing slashes are stripped:
      - Some clients send "https://example.com/" with a trailing slash.
        Normalizing both sides avoids a mismatch against "https://example.com"
        in allowed_origins.

    Args:
        request: FastAPI request object

    Raises:
        HTTPException 403: If Origin header is absent or not in allowed_origins
    """
    # Safe methods cannot cause state changes — no CSRF risk, skip check.
    if request.method in ["GET", "OPTIONS", "HEAD"]:
        return

    origin = request.headers.get("Origin")

    # Origin is set automatically by browsers on cross-origin requests and
    # cannot be forged by page scripts. An absent Origin on a POST indicates
    # a non-browser client; we reject it as a conservative default.
    if origin:
        normalized_origin = origin.rstrip("/")
        for allowed in allowed_origins:
            if normalized_origin == allowed.rstrip("/"):
                logger.debug(f"Origin validation passed: {origin}")
                return

    # Origin missing or not in allowlist — reject the request.
    logger.warning(
        f"Origin validation failed - Origin: {origin}, "
        f"Method: {request.method}, Path: {request.url.path}"
    )
    raise HTTPException(
        status_code=403,
        detail={
            "error": "Invalid origin",
            "message": "Request origin not allowed. This request must come from an authorized domain."
        }
    )

