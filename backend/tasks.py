"""
Celery Tasks

This module defines all Celery tasks for the ScholarSource application.
Tasks are executed by Celery workers in separate processes.
"""

import sys
import os
import time
from backend.env_loader import load_environment

# Load environment variables
load_environment()

# Disable CrewAI telemetry prompts in production/worker environment
os.environ["OTEL_SDK_DISABLED"] = "true"

import re
import asyncio
import traceback
import time
import concurrent.futures
from pathlib import Path
from typing import Dict
from celery import Task

# Add src to path to import ScholarSource
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import utilities
from scholar_source.utils import get_crew_output_path

from backend.celery_app import app
from scholar_source.crew import ScholarSource
from backend.jobs import update_job_status, get_job
from backend.markdown_parser import parse_markdown_to_resources
from backend.logging_config import get_logger
from backend.error_utils import transform_error_for_user
from backend.security_utils import detect_prompt_injection

# Get logger for this module
logger = get_logger(__name__)

# Helper to conditionally apply Celery task decorator
# If app is None (sync mode), return a no-op decorator
def task_decorator(*args, **kwargs):
    if app is not None:
        # Return the actual Celery task decorator
        return app.task(*args, **kwargs)
    else:
        # Return a no-op decorator for sync mode (ignores all arguments)
        def noop_decorator(func):
            return func
        return noop_decorator


