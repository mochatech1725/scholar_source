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


def create_job(inputs: dict, user_id: str, access_token: str = None) -> str:
    """
    Create a new job in Supabase database.

    Args:
        inputs: Dictionary of course input parameters
        user_id: UUID of the authenticated user
        access_token: Optional JWT access token for RLS authentication

    Returns:
        str: UUID of the created job

    Raises:
        Exception: If job creation fails
    """
    supabase = get_supabase_client(access_token=access_token)

    # Generate search title from inputs for user-friendly display
    search_title = _generate_search_title(inputs)

    job_data = {
        "user_id": user_id,
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


def get_job(job_id: str, access_token: str = None, use_service_role: bool = False) -> Optional[Dict[str, Any]]:
    """
    Get job data from Supabase database.

    Args:
        job_id: UUID of the job
        access_token: Optional JWT access token for RLS authentication (for API endpoints)
        use_service_role: If True, use service role key to bypass RLS (for background operations)

    Returns:
        dict | None: Job data dictionary or None if not found
    """
    supabase = get_supabase_client(access_token=access_token, use_service_role=use_service_role)

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
    metadata: Optional[dict] = None,
    access_token: str = None,
    use_service_role: bool = False
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
        access_token: Optional JWT access token for RLS authentication (for API endpoints)
        use_service_role: If True, use service role key to bypass RLS (for background operations)

    Raises:
        Exception: If update fails
    """
    supabase = get_supabase_client(access_token=access_token, use_service_role=use_service_role)

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

    This should represent the COURSE name, not the textbook.
    Textbook info is handled separately via textbook_info.

    Args:
        inputs: Dictionary of course inputs

    Returns:
        str: User-friendly search title (course name)
    """
    # Priority: Course information first (this is what appears under "Discovered Resources")
    if inputs.get("course_name") and inputs.get("university_name"):
        return f"{inputs['university_name']} - {inputs['course_name']}"
    elif inputs.get("course_name"):
        return inputs["course_name"]
    elif inputs.get("university_name"):
        return f"{inputs['university_name']} Course"
    # Fallback to textbook info if no course info provided
    elif inputs.get("textbook"):
        return inputs["textbook"]
    else:
        return "Course Resource Search"
