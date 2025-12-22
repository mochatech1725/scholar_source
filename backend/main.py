"""
FastAPI Backend

Main FastAPI application for ScholarSource web interface.
Handles job submission, status polling, and shareable results.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative React dev port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        # Add production origins when deploying
        # "https://your-app.pages.dev",
        # "https://yourdomain.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

    return {
        "job_id": job["id"],
        "status": job["status"],
        "status_message": job.get("status_message"),
        "search_title": job.get("search_title"),
        "results": job.get("results"),
        "raw_output": job.get("raw_output"),
        "error": job.get("error"),
        "metadata": job.get("metadata"),
        "created_at": job["created_at"],
        "completed_at": job.get("completed_at")
    }


@app.get("/api/results/{job_id}", response_model=JobStatusResponse, tags=["Jobs"])
async def get_shareable_results(job_id: str):
    """
    Get results for a completed job (shareable link endpoint).

    This endpoint is designed for shareable links. It only returns
    results if the job is completed. Returns 404 if job doesn't exist
    or isn't completed yet.

    Args:
        job_id: UUID of the job

    Returns:
        JobStatusResponse: Job results and metadata

    Raises:
        HTTPException: If job not found or not completed
    """
    job = get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Results not found",
                "message": f"No job found with ID: {job_id}"
            }
        )

    if job["status"] != "completed":
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Results not available",
                "message": f"Job is {job['status']}. Results are only available for completed jobs."
            }
        )

    return {
        "job_id": job["id"],
        "status": job["status"],
        "status_message": job.get("status_message"),
        "search_title": job.get("search_title"),
        "results": job.get("results"),
        "raw_output": job.get("raw_output"),
        "error": job.get("error"),
        "metadata": job.get("metadata"),
        "created_at": job["created_at"],
        "completed_at": job.get("completed_at")
    }


# Development server command:
# uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
