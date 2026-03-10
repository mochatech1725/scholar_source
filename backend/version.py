"""
Application version helpers.

Provides a single runtime version sourced from package metadata when available,
with a local development fallback to the root pyproject.toml.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
import re


PACKAGE_NAME = "scholar_source"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"


def get_app_version() -> str:
    """Return the canonical app version."""
    try:
        return package_version(PACKAGE_NAME)
    except PackageNotFoundError:
        pyproject_contents = PYPROJECT_PATH.read_text(encoding="utf-8")
        match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject_contents, re.MULTILINE)
        if not match:
            raise RuntimeError(f"Unable to determine app version from {PYPROJECT_PATH}")
        return match.group(1)


APP_VERSION = get_app_version()
