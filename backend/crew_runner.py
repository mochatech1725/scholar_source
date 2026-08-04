"""
CrewAI Runner

Runs the ScholarSource crew using Celery task queue for distributed job processing.
Replaces the old threading-based approach with a scalable queue-based architecture.
"""

import sys
from pathlib import Path

# Add src to path to import ScholarSource
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from backend.jobs import get_job, update_job_status
from backend.logging_config import get_logger

# Get logger for this module
logger = get_logger(__name__)


def run_crew_async(
    job_id: str,
    inputs: dict[str, str],
) -> str:
    """
    Enqueue a ScholarSource crew job to the Celery task queue, or run synchronously if in SYNC_MODE.

    In normal mode (with Redis/Celery):
    - Enqueues the job to Celery task queue
    - The actual job execution happens in a separate worker process

    In SYNC_MODE (no Redis):
    - Runs the job synchronously in the current process
    - Blocks until completion (not recommended for production)

    Args:
        job_id: UUID of the job to run
        inputs: Dictionary of course input parameters

    Returns:
        str: Celery task ID (in async mode) or "sync" (in sync mode)

    Raises:
        ValueError: If job doesn't exist or is not in pending status
    """
    import os

    # Check if running in sync mode
    SYNC_MODE = os.getenv("SYNC_MODE", "false").lower() in ("true", "1", "yes")

    # Verify job exists and is in correct status
    job = get_job(job_id, use_service_role=True)
    if not job:
        raise ValueError(f"Job {job_id} does not exist")

    job_status = job.get("status")
    if job_status not in ["pending", "queued"]:
        logger.warning(f"Job {job_id} is in status '{job_status}', expected 'pending' or 'queued'. Proceeding anyway.")

    if SYNC_MODE:
        # Run synchronously in the current process
        logger.info(f"Running job {job_id} synchronously (SYNC_MODE)")
        from backend.tasks import run_crew_task_sync

        # Update job status to running (will be updated by the sync task)
        update_job_status(
            job_id,
            status="running",
            status_message="Starting job execution (sync mode)...",
            metadata={
                "sync_mode": True,
            },
            use_service_role=True,
        )

        # Run the task synchronously (this will block)
        try:
            result = run_crew_task_sync(job_id, inputs)
            logger.info(f"Job {job_id} completed in sync mode: {result.get('status')}")
            return "sync"
        except Exception as e:
            logger.error(f"Job {job_id} failed in sync mode: {e}")
            raise
    else:
        # Import here to avoid circular dependency
        from backend.tasks import run_crew_task

        # Enqueue the task to Celery
        logger.info(f"Enqueueing job {job_id} to Celery task queue")
        celery_result = run_crew_task.apply_async(
            args=[job_id, inputs],
            task_id=None,  # Let Celery generate task ID
            queue="crew_jobs",  # Use the crew_jobs queue
            priority=5,  # Default priority (can be adjusted based on user tier, etc.)
        )

        celery_task_id = celery_result.id
        logger.info(f"Job {job_id} enqueued with Celery task ID: {celery_task_id}")

        # Update job status to queued with task ID
        update_job_status(
            job_id,
            status="queued",
            status_message="Job queued for processing",
            metadata={
                "celery_task_id": celery_task_id,
            },
            use_service_role=True,
        )

        return celery_task_id


def cancel_crew_job(job_id: str) -> bool:
    """
    Cancel an active crew job by revoking its Celery task (or marking as cancelled in sync mode).

    In async mode (with Celery):
    - Revokes the Celery task (terminates if running, removes if queued)

    In sync mode:
    - Marks the job as cancelled (cannot actually stop running task)

    Args:
        job_id: UUID of the job to cancel

    Returns:
        bool: True if task was found and cancelled, False otherwise
    """
    import os

    SYNC_MODE = os.getenv("SYNC_MODE", "false").lower() in ("true", "1", "yes")

    # Get the job to find the Celery task ID
    job = get_job(job_id, use_service_role=True)
    if not job:
        logger.warning(f"Cannot cancel job {job_id}: Job not found")
        return False

    # In sync mode, just mark as cancelled (can't actually stop running task)
    if SYNC_MODE or job.get("metadata", {}).get("sync_mode"):
        logger.info(f"Marking job {job_id} as cancelled (sync mode - cannot stop running task)")
        update_job_status(
            job_id,
            status="cancelled",
            status_message="Job cancelled by user (sync mode)",
            error="Job was cancelled (sync mode - task may complete)",
            use_service_role=True,
        )
        return True

    # Get Celery task ID from job metadata
    metadata = job.get("metadata", {})
    celery_task_id = metadata.get("celery_task_id")

    if not celery_task_id:
        logger.warning(f"Cannot cancel job {job_id}: No Celery task ID found in metadata")
        # Still update job status to cancelled for consistency
        update_job_status(
            job_id,
            status="cancelled",
            status_message="Job cancelled by user",
            error="Job was cancelled (no active task found)",
            use_service_role=True,
        )
        return False

    # Revoke the Celery task
    from backend.celery_app import app

    if app is None:
        logger.warning(f"Cannot cancel job {job_id}: Celery app not available")
        update_job_status(
            job_id,
            status="cancelled",
            status_message="Job cancelled by user",
            error="Job was cancelled (Celery not available)",
            use_service_role=True,
        )
        return False

    # terminate=True will kill the worker processing the task (if it's running)
    # signal='SIGTERM' is a graceful termination signal
    logger.info(f"Revoking Celery task {celery_task_id} for job {job_id}")
    app.control.revoke(celery_task_id, terminate=True, signal="SIGTERM")

    # Update job status to cancelled
    update_job_status(
        job_id,
        status="cancelled",
        status_message="Job cancelled by user",
        error="Job was cancelled before completion",
        use_service_role=True,
    )

    logger.info(f"Successfully cancelled job {job_id} (Celery task: {celery_task_id})")
    return True


def validate_crew_inputs(inputs: dict[str, str]) -> bool:
    """
    Validate that crew inputs meet minimum requirements.

    At least one of the following must be provided:
    - course_name
    - university_name
    - course_url
    - textbook
    - topics_list
    - book_title
    - book_author
    - isbn
    - book_url

    Args:
        inputs: Dictionary of course inputs

    Returns:
        bool: True if inputs are valid, False otherwise
    """

    def has_value(key: str) -> bool:
        value = inputs.get(key)
        if isinstance(value, str):
            return bool(value.strip())
        return bool(value)

    # Check for course/topic information.
    has_course_info = any(has_value(key) for key in ("course_name", "university_name", "course_url", "topics_list"))

    # Check for book identification. `textbook` is a legacy free-text field.
    has_book_info = any(has_value(key) for key in ("textbook", "book_title", "book_author", "isbn"))

    # Check for a link to the book.
    has_book_link = has_value("book_url")

    # At least one combination must be satisfied
    return has_course_info or has_book_info or has_book_link