@task_decorator(
    bind=True,
    name="backend.tasks.run_crew_task",
    queue="crew_jobs",
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    reject_on_worker_lost=True,
)
def run_crew_task(
    self: Task,
    job_id: str,
    inputs: Dict[str, str],
) -> Dict[str, any]:
    """
    Celery task to run the ScholarSource crew.

    This task:
    1. Updates job status to 'running'
    2. Executes the crew with provided inputs using kickoff_async()
    3. Parses the markdown output into structured resources
    4. Updates job with results or error
    5. Supports cancellation via Celery's revoke mechanism

    Args:
        self: Celery task instance (auto-injected when bind=True)
        job_id: UUID of the job to run
        inputs: Dictionary of course input parameters

    Returns:
        Dict with status and results/error information
    """
    start_time = time.time()

    logger.info(f"Starting Celery task for job {job_id} (task_id: {self.request.id})")
    logger.info(f"Job {job_id} fields: {[k for k in inputs if inputs[k]]}")

    # Check if job was cancelled before starting
    job = get_job(job_id, use_service_role=True)
    if job and job.get("status") == "cancelled":
        elapsed = time.time() - start_time
        logger.info(f"Job {job_id} was cancelled before execution started (elapsed: {elapsed:.2f}s)")
        return {"status": "cancelled", "message": "Job was cancelled before execution"}

    try:
        # Update status to running
        update_job_status(
            job_id,
            status="running",
            status_message="Initializing CrewAI agents...",
            metadata={"celery_task_id": self.request.id},
            use_service_role=True
        )

        # Normalize inputs - convert None to empty string, but preserve lists for desired_resource_types
        normalized_inputs = {}
        for key, value in inputs.items():
            if key == 'desired_resource_types':
                # Keep as list (empty list if None or empty)
                normalized_inputs[key] = value if isinstance(value, list) else ([] if value is None else [])
            else:
                normalized_inputs[key] = (value if value is not None else "")

        # Ensure all required keys exist
        required_keys = [
            'university_name', 'course_name', 'course_url', 'textbook',
            'topics_list', 'book_title', 'book_author', 'isbn',
            'book_pdf_path', 'book_url', 'desired_resource_types', 'excluded_sites', 'targeted_sites',
            'chapter', 'sections', 'preferred_creators'
        ]

        for key in required_keys:
            if key not in normalized_inputs:
                if key == 'desired_resource_types':
                    normalized_inputs[key] = []
                else:
                    normalized_inputs[key] = ""

        # Secondary validation - defense-in-depth against prompt injection
        for key, value in normalized_inputs.items():
            if isinstance(value, str) and value:
                is_suspicious, reason = detect_prompt_injection(value)
                if is_suspicious:
                    error_msg = f"Input validation failed for '{key}': {reason}"
                    logger.error(f"🚨 Prompt injection attempt blocked in job {job_id}: {error_msg}")
                    update_job_status(
                        job_id=job_id,
                        status="failed",
                        error=error_msg,
                        status_message="Input validation failed",
                        use_service_role=True
                    )
                    return {"error": error_msg}

        update_job_status(
            job_id,
            status="running",
            status_message="Analyzing course and book structure...",
            use_service_role=True
        )

        # Initialize crew
        crew_instance = ScholarSource()
        crew = crew_instance.crew()

        logger.info(f"🚀 Starting CrewAI execution for job {job_id}")

        # Run crew asynchronously
        # Note: We need to run the async crew in an event loop
        result = asyncio.run(_run_crew_async(crew, normalized_inputs, job_id))

        # Update status
        update_job_status(
            job_id,
            status="running",
            status_message="Parsing results...",
            use_service_role=True
        )

        # Extract raw output
        raw_output = str(result.raw) if hasattr(result, 'raw') else str(result)

        # Try to read the report file if it exists
        report_path = get_crew_output_path()
        if report_path.exists():
            with open(report_path, "r") as f:
                markdown_content = f.read()
        else:
            # Use raw output as fallback
            markdown_content = raw_output

        # Check if the crew returned an error
        if "ERROR:" in markdown_content[:500]:
            error_match = re.search(r'ERROR:\s*(.+?)(?:\n|$)', markdown_content)
            error_msg = error_match.group(1) if error_match else "Cannot access provided resources"

            update_job_status(
                job_id,
                status="failed",
                error=error_msg,
                status_message="Failed to access course or book resources",
                raw_output=markdown_content[:1000],
                use_service_role=True
            )
            return {
                "status": "failed",
                "error": error_msg,
                "job_id": job_id
            }

        # Parse markdown into structured resources and metadata
        excluded_sites = normalized_inputs.get('excluded_sites', '')
        parsed_data = parse_markdown_to_resources(markdown_content, excluded_sites=excluded_sites)
        resources = parsed_data.get("resources", [])
        textbook_info = parsed_data.get("textbook_info")
        section_groups = parsed_data.get("section_groups")

        # Prepare metadata
        metadata = {
            "resource_count": len(resources),
            "crew_output_length": len(raw_output),
            "celery_task_id": self.request.id
        }
        if textbook_info:
            metadata["textbook_info"] = textbook_info
        if section_groups:
            metadata["section_groups"] = section_groups

        # Clean up uploaded PDF temp file if present
        pdf_path = normalized_inputs.get('book_pdf_path', '')
        if pdf_path and pdf_path.startswith('/tmp/scholar_uploads/'):
            try:
                os.unlink(pdf_path)
            except Exception:
                pass

        # Check if job was cancelled during execution
        job = get_job(job_id, use_service_role=True)
        if job and job.get("status") == "cancelled":
            logger.info(f"Job {job_id} was cancelled during execution, discarding results")
            return {"status": "cancelled", "message": "Job was cancelled during execution"}

        # Update job with results
        update_job_status(
            job_id,
            status="completed",
            status_message="Resource discovery completed successfully",
            results=resources,
            raw_output=markdown_content,
            metadata=metadata,
            use_service_role=True
        )

        elapsed = time.time() - start_time
        logger.info(f"✅ Job {job_id} completed successfully with {len(resources)} resources (elapsed: {elapsed:.2f}s)")

        return {
            "status": "completed",
            "job_id": job_id,
            "resource_count": len(resources)
        }

    except Exception as e:
        elapsed = time.time() - start_time

        # Transform error for user-friendly display
        user_message, error_type = transform_error_for_user(e)
        technical_error = str(e)
        stack_trace = traceback.format_exc()

        # Log the technical details for debugging (no user input values)
        logger.error(f"❌ Job {job_id} failed with {error_type}: {technical_error} (elapsed: {elapsed:.2f}s)")
        logger.error(stack_trace)

        # Clean up uploaded PDF on failure too
        try:
            pdf_path = normalized_inputs.get('book_pdf_path', '')
            if pdf_path and pdf_path.startswith('/tmp/scholar_uploads/'):
                os.unlink(pdf_path)
        except Exception:
            pass

        # Update job with user-friendly error message
        update_job_status(
            job_id,
            status="failed",
            error=user_message,  # User-friendly message
            status_message="Job failed due to an error",
            metadata={
                "error_type": error_type,
                "technical_error": technical_error,
                "celery_task_id": self.request.id
            },
            use_service_role=True
        )

        # Re-raise exception to trigger Celery retry mechanism
        raise self.retry(exc=e, countdown=60)


