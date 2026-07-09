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
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Optional, Tuple
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
from backend.resource_types import ALLOWED_RESOURCE_TYPE_SET

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


# ── Private helpers ───────────────────────────────────────────────────────────

_REQUIRED_KEYS: List[str] = [
    'university_name', 'course_name', 'course_url', 'textbook',
    'topics_list', 'book_title', 'book_author', 'isbn',
    'book_pdf_path', 'book_url', 'desired_resource_types', 'excluded_sites',
    'targeted_sites', 'chapter', 'sections', 'preferred_creators',
]

def _normalize_inputs(inputs: Dict) -> Dict:
    """
    Normalize raw task inputs for crew consumption:
    - Convert None values to empty strings (preserving lists for desired_resource_types).
    - Strip unrecognised desired_resource_types as defense in depth.
    - Fill in any missing required keys with safe defaults.
    """
    normalized: Dict = {}
    for key, value in inputs.items():
        if key == 'desired_resource_types':
            raw = value if isinstance(value, list) else ([] if value is None else [])
            # Discard any items not in the allowlist
            filtered = [v for v in raw if isinstance(v, str) and v in ALLOWED_RESOURCE_TYPE_SET]
            if len(filtered) < len(raw):
                discarded = [v for v in raw if v not in ALLOWED_RESOURCE_TYPE_SET]
                logger.warning(f"Discarding unrecognised resource types: {discarded}")
            normalized[key] = filtered
        else:
            normalized[key] = value if value is not None else ""
    for key in _REQUIRED_KEYS:
        if key not in normalized:
            normalized[key] = [] if key == 'desired_resource_types' else ""
    return normalized


def _validate_injection(normalized_inputs: Dict, job_id: str) -> Optional[str]:
    """
    Secondary defense-in-depth check for prompt injection in all string inputs.
    Returns an error message string if any field is suspicious, otherwise None.
    Caller is responsible for updating job status on failure.
    """
    for key, value in normalized_inputs.items():
        if isinstance(value, str) and value:
            is_suspicious, reason = detect_prompt_injection(value)
            if is_suspicious:
                msg = f"Input validation failed for '{key}': {reason}"
                logger.error(f"🚨 Prompt injection attempt blocked in job {job_id}: {msg}")
                return msg
    return None


def _read_crew_output(result) -> Tuple[str, str]:
    """
    Extract (raw_output, markdown_content) from a crew result.
    Prefers the on-disk report file; falls back to the result's raw string.
    """
    raw_output = str(result.raw) if hasattr(result, 'raw') else str(result)
    report_path = get_crew_output_path()
    if report_path.exists():
        with open(report_path, "r") as f:
            markdown_content = f.read()
    else:
        markdown_content = raw_output
    return raw_output, markdown_content


def _clear_previous_crew_output() -> None:
    """Remove stale CrewAI output so this run cannot parse an old report."""
    report_path = get_crew_output_path()
    if not report_path.exists():
        return

    try:
        report_path.unlink()
    except OSError as error:
        logger.warning(f"Failed to remove stale CrewAI report {report_path}: {error}")


def _extract_fatal_crew_error(markdown_content: str) -> Optional[str]:
    """Return a top-level crew error, not per-resource ERROR markers."""
    content = markdown_content.lstrip()
    if content.startswith("```"):
        content = re.sub(r"\A```(?:markdown)?\s*", "", content, count=1, flags=re.IGNORECASE)

    error_match = re.match(r"ERROR:\s*(.+?)(?:\n|$)", content, flags=re.IGNORECASE)
    if error_match:
        return error_match.group(1)
    return None


def _parse_crew_results(
    markdown_content: str,
    normalized_inputs: Dict,
) -> Tuple[list, Optional[dict], Optional[dict]]:
    """
    Parse markdown output into structured resources.
    Returns (resources, textbook_info, section_groups).
    """
    excluded_sites = normalized_inputs.get('excluded_sites', '')
    parsed_data = parse_markdown_to_resources(markdown_content, excluded_sites=excluded_sites)
    return (
        parsed_data.get("resources", []),
        parsed_data.get("textbook_info"),
        parsed_data.get("section_groups"),
    )


def _cleanup_pdf(normalized_inputs: Dict) -> None:
    """Remove the temporary PDF upload file if it came from /tmp/scholar_uploads/."""
    pdf_path = normalized_inputs.get('book_pdf_path', '')
    if pdf_path and pdf_path.startswith('/tmp/scholar_uploads/'):
        try:
            os.unlink(pdf_path)
        except OSError as e:
            logger.warning(f"Failed to remove temp PDF {pdf_path}: {e}")


