"""
Utility functions for ScholarSource application.

This module contains helper functions that are used across multiple modules.
"""

from pathlib import Path
from scholar_source.constants import CREW_OUTPUT_FILENAME


def get_crew_output_file() -> str:
    """
    Get the filename used by CrewAI tasks to write their output.

    This file is created during crew execution and read by the backend
    to parse and process the results.

    Returns:
        str: The output filename (e.g., "report.md")

    Example:
        >>> output_file = get_crew_output_file()
        >>> report_path = Path(output_file)
    """
    return CREW_OUTPUT_FILENAME


def get_crew_output_path() -> Path:
    """
    Get the Path object for the crew output file.

    Convenience method that returns a Path object instead of a string.
    Useful when you need to perform file operations.

    Returns:
        Path: Path object pointing to the output file

    Example:
        >>> report_path = get_crew_output_path()
        >>> if report_path.exists():
        ...     content = report_path.read_text()
    """
    return Path(CREW_OUTPUT_FILENAME)
