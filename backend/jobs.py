"""
Job Management with Supabase

CRUD operations for managing background jobs in Supabase PostgreSQL.
Jobs are persisted across server restarts.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from backend.database import get_supabase_client
from backend.logging_config import get_logger

# Get logger for this module
logger = get_logger(__name__)


def create_job(inputs: dict) -> str:
    """
    Create a new job in Supabase database.

    Args:
        inputs: Dictionary of course input parameters

    Returns:
        str: UUID of the created job

    Raises:
        Exception: If job creation fails
    """
    supabase = get_supabase_client()

    # Generate search title from inputs for user-friendly display
    search_title = _generate_search_title(inputs)

    job_data = {
        "status": "pending",
        "inputs": inputs,
        "search_title": search_title,
        "created_at": datetime.utcnow().isoformat()
    }

    try:
        response = supabase.table("jobs").insert(job_data).execute()
        if not response.data:
            raise Exception("Failed to create job: No data returned")
        return response.data[0]["id"]
    except Exception as e:
        raise Exception(f"Failed to create job in database: {str(e)}")


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get job data from Supabase database.

    Args:
        job_id: UUID of the job

    Returns:
        dict | None: Job data dictionary or None if not found
    """
    supabase = get_supabase_client()

    try:
        response = supabase.table("jobs").select("*").eq("id", job_id).execute()

        if not response.data:
            return None

        return response.data[0]
    except Exception as e:
        logger.error(f"Error fetching job {job_id}: {str(e)}")
        return None


def update_job_status(
    job_id: str,
    status: str,
    results: Optional[list] = None,
    error: Optional[str] = None,
    status_message: Optional[str] = None,
    raw_output: Optional[str] = None,
    metadata: Optional[dict] = None
) -> None:
    """
    Update job status and optional fields in Supabase.

    Args:
        job_id: UUID of the job
        status: New status (pending, running, completed, failed, cancelled)
        results: List of Resource dictionaries (optional)
        error: Error message if failed (optional)
        status_message: Current progress message (optional)
        raw_output: Raw markdown output from crew (optional)
        metadata: Additional metadata (optional)

    Raises:
        Exception: If update fails
    """
    supabase = get_supabase_client()

    update_data = {"status": status}

    # Add completion timestamp if job is completed, failed, or cancelled
    if status in ["completed", "failed", "cancelled"]:
        update_data["completed_at"] = datetime.utcnow().isoformat()

    # Add optional fields if provided
    if results is not None:
        update_data["results"] = results
    if error is not None:
        update_data["error"] = error
    if status_message is not None:
        update_data["status_message"] = status_message
    if raw_output is not None:
        update_data["raw_output"] = raw_output
    if metadata is not None:
        update_data["metadata"] = metadata

    try:
        supabase.table("jobs").update(update_data).eq("id", job_id).execute()
    except Exception as e:
        raise Exception(f"Failed to update job {job_id}: {str(e)}")


def _generate_search_title(inputs: dict) -> str:
    """
    Generate a user-friendly search title from inputs.

    Args:
        inputs: Dictionary of course inputs

    Returns:
        str: User-friendly search title
    """
    # Priority order for title generation
    if inputs.get("book_title"):
        return inputs["book_title"]
    elif inputs.get("course_name") and inputs.get("university_name"):
        return f"{inputs['university_name']} - {inputs['course_name']}"
    elif inputs.get("course_name"):
        return inputs["course_name"]
    elif inputs.get("university_name"):
        return f"{inputs['university_name']} Course"
    elif inputs.get("textbook"):
        return inputs["textbook"]
    else:
        return "Course Resource Search"