def _handle_task_failure(
    job_id: str,
    e: Exception,
    elapsed: float,
    normalized_inputs: Dict,
    extra_metadata: Dict,
) -> Tuple[str, str]:
    """
    Shared failure handler used by both task variants.
    - Logs the exception with elapsed time.
    - Cleans up any uploaded PDF.
    - Updates the job to 'failed' in the DB.
    Returns (user_message, error_type) so the caller can take its final action
    (Celery retry vs. sync return).
    """
    user_message, error_type = transform_error_for_user(e)
    technical_error = str(e)
    stack_trace = traceback.format_exc()

    logger.error(
        f"❌ Job {job_id} failed with {error_type}: {technical_error} (elapsed: {elapsed:.2f}s)"
    )
    logger.error(stack_trace)

    _cleanup_pdf(normalized_inputs)

    update_job_status(
        job_id,
        status="failed",
        error=user_message,
        status_message="Job failed due to an error",
        metadata={"error_type": error_type, "technical_error": technical_error, **extra_metadata},
        use_service_role=True,
    )
    return user_message, error_type


# ── Crew runner (async helper) ────────────────────────────────────────────────

async def _run_crew_async(crew, inputs: Dict, job_id: str):
    """Run crew.kickoff_async, flushing stdout/stderr around it for Railway log visibility."""
    sys.stdout.flush()
    sys.stderr.flush()

    logger.info(f"[CrewAI] Starting crew.kickoff_async for job {job_id}")
    print(f"[CrewAI] === CREW EXECUTION START === job_id={job_id}", flush=True)

    result = await crew.kickoff_async(inputs=inputs)

    sys.stdout.flush()
    sys.stderr.flush()

    print(f"[CrewAI] === CREW EXECUTION END === job_id={job_id}", flush=True)
    logger.info(f"[CrewAI] Completed crew.kickoff_async for job {job_id}")

    return result


# ── Celery task ───────────────────────────────────────────────────────────────

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

    1. Updates job status to 'running'
    2. Executes the crew with provided inputs via kickoff_async()
    3. Parses the markdown output into structured resources
    4. Updates job with results or error
    5. Supports cancellation via Celery's revoke mechanism

    Args:
        self: Celery task instance (auto-injected when bind=True)
        job_id: UUID of the job to run
        inputs: Dictionary of course input parameters
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

    normalized_inputs: Dict = {}
    try:
        update_job_status(
            job_id,
            status="running",
            status_message="Initializing CrewAI agents...",
            metadata={"celery_task_id": self.request.id},
            use_service_role=True,
        )

        normalized_inputs = _normalize_inputs(inputs)

        # Secondary defense-in-depth: prompt injection check
        injection_error = _validate_injection(normalized_inputs, job_id)
        if injection_error:
            update_job_status(
                job_id,
                status="failed",
                error=injection_error,
                status_message="Input validation failed",
                use_service_role=True,
            )
            return {"error": injection_error}

        update_job_status(
            job_id,
            status="running",
            status_message="Analyzing course and book structure...",
            use_service_role=True,
        )

        crew_instance = ScholarSource()
        crew = crew_instance.crew()
        logger.info(f"🚀 Starting CrewAI execution for job {job_id}")

        _clear_previous_crew_output()
        result = asyncio.run(_run_crew_async(crew, normalized_inputs, job_id))

        update_job_status(
            job_id,
            status="running",
            status_message="Parsing results...",
            use_service_role=True,
        )

        raw_output, markdown_content = _read_crew_output(result)

        resources, textbook_info, section_groups = _parse_crew_results(
            markdown_content, normalized_inputs
        )

        # Treat only top-level crew errors as fatal. Resource-level errors are
        # filtered by the markdown parser so valid partial results can complete.
        error_msg = _extract_fatal_crew_error(markdown_content)
        if error_msg and not resources:
            update_job_status(
                job_id,
                status="failed",
                error=error_msg,
                status_message="Failed to access course or book resources",
                raw_output=markdown_content[:1000],
                use_service_role=True,
            )
            return {"status": "failed", "error": error_msg, "job_id": job_id}

        metadata: Dict = {
            "resource_count": len(resources),
            "crew_output_length": len(raw_output),
            "celery_task_id": self.request.id,
        }
        if textbook_info:
            metadata["textbook_info"] = textbook_info
        if section_groups:
            metadata["section_groups"] = section_groups

        _cleanup_pdf(normalized_inputs)

        # Check if job was cancelled during execution
        job = get_job(job_id, use_service_role=True)
        if job and job.get("status") == "cancelled":
            logger.info(f"Job {job_id} was cancelled during execution, discarding results")
            return {"status": "cancelled", "message": "Job was cancelled during execution"}

        update_job_status(
            job_id,
            status="completed",
            status_message="Resource discovery completed successfully",
            results=resources,
            raw_output=markdown_content,
            metadata=metadata,
            use_service_role=True,
        )

        elapsed = time.time() - start_time
        logger.info(
            f"✅ Job {job_id} completed successfully with {len(resources)} resources "
            f"(elapsed: {elapsed:.2f}s)"
        )
        return {"status": "completed", "job_id": job_id, "resource_count": len(resources)}

    except Exception as e:
        # Intentionally broad: CrewAI, Supabase, asyncio, and network layers can
        # all raise different exception types.  Fatal signals (KeyboardInterrupt,
        # SystemExit) are BaseException and are not caught here.
        elapsed = time.time() - start_time
        _handle_task_failure(
            job_id, e, elapsed, normalized_inputs,
            extra_metadata={"celery_task_id": self.request.id},
        )
        raise self.retry(exc=e, countdown=60)