async def _run_crew_async(crew, inputs: Dict[str, str], job_id: str):
    """
    Helper function to run crew asynchronously.

    Args:
        crew: CrewAI crew instance
        inputs: Normalized input parameters
        job_id: Job ID for logging

    Returns:
        Crew execution result
    """
    # Flush before crew execution
    sys.stdout.flush()
    sys.stderr.flush()
    
    logger.info(f"[CrewAI] Starting crew.kickoff_async for job {job_id}")
    print(f"[CrewAI] === CREW EXECUTION START === job_id={job_id}", flush=True)
    
    result = await crew.kickoff_async(inputs=inputs)
    
    # Flush after crew execution
    sys.stdout.flush()
    sys.stderr.flush()
    
    print(f"[CrewAI] === CREW EXECUTION END === job_id={job_id}", flush=True)
    logger.info(f"[CrewAI] Completed crew.kickoff_async for job {job_id}")
    
    return result


def run_crew_task_sync(
    job_id: str,
    inputs: Dict[str, str],
) -> Dict[str, any]:
    """
    Synchronous version of run_crew_task that runs in-process without Celery.

    This function is used when SYNC_MODE=true (no Redis/Celery required).
    It performs the same operations as the Celery task but runs synchronously.

    Args:
        job_id: UUID of the job to run
        inputs: Dictionary of course input parameters

    Returns:
        Dict with status and results/error information
    """
    start_time = time.time()

    logger.info(f"Starting synchronous task for job {job_id} (SYNC_MODE)")
    logger.info(f"Job {job_id} fields: {[k for k in inputs if inputs[k]]}")

    # Check if job was cancelled before starting
    job = get_job(job_id, use_service_role=True)
    if job and job.get("status") == "cancelled":
        logger.info(f"Job {job_id} was cancelled before execution started")
        return {"status": "cancelled", "message": "Job was cancelled before execution"}

    try:
        # Update status to running
        update_job_status(
            job_id,
            status="running",
            status_message="Initializing CrewAI agents...",
            metadata={"sync_mode": True},
            use_service_role=True
        )

        # Normalize inputs - convert None to empty string, but preserve lists for desired_resource_types
        normalized_inputs = {}
        for key, value in inputs.items():
            if key == 'desired_resource_types':
                # Keep as list (empty list if None or empty)
                normalized_inputs[key] = value if isinstance(value, list) else ([] if value is None else [])
            else:
                normalized_inputs[key] = (value if value is not None else "")

        # Ensure all required keys exist
        required_keys = [
            'university_name', 'course_name', 'course_url', 'textbook',
            'topics_list', 'book_title', 'book_author', 'isbn',
            'book_pdf_path', 'book_url', 'desired_resource_types', 'excluded_sites', 'targeted_sites',
            'chapter', 'sections', 'preferred_creators'
        ]

        for key in required_keys:
            if key not in normalized_inputs:
                if key == 'desired_resource_types':
                    normalized_inputs[key] = []
                else:
                    normalized_inputs[key] = ""

        # Secondary validation - defense-in-depth against prompt injection
        for key, value in normalized_inputs.items():
            if isinstance(value, str) and value:
                is_suspicious, reason = detect_prompt_injection(value)
                if is_suspicious:
                    error_msg = f"Input validation failed for '{key}': {reason}"
                    logger.error(f"🚨 Prompt injection attempt blocked in job {job_id}: {error_msg}")
                    update_job_status(
                        job_id=job_id,
                        status="failed",
                        error=error_msg,
                        status_message="Input validation failed",
                        use_service_role=True
                    )
                    return {"error": error_msg}

        update_job_status(
            job_id,
            status="running",
            status_message="Analyzing course and book structure...",
            use_service_role=True
        )

        # Initialize crew
        crew_instance = ScholarSource()
        crew = crew_instance.crew()

        logger.info(f"🚀 Starting CrewAI execution for job {job_id} (sync mode)")

        # Run crew asynchronously
        # Handle case where we're already in an event loop (e.g., called from async FastAPI endpoint)
        try:
            # Try to get the current event loop
            loop = asyncio.get_running_loop()
            # If we're in a running loop, we need to run in a new thread
            # Create a new event loop in a thread to avoid the "cannot be called from a running event loop" error
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _run_crew_async(crew, normalized_inputs, job_id))
                result = future.result()
        except RuntimeError:
            # No running event loop, safe to use asyncio.run()
            result = asyncio.run(_run_crew_async(crew, normalized_inputs, job_id))

        # Update status
        update_job_status(
            job_id,
            status="running",
            status_message="Parsing results...",
            use_service_role=True
        )

        # Extract raw output
        raw_output = str(result.raw) if hasattr(result, 'raw') else str(result)

        # Try to read the report file if it exists
        report_path = get_crew_output_path()
        if report_path.exists():
            with open(report_path, "r") as f:
                markdown_content = f.read()
        else:
            # Use raw output as fallback
            markdown_content = raw_output

        # Check if the crew returned an error
        if "ERROR:" in markdown_content[:500]:
            error_match = re.search(r'ERROR:\s*(.+?)(?:\n|$)', markdown_content)
            error_msg = error_match.group(1) if error_match else "Cannot access provided resources"

            update_job_status(
                job_id,
                status="failed",
                error=error_msg,
                status_message="Failed to access course or book resources",
                raw_output=markdown_content[:1000],
                use_service_role=True
            )
            return {
                "status": "failed",
                "error": error_msg,
                "job_id": job_id
            }

        # Parse markdown into structured resources and metadata
        excluded_sites = normalized_inputs.get('excluded_sites', '')
        parsed_data = parse_markdown_to_resources(markdown_content, excluded_sites=excluded_sites)
        resources = parsed_data.get("resources", [])
        textbook_info = parsed_data.get("textbook_info")
        section_groups = parsed_data.get("section_groups")

        # Prepare metadata
        metadata = {
            "resource_count": len(resources),
            "crew_output_length": len(raw_output),
            "sync_mode": True
        }
        if textbook_info:
            metadata["textbook_info"] = textbook_info
        if section_groups:
            metadata["section_groups"] = section_groups

        # Clean up uploaded PDF temp file if present
        pdf_path = normalized_inputs.get('book_pdf_path', '')
        if pdf_path and pdf_path.startswith('/tmp/scholar_uploads/'):
            try:
                os.unlink(pdf_path)
            except Exception:
                pass

        # Check if job was cancelled during execution
        job = get_job(job_id, use_service_role=True)
        if job and job.get("status") == "cancelled":
            logger.info(f"Job {job_id} was cancelled during execution, discarding results")
            return {"status": "cancelled", "message": "Job was cancelled during execution"}

        # Update job with results
        update_job_status(
            job_id,
            status="completed",
            status_message="Resource discovery completed successfully",
            results=resources,
            raw_output=markdown_content,
            metadata=metadata,
            use_service_role=True
        )

        elapsed = time.time() - start_time
        logger.info(f"✅ Job {job_id} completed successfully with {len(resources)} resources (elapsed: {elapsed:.2f}s)")

        return {
            "status": "completed",
            "job_id": job_id,
            "resource_count": len(resources)
        }

    except Exception as e:
        elapsed = time.time() - start_time

        # Transform error for user-friendly display
        user_message, error_type = transform_error_for_user(e)
        technical_error = str(e)
        stack_trace = traceback.format_exc()

        # Log the technical details for debugging (no user input values)
        logger.error(f"❌ Job {job_id} failed with {error_type}: {technical_error} (elapsed: {elapsed:.2f}s)")
        logger.error(stack_trace)

        # Clean up uploaded PDF on failure too
        try:
            pdf_path = normalized_inputs.get('book_pdf_path', '')
            if pdf_path and pdf_path.startswith('/tmp/scholar_uploads/'):
                os.unlink(pdf_path)
        except Exception:
            pass

        # Update job with user-friendly error message
        update_job_status(
            job_id,
            status="failed",
            error=user_message,  # User-friendly message
            status_message="Job failed due to an error",
            metadata={
                "error_type": error_type,
                "technical_error": technical_error,
                "sync_mode": True
            },
            use_service_role=True
        )

        return {
            "status": "failed",
            "error": user_message,
            "job_id": job_id
        }


@task_decorator(
    bind=True,
    name="backend.tasks.cleanup_old_results",
    queue="default",
)
def cleanup_old_results(self: Task) -> Dict[str, any]:
    """
    Periodic task to clean up old job results.

    This task can be scheduled using Celery Beat to run periodically.

    Returns:
        Dict with cleanup statistics
    """
    logger.info("Starting cleanup of old results")

    # TODO: Implement cleanup logic
    # - Delete old jobs from database (e.g., completed jobs older than 30 days)
    # - Clean up orphaned files

    return {
        "status": "completed",
        "message": "Cleanup completed successfully"
    }


@task_decorator(
    bind=True,
    name="backend.tasks.health_check",
    queue="default",
)
def health_check(self: Task) -> Dict[str, any]:
    """
    Health check task to verify worker is functioning.

    Returns:
        Dict with health status
    """
    logger.info("Health check task executed")
    return {
        "status": "healthy",
        "worker_id": self.request.hostname,
        "task_id": self.request.id
    }
