"""
FastAPI Backend

Main FastAPI application for ScholarSource web interface.
Handles job submission and status polling.
"""

import os
import uuid

import filetype
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Depends, UploadFile, File
from uuid import UUID
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.models import (
    CourseInputRequest,
    JobSubmitResponse,
    JobStatusResponse,
    HealthResponse
)
from backend.jobs import create_job, get_job
from backend.crew_runner import run_crew_async, validate_crew_inputs
from backend.logging_config import configure_logging, get_logger
from backend.rate_limiter import limiter, rate_limit_handler
from backend.csrf_protection import validate_origin
from backend.celery_app import app as celery_app
from backend.error_utils import transform_error_for_user
from backend.auth import get_current_user, AuthenticationError
from backend.version import APP_VERSION
from slowapi.errors import RateLimitExceeded
from backend.env_loader import load_environment

# Load environment variables
load_environment()
# Constants
QUEUE_ELAPSED_TIME_THRESHOLD_SECONDS = 30  # Time in seconds before checking worker availability for queued jobs

# Configure centralized logging (console only, no log file)
configure_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_file=None,
    console_output=True
)

# Get logger for this module
logger = get_logger(__name__)
logger.info("Starting ScholarSource API...")

# Initialize FastAPI app
app = FastAPI(
    title="ScholarSource API",
    description="Backend API for discovering educational resources aligned with course textbooks",
    version=APP_VERSION
)

# Register rate limiter with app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# Register authentication exception handler
@app.exception_handler(AuthenticationError)
async def auth_exception_handler(request: Request, exc: AuthenticationError):
    """Handle authentication errors with 401 Unauthorized response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

# CORS configuration - allow frontend origins
_production_origins = [
    "https://scholar-source.pages.dev",  # Cloudflare Pages
]
_dev_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
_extra_origins = [
    o.strip()
    for o in os.getenv("EXTRA_ALLOWED_ORIGINS", "").split(",")
    if o.strip()
]
_allowed_origins = (
    _production_origins + _extra_origins
    if os.getenv("ENVIRONMENT", "local") == "production"
    else _production_origins + _dev_origins + _extra_origins
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # OPTIONS required for CORS preflight
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
    expose_headers=[],
)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - API information"""
    return {
        "message": "ScholarSource API",
        "version": APP_VERSION,
        "docs": "/docs",
        "health": "/api/health"
    }


def check_celery_workers() -> dict:
    """
    Check if Celery workers are running and connected.
    
    Returns:
        dict with 'available' (bool), 'count' (int), and 'workers' (list)
    """
    # Check if running in sync mode
    SYNC_MODE = os.getenv("SYNC_MODE", "false").lower() in ("true", "1", "yes")
    
    if SYNC_MODE:
        # In sync mode, workers are not needed (tasks run in-process)
        return {
            "available": True,
            "count": 1,
            "workers": ["sync-mode"],
            "mode": "sync"
        }
    
    if celery_app is None:
        return {
            "available": False,
            "count": 0,
            "workers": [],
            "error": "Celery app not initialized (SYNC_MODE may be enabled)"
        }
    
    try:
        # Use Celery's inspect API with a short timeout
        inspector = celery_app.control.inspect(timeout=2.0)
        active_workers = inspector.ping()
        
        if active_workers:
            worker_names = list(active_workers.keys())
            return {
                "available": True,
                "count": len(worker_names),
                "workers": worker_names
            }
        else:
            return {
                "available": False,
                "count": 0,
                "workers": []
            }
    except Exception as e:
        # Log technical details but return generic error
        logger.warning(f"Failed to check Celery workers: {e}")
        user_message, _ = transform_error_for_user(e)
        return {
            "available": False,
            "count": 0,
            "workers": [],
            "error": user_message
        }