# ── Sync task (no Celery / no Redis) ─────────────────────────────────────────

def run_crew_task_sync(
    job_id: str,
    inputs: Dict[str, str],
) -> Dict[str, any]:
    """
    Synchronous version of run_crew_task used when SYNC_MODE=true.
    Performs the same steps without Celery / Redis.

    Args:
        job_id: UUID of the job to run
        inputs: Dictionary of course input parameters
    """
    start_time = time.time()
    logger.info(f"Starting synchronous task for job {job_id} (SYNC_MODE)")
    logger.info(f"Job {job_id} fields: {[k for k in inputs if inputs[k]]}")

    # Check if job was cancelled before starting
    job = get_job(job_id, use_service_role=True)
    if job and job.get("status") == "cancelled":
        logger.info(f"Job {job_id} was cancelled before execution started")
        return {"status": "cancelled", "message": "Job was cancelled before execution"}

    normalized_inputs: Dict = {}
    try:
        update_job_status(
            job_id,
            status="running",
            status_message="Initializing CrewAI agents...",
            metadata={"sync_mode": True},
            use_service_role=True,
        )

        normalized_inputs = _normalize_inputs(inputs)

        # Secondary defense-in-depth: prompt injection check
        injection_error = _validate_injection(normalized_inputs, job_id)
        if injection_error:
            update_job_status(
                job_id,
                status="failed",
                error=injection_error,
                status_message="Input validation failed",
                use_service_role=True,
            )
            return {"error": injection_error}

        update_job_status(
            job_id,
            status="running",
            status_message="Analyzing course and book structure...",
            use_service_role=True,
        )

        crew_instance = ScholarSource()
        crew = crew_instance.crew()
        logger.info(f"🚀 Starting CrewAI execution for job {job_id} (sync mode)")

        _clear_previous_crew_output()

        # Handle the case where FastAPI's event loop is already running
        try:
            asyncio.get_running_loop()
            # Already inside a running loop — spin up a thread with its own loop
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run, _run_crew_async(crew, normalized_inputs, job_id)
                )
                result = future.result()
        except RuntimeError:
            # No running loop, safe to call asyncio.run() directly
            result = asyncio.run(_run_crew_async(crew, normalized_inputs, job_id))

        update_job_status(
            job_id,
            status="running",
            status_message="Parsing results...",
            use_service_role=True,
        )

        raw_output, markdown_content = _read_crew_output(result)

        resources, textbook_info, section_groups = _parse_crew_results(
            markdown_content, normalized_inputs
        )

        # Treat only top-level crew errors as fatal. Resource-level errors are
        # filtered by the markdown parser so valid partial results can complete.
        error_msg = _extract_fatal_crew_error(markdown_content)
        if error_msg and not resources:
            update_job_status(
                job_id,
                status="failed",
                error=error_msg,
                status_message="Failed to access course or book resources",
                raw_output=markdown_content[:1000],
                use_service_role=True,
            )
            return {"status": "failed", "error": error_msg, "job_id": job_id}

        metadata: Dict = {
            "resource_count": len(resources),
            "crew_output_length": len(raw_output),
            "sync_mode": True,
        }
        if textbook_info:
            metadata["textbook_info"] = textbook_info
        if section_groups:
            metadata["section_groups"] = section_groups

        _cleanup_pdf(normalized_inputs)

        # Check if job was cancelled during execution
        job = get_job(job_id, use_service_role=True)
        if job and job.get("status") == "cancelled":
            logger.info(f"Job {job_id} was cancelled during execution, discarding results")
            return {"status": "cancelled", "message": "Job was cancelled during execution"}

        update_job_status(
            job_id,
            status="completed",
            status_message="Resource discovery completed successfully",
            results=resources,
            raw_output=markdown_content,
            metadata=metadata,
            use_service_role=True,
        )

        elapsed = time.time() - start_time
        logger.info(
            f"✅ Job {job_id} completed successfully with {len(resources)} resources "
            f"(elapsed: {elapsed:.2f}s)"
        )
        return {"status": "completed", "job_id": job_id, "resource_count": len(resources)}

    except Exception as e:
        # Intentionally broad: same reasoning as run_crew_task above.
        elapsed = time.time() - start_time
        user_message, _ = _handle_task_failure(
            job_id, e, elapsed, normalized_inputs,
            extra_metadata={"sync_mode": True},
        )
        return {"status": "failed", "error": user_message, "job_id": job_id}


# ── Maintenance tasks ─────────────────────────────────────────────────────────

@task_decorator(
    name="backend.tasks.cleanup_old_results",
    queue="default",
)
def cleanup_old_results() -> Dict[str, any]:
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
