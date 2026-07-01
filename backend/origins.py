"""
Allowed Origins

Single source of truth for allowed origins used by both the CORS middleware
and the CSRF origin validation. Both systems stay in sync automatically.

Configuration:
  ENVIRONMENT          — set to "production" to exclude dev origins
  EXTRA_ALLOWED_ORIGINS — comma-separated list of additional origins to append
"""

import os


_production_origins = [
    "https://scholar-source.pages.dev",  # Cloudflare Pages
    "https://scholar-source.com",
]
_dev_origins = [
    "https://dev.scholar-source.pages.dev",  # Cloudflare Pages dev branch
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5175",  # Standard Vite port
    "http://127.0.0.1:5175",
]
_extra_origins = [
    o.strip()
    for o in os.getenv("EXTRA_ALLOWED_ORIGINS", "").split(",")
    if o.strip()
]

allowed_origins: list[str] = (
    _production_origins + _extra_origins
    if os.getenv("ENVIRONMENT", "local") == "production"
    else _production_origins + _dev_origins + _extra_origins
)
