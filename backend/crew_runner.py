"""
CrewAI Runner

Runs the ScholarSource crew in a background thread and manages job status updates.
"""

import sys
import os
import threading
import traceback
from io import StringIO
from pathlib import Path
from typing import Dict

# Add src to path to import ScholarSource
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from scholar_source.crew import ScholarSource
from backend.jobs import update_job_status
from backend.markdown_parser import parse_markdown_to_resources


def run_crew_async(job_id: str, inputs: Dict[str, str]) -> None:
    """
    Run the ScholarSource crew in a background thread.

    This function:
    1. Updates job status to 'running'
    2. Executes the crew with provided inputs
    3. Parses the markdown output into structured resources
    4. Updates job with results or error

    Args:
        job_id: UUID of the job to run
        inputs: Dictionary of course input parameters
    """
    thread = threading.Thread(
        target=_run_crew_worker,
        args=(job_id, inputs),
        daemon=True
    )
    thread.start()


def _run_crew_worker(job_id: str, inputs: Dict[str, str]) -> None:
    """
    Worker function that runs in background thread.

    Args:
        job_id: UUID of the job
        inputs: Course input parameters
    """
    try:
        # Update status to running
        update_job_status(
            job_id,
            status="running",
            status_message="Initializing CrewAI agents..."
        )

        # Normalize inputs - convert None to empty string
        normalized_inputs = {
            key: (value if value is not None else "")
            for key, value in inputs.items()
        }

        # Ensure all required keys exist
        required_keys = [
            'university_name', 'course_name', 'course_url', 'textbook',
            'topics_list', 'book_title', 'book_author', 'isbn',
            'book_pdf_path', 'book_url'
        ]

        for key in required_keys:
            if key not in normalized_inputs:
                normalized_inputs[key] = ""

        # Update status
        update_job_status(
            job_id,
            status="running",
            status_message="Analyzing course and book structure..."
        )

        # Initialize and run crew
        crew_instance = ScholarSource()

        # Capture stdout/stderr for progress monitoring (optional)
        # For now, we'll just run the crew normally
        result = crew_instance.crew().kickoff(inputs=normalized_inputs)

        # Update status
        update_job_status(
            job_id,
            status="running",
            status_message="Parsing results..."
        )

        # Extract raw output
        raw_output = str(result.raw) if hasattr(result, 'raw') else str(result)

        # Try to read the report.md file if it exists
        report_path = Path("report.md")
        if report_path.exists():
            with open(report_path, "r") as f:
                markdown_content = f.read()
        else:
            # Use raw output as fallback
            markdown_content = raw_output

        # Parse markdown into structured resources
        resources = parse_markdown_to_resources(markdown_content)

        # Update job with results
        update_job_status(
            job_id,
            status="completed",
            status_message="Resource discovery completed successfully",
            results=resources,
            raw_output=markdown_content,
            metadata={
                "resource_count": len(resources),
                "crew_output_length": len(raw_output)
            }
        )

    except Exception as e:
        # Log error and update job
        error_message = str(e)
        stack_trace = traceback.format_exc()

        print(f"[ERROR] Job {job_id} failed: {error_message}")
        print(stack_trace)

        update_job_status(
            job_id,
            status="failed",
            error=error_message,
            status_message="Job failed due to an error",
            metadata={
                "error_type": type(e).__name__,
                "stack_trace": stack_trace
            }
        )


def validate_crew_inputs(inputs: Dict[str, str]) -> bool:
    """
    Validate that crew inputs meet minimum requirements.

    At least one of the following must be provided:
    - (course_name OR university_name) OR course_url
    - (book_title AND book_author) OR isbn
    - book_pdf_path
    - book_url

    Args:
        inputs: Dictionary of course inputs

    Returns:
        bool: True if inputs are valid, False otherwise
    """
    # Check for course information
    has_course_info = bool(
        inputs.get('course_name') or
        inputs.get('university_name') or
        inputs.get('course_url')
    )

    # Check for book identification
    has_book_info = bool(
        (inputs.get('book_title') and inputs.get('book_author')) or
        inputs.get('isbn')
    )

    # Check for book file or link
    has_book_file = bool(inputs.get('book_pdf_path'))
    has_book_link = bool(inputs.get('book_url'))

    # At least one combination must be satisfied
    return has_course_info or has_book_info or has_book_file or has_book_link
