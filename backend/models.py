"""
Pydantic Models

Request and response models for the FastAPI backend.
"""

import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.resource_types import ALLOWED_RESOURCE_TYPES, ResourceType
from backend.security_utils import detect_prompt_injection, validate_domain_list, validate_text_input, validate_url
from backend.security_utils import validate_isbn as validate_isbn_format


class CourseInputRequest(BaseModel):
    """Request model for course input form submission"""

    course_name: str | None = Field(None, description="Course name")
    university_name: str | None = Field(None, description="University or institution name")
    subject: str | None = Field(None, description="Course subject or academic discipline")
    course_url: str | None = Field(None, description="Course webpage URL (required if no book info)")
    textbook: str | None = Field(None, description="Textbook information (legacy)")
    topics_list: str | None = Field(None, description="Comma-separated topics")
    book_title: str | None = Field(None, description="Book title")
    book_author: str | None = Field(None, description="Book author(s)")
    book_edition: str | None = Field(None, description="Book edition")
    isbn: str | None = Field(None, description="Book ISBN")
    book_upload_id: str | None = Field(None, description="Opaque ID returned by /api/upload-pdf")
    book_pdf_path: str | None = Field(None, description="Internal/legacy local PDF path")
    book_url: str | None = Field(None, description="Book URL")
    # Email field - COMMENTED OUT but kept for API compatibility
    email: str | None = Field(None, description="Email address to receive results (optional, currently disabled)")
    desired_resource_types: list[ResourceType] | None = Field(
        None,
        description=f"List of desired resource types. Allowed values: {', '.join(ALLOWED_RESOURCE_TYPES)}",
    )
    excluded_sites: str | None = Field(
        None,
        description=("Comma-separated list of domains to exclude from results (e.g., 'khanacademy.org, coursera.org')"),
    )
    targeted_sites: str | None = Field(
        None,
        description=(
            "Comma-separated list of domains to prioritize/target in search (e.g., 'stanford.edu, berkeley.edu')"
        ),
    )
    chapter: str | None = Field(
        None, description="Chapter name/number for section-by-section search (e.g., 'Chapter 16' or 'Vector Calculus')"
    )
    sections: str | None = Field(
        None,
        description=(
            "Comma-separated specific sections to focus on (e.g., '16.1, 16.4' or "
            "'Surface Integrals, Green's Theorem'). Narrows the search within the chapter."
        ),
    )
    preferred_creators: str | None = Field(
        None,
        description="Comma-separated preferred content creators (e.g., 'Professor Leonard, PatrickJMT, 3Blue1Brown')",
    )

    @model_validator(mode="before")
    @classmethod
    def convert_empty_strings_to_none(cls, data):
        """Convert empty strings to None for all optional fields"""
        if isinstance(data, dict):
            if isinstance(data.get("course_input"), dict):
                data = data["course_input"]
            return {k: None if (isinstance(v, str) and v.strip() == "") else v for k, v in data.items()}
        return data

    @field_validator("course_url", "book_url", mode="after")
    @classmethod
    def validate_urls(cls, v):
        """Validate URL format and check for security issues"""
        if v is None or v == "":
            return v

        # Validate URL format and scheme
        if not validate_url(v):
            raise ValueError("Invalid URL format or unsafe URL scheme")

        # Check for prompt injection in URL
        is_suspicious, reason = detect_prompt_injection(v)
        if is_suspicious:
            raise ValueError(f"URL contains suspicious patterns: {reason}")

        return v

    @field_validator("chapter", "sections", "preferred_creators", mode="after")
    @classmethod
    def validate_chapter_fields(cls, v):
        """Validate chapter and preferred_creators fields for length and security"""
        if v is None or v == "":
            return v

        is_valid, error = validate_text_input(v, max_length=200)
        if not is_valid:
            raise ValueError(error)

        is_suspicious, reason = detect_prompt_injection(v)
        if is_suspicious:
            raise ValueError(f"Input contains suspicious patterns: {reason}")

        return v

    @field_validator(
        "course_name",
        "university_name",
        "subject",
        "book_title",
        "book_author",
        "book_edition",
        "textbook",
        mode="after",
    )
    @classmethod
    def validate_text_fields(cls, v):
        """Validate text fields for length and security"""
        if v is None or v == "":
            return v

        # Validate text input (length, control characters)
        is_valid, error = validate_text_input(v, max_length=200)
        if not is_valid:
            raise ValueError(error)

        # Check for prompt injection
        is_suspicious, reason = detect_prompt_injection(v)
        if is_suspicious:
            raise ValueError(f"Input contains suspicious patterns: {reason}")

        return v

    @field_validator("topics_list", mode="after")
    @classmethod
    def validate_topics(cls, v):
        """Validate topics list for security"""
        if v is None or v == "":
            return v

        # Validate with longer max length for topics
        is_valid, error = validate_text_input(v, max_length=1000)
        if not is_valid:
            raise ValueError(error)

        # Check for prompt injection
        is_suspicious, reason = detect_prompt_injection(v)
        if is_suspicious:
            raise ValueError(f"Topics list contains suspicious patterns: {reason}")

        return v

    @field_validator("excluded_sites", "targeted_sites", mode="after")
    @classmethod
    def validate_sites(cls, v):
        """Validate domain lists"""
        if v is None or v == "":
            return v

        # Validate domain list format
        is_valid, error = validate_domain_list(v)
        if not is_valid:
            raise ValueError(error)

        return v

    @field_validator("isbn", mode="after")
    @classmethod
    def validate_isbn(cls, v):
        """Validate ISBN format"""
        if v is None or v == "":
            return v

        # Validate ISBN format
        is_valid, error = validate_isbn_format(v)
        if not is_valid:
            raise ValueError(error)

        return v

    @field_validator("book_upload_id", mode="after")
    @classmethod
    def validate_book_upload_id(cls, v):
        """Validate upload IDs without exposing server file paths."""
        if v is None or v == "":
            return v

        try:
            return str(uuid.UUID(v))
        except ValueError as error:
            raise ValueError("Invalid upload ID") from error

    # Email validation - COMMENTED OUT
    # @field_validator('email', mode='after')
    # @classmethod
    # def validate_email(cls, v):
    #     """Validate email format if provided"""
    #     if v is None:
    #         return None
    #     if isinstance(v, str):
    #         # Basic email validation regex
    #         email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    #         if re.match(email_pattern, v.strip()):
    #             return v.strip()
    #         # If invalid format, return None (don't raise error for optional field)
    #         return None
    #     return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "course_name": "Introduction to Algorithms",
                "university_name": "MIT",
                "course_url": "https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/",
                "book_title": "Introduction to Algorithms",
                "book_author": "Cormen, Leiserson, Rivest, Stein",
                "book_upload_id": "123e4567-e89b-12d3-a456-426614174000",
            }
        }
    )


