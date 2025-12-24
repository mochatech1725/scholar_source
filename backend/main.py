"""
FastAPI Backend

Main FastAPI application for ScholarSource web interface.
Handles job submission and status polling.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from backend.models import (
    CourseInputRequest,
    JobSubmitResponse,
    JobStatusResponse,
    HealthResponse
)
from backend.jobs import create_job, get_job
from backend.crew_runner import run_crew_async, validate_crew_inputs
from backend.database import get_supabase_client

# Initialize FastAPI app
app = FastAPI(
    title="ScholarSource API",
    description="Backend API for discovering educational resources aligned with course textbooks",
    version="0.1.0"
)

# CORS configuration - allow frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Vite dev server (primary port)
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Alternative Vite port (for reference)
        "http://127.0.0.1:5173",
        # Add production origins when deploying
        # "https://your-app.pages.dev",
        # "https://yourdomain.com",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - API information"""
    return {
        "message": "ScholarSource API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/health"
    }


@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns API status and database connectivity.
    """
    try:
        # Test database connection
        supabase = get_supabase_client()
        # Try a simple query to verify connection
        supabase.table("jobs").select("id").limit(1).execute()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "version": "0.1.0",
        "database": db_status
    }


@app.options("/api/submit", tags=["Jobs"])
async def submit_job_options():
    """Handle CORS preflight for submit endpoint"""
    return Response(status_code=200)


@app.post("/api/submit", response_model=JobSubmitResponse, tags=["Jobs"])
async def submit_job(request: CourseInputRequest):
    """
    Submit a new job to find educational resources.

    Validates inputs, creates a background job, and returns a job_id
    for status polling.

    Args:
        request: Course input parameters (at least one field required)

    Returns:
        JobSubmitResponse: Job ID and status

    Raises:
        HTTPException: If inputs are invalid or job creation fails
    """
    # Convert request to dict
    inputs = request.model_dump()

    # Validate that at least one input is provided
    if not validate_crew_inputs(inputs):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Invalid inputs",
                "message": "You must provide at least one of the following: "
                          "course information (course_name, university_name, or course_url), "
                          "book information (book_title + book_author, or ISBN), "
                          "book file (book_pdf_path), or book URL (book_url)"
            }
        )

    try:
        # Create job in database
        job_id = create_job(inputs)

        # Start background crew execution
        run_crew_async(job_id, inputs)

        return {
            "job_id": job_id,
            "status": "pending",
            "message": "Job created successfully. Use job_id to poll for status."
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Job creation failed",
                "message": str(e)
            }
        )


@app.get("/api/status/{job_id}", response_model=JobStatusResponse, tags=["Jobs"])
async def get_job_status(job_id: str):
    """
    Get the current status of a job.

    Poll this endpoint to check job progress and retrieve results
    when the job completes.

    Args:
        job_id: UUID of the job

    Returns:
        JobStatusResponse: Current job status and results (if completed)

    Raises:
        HTTPException: If job is not found
    """
    job = get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Job not found",
                "message": f"No job found with ID: {job_id}"
            }
        )

    # Extract relevant input fields for display
    inputs = job.get("inputs", {})
    
    return {
        "job_id": job["id"],
        "status": job["status"],
        "status_message": job.get("status_message"),
        "search_title": job.get("search_title"),
        "results": job.get("results"),
        "raw_output": job.get("raw_output"),
        "error": job.get("error"),
        "metadata": job.get("metadata"),
        "course_name": inputs.get("course_name") or None,
        "book_title": inputs.get("book_title") or None,
        "book_author": inputs.get("book_author") or None,
        "created_at": job["created_at"],
        "completed_at": job.get("completed_at")
    }


@app.post("/api/cancel/{job_id}", tags=["Jobs"])
async def cancel_job(job_id: str):
    """
    Cancel a running or pending job.

    Note: CrewAI jobs cannot be forcefully terminated mid-execution.
    This endpoint marks the job as cancelled in the database. If the job
    is still running, it will complete but the results will be marked as cancelled.

    Args:
        job_id: UUID of the job to cancel

    Returns:
        dict: Cancellation confirmation

    Raises:
        HTTPException: If job is not found or cannot be cancelled
    """
    job = get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Job not found",
                "message": f"No job found with ID: {job_id}"
            }
        )

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
        update_job_status(
            job_id,
            status="cancelled",
            status_message="Job cancelled by user",
            error="Job was cancelled before completion"
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
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Cancellation failed",
                "message": str(e)
            }
        )


# Development server command:
# uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