@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns API status and database connectivity.
    """
    # Simplified health check for Railway startup
    # Database check can cause timeout during container startup
    return {
        "status": "healthy",
        "version": APP_VERSION,
        "database": "skipped"
    }


@app.get("/api/health/workers", tags=["Health"])
async def worker_health_check():
    """
    Check if Celery workers are available to process jobs.
    
    Returns worker availability status.
    """
    worker_status = check_celery_workers()
    
    if worker_status["available"]:
        return {
            "status": "healthy",
            "workers_available": True,
            "worker_count": worker_status["count"],
            "workers": worker_status["workers"]
        }
    else:
        return {
            "status": "degraded",
            "workers_available": False,
            "worker_count": 0,
            "workers": [],
            "message": "No Celery workers are currently running. Jobs will be queued but not processed."
        }


@app.post("/api/submit", response_model=JobSubmitResponse, tags=["Jobs"])
@limiter.limit("10/hour; 2/minute")
async def submit_job(
    request: Request,
    course_input: CourseInputRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Submit a new job to find educational resources.

    Validates inputs, creates a background job, and returns a job_id
    for status polling.

    Args:
        request: FastAPI request object (for rate limiting)
        course_input: Course input parameters (at least one field required)
        current_user: Authenticated user (automatically extracted from JWT)

    Returns:
        JobSubmitResponse: Job ID and status

    Raises:
        HTTPException: If inputs are invalid, origin is invalid, or job creation fails
        AuthenticationError: If authentication fails (401)
    """
    # Validate Origin header to prevent cross-origin POST requests
    validate_origin(request)

    # Extract user_id and access_token from authenticated user
    user_id = current_user["id"]
    access_token = current_user.get("access_token")
    logger.info(f"Job submission request from user: {user_id}")

    # Convert course_input to dict
    inputs = course_input.model_dump()

    # Validate that at least one input is provided
    if not validate_crew_inputs(inputs):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Invalid inputs",
                "message": "You must provide at least one of the following: "
                          "course URL (course_url), "
                          "book ISBN (isbn), "
                          "book file (book_pdf_path), or book URL (book_url)"
            }
        )

    try:
        logger.info(f"Creating new job with inputs: {inputs}")

        # Create job in database with user_id and access_token for RLS
        job_id = create_job(inputs, user_id, access_token=access_token)
        logger.info(f"Job created with ID: {job_id} for user: {user_id}")

        # Check if workers are available (non-blocking check)
        worker_status = check_celery_workers()

        # Start background crew execution.
        # Use BackgroundTasks to ensure this doesn't block the response,
        # even in SYNC_MODE
        background_tasks.add_task(run_crew_async, job_id, inputs)

        response = {
            "job_id": job_id,
            "status": "pending",
            "message": "Job created successfully. Use job_id to poll for status."
        }
        
        # Add warning if no workers are available
        if not worker_status["available"]:
            response["warning"] = "No workers currently available. Job is queued but may take longer to start."
            logger.warning(f"Job {job_id} submitted but no Celery workers are available")
        
        return response

    except Exception as e:
        # Log technical details for debugging
        logger.error(f"Job creation failed: {str(e)}", exc_info=True)

        # Transform error for user-friendly display
        user_message, _ = transform_error_for_user(e)

        raise HTTPException(
            status_code=500,
            detail={
                "error": "Job creation failed",
                "message": user_message
            }
        )


def verify_job_ownership(job: dict | None, job_id: UUID, user_id: str, action: str = "access") -> None:
    """
    Verify the job exists and belongs to the requesting user.
    Raises HTTPException 404 if the job is absent, 403 if it belongs to another user.
    `action` is used in the 403 message (e.g. "access", "cancel").
    """
    if not job:
        raise HTTPException(
            status_code=404,
            detail={"error": "Job not found", "message": f"No job found with ID: {job_id}"}
        )
    if job.get("user_id") != user_id:
        raise HTTPException(
            status_code=403,
            detail={"error": "Forbidden", "message": f"You do not have permission to {action} this job"}
        )


