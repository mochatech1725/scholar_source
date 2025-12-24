"""
CrewAI Runner

Runs the ScholarSource crew asynchronously and manages job status updates with cancellation support.
"""

import sys
import os
import re
import asyncio
import traceback
from io import StringIO
from pathlib import Path
from typing import Dict

# Add src to path to import ScholarSource
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from scholar_source.crew import ScholarSource
from backend.jobs import update_job_status, get_job
from backend.markdown_parser import parse_markdown_to_resources
from backend.email_service import send_results_email

# Store active crew tasks so we can cancel them
_active_tasks = {}


def run_crew_async(job_id: str, inputs: Dict[str, str]) -> None:
    """
    Run the ScholarSource crew asynchronously with cancellation support.

    This function:
    1. Updates job status to 'running'
    2. Executes the crew with provided inputs using kickoff_async()
    3. Parses the markdown output into structured resources
    4. Updates job with results or error
    5. Supports cancellation via cancel_crew_job()

    Args:
        job_id: UUID of the job to run
        inputs: Dictionary of course input parameters
    """
    import threading

    def run_in_thread():
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(_run_crew_worker(job_id, inputs))
        finally:
            loop.close()

    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()


def cancel_crew_job(job_id: str) -> bool:
    """
    Cancel an active crew job by cancelling its async task.

    Args:
        job_id: UUID of the job to cancel

    Returns:
        bool: True if task was found and cancelled, False otherwise
    """
    task = _active_tasks.get(job_id)
    if task and not task.done():
        task.cancel()
        print(f"[INFO] Cancelled crew task for job {job_id}")
        return True
    return False


async def _run_crew_worker(job_id: str, inputs: Dict[str, str]) -> None:
    """
    Worker function that runs in background thread.

    Args:
        job_id: UUID of the job
        inputs: Course input parameters
    """
    # Check if job was cancelled before starting
    job = get_job(job_id)
    if job and job.get("status") == "cancelled":
        print(f"[INFO] Job {job_id} was cancelled before execution started")
        return

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

        # Initialize and run crew asynchronously
        crew_instance = ScholarSource()
        crew = crew_instance.crew()

        # Create async task for crew execution
        crew_task = asyncio.create_task(crew.kickoff_async(inputs=normalized_inputs))

        # Store task so it can be cancelled
        _active_tasks[job_id] = crew_task

        try:
            # Wait for crew to complete or be cancelled
            result = await crew_task
        except asyncio.CancelledError:
            print(f"[INFO] Job {job_id} was cancelled during execution")
            update_job_status(
                job_id,
                status="cancelled",
                status_message="Job cancelled by user",
                error="Job was cancelled before completion"
            )
            return
        finally:
            # Remove from active tasks
            _active_tasks.pop(job_id, None)

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

        # Check if the crew returned an error (e.g., couldn't access sources)
        if "ERROR:" in markdown_content[:500]:  # Check first 500 chars for error
            # Extract error message
            error_match = re.search(r'ERROR:\s*(.+?)(?:\n|$)', markdown_content)
            error_msg = error_match.group(1) if error_match else "Cannot access provided resources"

            update_job_status(
                job_id,
                status="failed",
                error=error_msg,
                status_message="Failed to access course or book resources",
                raw_output=markdown_content[:1000]  # Store first 1000 chars for debugging
            )
            return

        # Parse markdown into structured resources and metadata
        parsed_data = parse_markdown_to_resources(markdown_content)
        resources = parsed_data.get("resources", [])
        textbook_info = parsed_data.get("textbook_info")

        # Prepare metadata
        metadata = {
            "resource_count": len(resources),
            "crew_output_length": len(raw_output)
        }
        if textbook_info:
            metadata["textbook_info"] = textbook_info

        # Check if job was cancelled during execution
        job = get_job(job_id)
        if job and job.get("status") == "cancelled":
            print(f"[INFO] Job {job_id} was cancelled during execution, discarding results")
            return

        # Update job with results
        update_job_status(
            job_id,
            status="completed",
            status_message="Resource discovery completed successfully",
            results=resources,
            raw_output=markdown_content,
            metadata=metadata
        )

        # Send email notification if email was provided
        email = inputs.get('email')
        if email:
            # Get job data for search title
            job = get_job(job_id)
            search_title = job.get('search_title', 'Your Search') if job else 'Your Search'

            # Send email (non-blocking, failure won't affect job status)
            try:
                send_results_email(
                    to_email=email,
                    search_title=search_title,
                    resources=resources,
                    job_id=job_id
                )
            except Exception as email_error:
                print(f"[WARNING] Failed to send email to {email}: {str(email_error)}")

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
