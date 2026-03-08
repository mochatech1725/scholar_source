"""
Shared constants for ScholarSource application.

This module contains constants that are used across multiple modules
to ensure consistency and ease of maintenance.

Note: For utility functions that use these constants, see utils.py
"""

# Crew output configuration
CREW_OUTPUT_FILENAME = "report.md"
"""
The filename used by CrewAI tasks to write their output.
This file is created during crew execution and read by the backend
to parse and process the results.

Use get_crew_output_file() or get_crew_output_path() from utils.py
to access this value programmatically.
"""