@app.get("/api/status/{job_id}", response_model=JobStatusResponse, tags=["Jobs"])
@limiter.limit("100/minute")
async def get_job_status(
    request: Request,
    job_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the current status of a job.

    Poll this endpoint to check job progress and retrieve results
    when the job completes.

    Args:
        job_id: UUID of the job
        current_user: Authenticated user (automatically extracted from JWT)

    Returns:
        JobStatusResponse: Current job status and results (if completed)

    Raises:
        HTTPException: If job is not found or user is not authorized
        AuthenticationError: If authentication fails (401)
    """
    user_id = current_user["id"]
    access_token = current_user.get("access_token")
    job = get_job(str(job_id), access_token=access_token)

    # Verify job exists and belongs to this user (RLS enforces this too, but double-check)
    verify_job_ownership(job, job_id, user_id, action="access")

    # Extract relevant input fields for display
    inputs = job.get("inputs", {})
    status_message = job.get("status_message")
    
    # Check if job is stuck in "queued" status (workers may be down)
    if job["status"] == "queued":
        try:
            created_at = datetime.fromisoformat(job["created_at"].replace("Z", "+00:00"))
            age_seconds = (datetime.now(timezone.utc) - created_at).total_seconds()
            
            # If queued for more than threshold, check worker availability
            if age_seconds > QUEUE_ELAPSED_TIME_THRESHOLD_SECONDS:
                worker_status = check_celery_workers()
                if not worker_status["available"]:
                    status_message = "⚠️ Job is queued but no workers are available. Workers may be starting up or offline."
                    logger.warning(f"Job {job_id} stuck in queue - no workers available")
        except Exception as e:
            logger.debug(f"Could not check queue age for job {job_id}: {e}")
    
    return {
        "job_id": job["id"],
        "status": job["status"],
        "status_message": status_message,
        "search_title": job.get("search_title"),
        "results": job.get("results"),
        "raw_output": job.get("raw_output"),
        "error": job.get("error"),
        "metadata": job.get("metadata"),
        "course_name": inputs.get("course_name") or None,
        "university_name": inputs.get("university_name") or None,
        "book_title": inputs.get("book_title") or None,
        "book_author": inputs.get("book_author") or None,
        "created_at": job["created_at"],
        "completed_at": job.get("completed_at")
    }


@app.post("/api/cancel/{job_id}", tags=["Jobs"])
@limiter.limit("20/hour")
async def cancel_job(
    request: Request,
    job_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Cancel a running or pending job.

    Note: CrewAI jobs cannot be forcefully terminated mid-execution.
    This endpoint marks the job as cancelled in the database. If the job
    is still running, it will complete but the results will be marked as cancelled.

    Args:
        request: FastAPI request object (for rate limiting and origin validation)
        job_id: UUID of the job to cancel
        current_user: Authenticated user (automatically extracted from JWT)

    Returns:
        dict: Cancellation confirmation

    Raises:
        HTTPException: If origin is invalid, job is not found, or cannot be cancelled
        AuthenticationError: If authentication fails (401)
    """
    # Validate Origin header to prevent cross-origin POST requests
    validate_origin(request)

    user_id = current_user["id"]
    access_token = current_user.get("access_token")
    job = get_job(str(job_id), access_token=access_token)

    verify_job_ownership(job, job_id, user_id, action="cancel")

    current_status = job.get("status")

    # Can only cancel pending or running jobs
    if current_status in ["completed", "failed", "cancelled"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Cannot cancel job",
                "message": f"Job is already {current_status}"
            }
        )

    # Attempt to cancel the running crew task
    try:
        from backend.crew_runner import cancel_crew_job
        from backend.jobs import update_job_status

        # Try to cancel the async task
        task_cancelled = cancel_crew_job(job_id)

        # Mark job as cancelled in database
        access_token = current_user.get("access_token")
        update_job_status(
            job_id,
            status="cancelled",
            status_message="Job cancelled by user",
            error="Job was cancelled before completion",
            access_token=access_token
        )

        if task_cancelled:
            message = "Job cancelled successfully. The crew execution has been stopped."
        else:
            message = "Job marked as cancelled. The crew task was not actively running."

        return {
            "job_id": job_id,
            "status": "cancelled",
            "message": message
        }
    except Exception as e:
        # Log technical details for debugging
        logger.error(f"Job cancellation failed: {str(e)}", exc_info=True)

        # Transform error for user-friendly display
        user_message, _ = transform_error_for_user(e)

        raise HTTPException(
            status_code=500,
            detail={
                "error": "Cancellation failed",
                "message": user_message
            }
        )


@app.post("/api/upload-pdf", tags=["Jobs"])
@limiter.limit("5/hour")
async def upload_pdf(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a PDF textbook for chapter-aware resource search.

    Saves the file to a temporary location and returns the path,
    which should be passed as book_pdf_path in a subsequent /api/submit call.

    Args:
        file: PDF file to upload (max 50 MB)
        current_user: Authenticated user (automatically extracted from JWT)

    Returns:
        dict: {"pdf_path": "/tmp/scholar_uploads/{user_id}/{uuid}.pdf"}

    Raises:
        HTTPException: If file is invalid or upload fails
        AuthenticationError: If authentication fails (401)
    """
    validate_origin(request)
    user_id = current_user["id"]

    # Validate file type by extension and content-type
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid file type", "message": "Only PDF files are accepted"}
        )
    content_type = file.content_type or ""
    if "pdf" not in content_type.lower():
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid content type", "message": "File must be a PDF (application/pdf)"}
        )

    # Read and check size (50 MB limit)
    MAX_SIZE = 50 * 1024 * 1024
    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(
            status_code=413,
            detail={"error": "File too large", "message": "PDF must be 50 MB or smaller"}
        )

    # Validate true file type via magic bytes (not just extension/content-type)
    kind = filetype.guess(contents[:2048])
    detected_mime = kind.mime if kind else None
    if detected_mime != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid file", "message": "File contents do not match a valid PDF"}
        )

    # Save to scoped temp directory
    upload_dir = f"/tmp/scholar_uploads/{user_id}"
    os.makedirs(upload_dir, exist_ok=True)
    pdf_path = f"{upload_dir}/{uuid.uuid4()}.pdf"

    try:
        with open(pdf_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        logger.error(f"PDF upload failed for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Upload failed", "message": "Could not save uploaded file"}
        )

    logger.info(f"PDF uploaded for user {user_id}: {pdf_path}")
    return {"pdf_path": pdf_path}


# Development server command:
# uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