class JobSubmitResponse(BaseModel):
    """Response model for job submission"""

    job_id: str = Field(..., description="UUID of created job")
    status: str = Field(..., description="Job status (always 'pending' on creation)")
    message: str = Field(..., description="Human-readable status message")
    warning: str | None = Field(None, description="Optional warning (e.g. no workers available)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "pending",
                "message": "Job created successfully. Use job_id to poll status.",
            }
        }
    )


class PdfUploadResponse(BaseModel):
    """Response model for PDF uploads."""

    upload_id: str = Field(..., description="Opaque PDF upload ID for use as book_upload_id")

    model_config = ConfigDict(json_schema_extra={"example": {"upload_id": "123e4567-e89b-12d3-a456-426614174000"}})


class WorkerHealthResponse(BaseModel):
    """Response model for worker health checks."""

    status: str = Field(..., description="Worker health status")
    workers_available: bool = Field(..., description="Whether any workers are available")
    worker_count: int = Field(..., description="Number of available workers")
    workers: list[str] = Field(..., description="Available worker names")
    message: str | None = Field(None, description="Optional worker health message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "workers_available": True,
                "worker_count": 1,
                "workers": ["celery@worker-1"],
            }
        }
    )


class CancelJobResponse(BaseModel):
    """Response model for job cancellation."""

    job_id: str = Field(..., description="UUID of the cancelled job")
    status: str = Field(..., description="Job status after cancellation")
    message: str = Field(..., description="Cancellation result message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "cancelled",
                "message": "Job cancelled successfully. The crew execution has been stopped.",
            }
        }
    )


class Resource(BaseModel):
    """Model for a single educational resource"""

    type: str = Field(..., description="Resource type (PDF, Video, Course, etc.)")
    title: str = Field(..., description="Resource title")
    source: str = Field(..., description="Source/provider (e.g., MIT OCW)")
    url: str = Field(..., description="Direct URL to resource")
    description: str | None = Field(None, description="Brief description")
    section: str | None = Field(None, description="Section name (chapter-aware mode only)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "PDF",
                "title": "Introduction to Algorithms Lecture Notes",
                "source": "MIT OpenCourseWare",
                "url": "https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/resources/mit6_006s20_lec1/",
                "description": "Comprehensive lecture notes covering algorithm basics",
            }
        }
    )


class JobStatusResponse(BaseModel):
    """Response model for job status queries"""

    job_id: str = Field(..., description="UUID of the job")
    status: str = Field(..., description="Job status (pending, running, completed, failed, cancelled)")
    status_message: str | None = Field(None, description="Current progress message")
    search_title: str | None = Field(None, description="User-friendly job name")
    results: list[Resource] | None = Field(None, description="List of resources (if completed)")
    raw_output: str | None = Field(None, description="Raw markdown output from crew")
    error: str | None = Field(None, description="Error message (if failed)")
    metadata: dict | None = Field(None, description="Additional job metadata")
    course_name: str | None = Field(None, description="Course name from inputs")
    university_name: str | None = Field(None, description="University or institution name from inputs")
    book_title: str | None = Field(None, description="Book title from inputs")
    book_author: str | None = Field(None, description="Book author from inputs")
    created_at: str = Field(..., description="ISO timestamp of job creation")
    completed_at: str | None = Field(None, description="ISO timestamp of completion")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "completed",
                "status_message": "Resource discovery completed successfully",
                "search_title": "MIT Introduction to Algorithms",
                "course_name": "Introduction to Algorithms",
                "university_name": "MIT",
                "results": [
                    {
                        "type": "PDF",
                        "title": "OpenStax Algorithms Textbook",
                        "source": "OpenStax",
                        "url": "https://openstax.org/details/books/introduction-algorithms",
                        "description": "Free open textbook on algorithms",
                    }
                ],
                "created_at": "2025-01-15T10:30:00Z",
                "completed_at": "2025-01-15T10:33:45Z",
            }
        }
    )


class HealthResponse(BaseModel):
    """Response model for health check"""

    status: str = Field(..., description="API health status")
    version: str = Field(..., description="API version")
    database: str = Field(..., description="Database connection status")

    model_config = ConfigDict(
        json_schema_extra={"example": {"status": "healthy", "version": "0.1.0", "database": "connected"}}
    )
