"""
Environment Variable Loader

Centralized environment variable loading for the ScholarSource backend.
Loads environment variables based on ENVIRONMENT setting (local, dev, prod).
"""

import os

from dotenv import load_dotenv


def load_environment():
    """
    Load environment variables based on ENVIRONMENT setting.

    Priority (highest to lowest):
    1. Already set environment variables
    2. .env.{environment} file (e.g., .env.local, .env.dev, .env.prod)
    3. .env file (fallback)

    The ENVIRONMENT variable determines which env file to load:
    - "local" (default) -> loads .env.local
    - "dev" -> loads .env.dev
    - "prod" -> loads .env.prod

    If ENVIRONMENT is not set, defaults to "local".
    """
    # Get environment type (default to "local" for development)
    env = os.getenv("ENVIRONMENT", "local")

    # Load environment-specific file first (takes precedence)
    env_file = f".env.{env}"
    load_dotenv(env_file, override=False)

    # Load base .env file as fallback
    load_dotenv(".env", override=False)

    return env


# Convenience: Load environment when this module is imported
_current_environment = load_environment()


def get_current_environment() -> str:
    """
    Get the current environment name.

    Returns:
        str: The current environment ("local", "dev", "prod", etc.)
    """
    return _current_environment
