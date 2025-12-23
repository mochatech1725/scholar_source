"""
Pydantic Models

Request and response models for the FastAPI backend.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime


class CourseInputRequest(BaseModel):
    """Request model for course input form submission"""

    university_name: Optional[str] = Field(None, description="University name")
    course_name: Optional[str] = Field(None, description="Course name")
    course_url: Optional[str] = Field(None, description="Course webpage URL")
    textbook: Optional[str] = Field(None, description="Textbook information (legacy)")
    topics_list: Optional[str] = Field(None, description="Comma-separated topics")
    book_title: Optional[str] = Field(None, description="Book title")
    book_author: Optional[str] = Field(None, description="Book author(s)")
    isbn: Optional[str] = Field(None, description="Book ISBN")
    book_pdf_path: Optional[str] = Field(None, description="Local PDF path")
    book_url: Optional[str] = Field(None, description="Book URL")
    email: Optional[EmailStr] = Field(None, description="Email address to receive results (optional)")

    class Config:
        json_schema_extra = {
            "example": {
                "university_name": "MIT",
                "course_name": "Introduction to Algorithms",
                "book_title": "Introduction to Algorithms",
                "book_author": "Cormen, Leiserson, Rivest, Stein"
            }
        }


class JobSubmitResponse(BaseModel):
    """Response model for job submission"""

    job_id: str = Field(..., description="UUID of created job")
    status: str = Field(..., description="Job status (always 'pending' on creation)")
    message: str = Field(..., description="Human-readable status message")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "pending",
                "message": "Job created successfully. Use job_id to poll status."
            }
        }


class Resource(BaseModel):
    """Model for a single educational resource"""

    type: str = Field(..., description="Resource type (PDF, Video, Course, etc.)")
    title: str = Field(..., description="Resource title")
    source: str = Field(..., description="Source/provider (e.g., MIT OCW)")
    url: str = Field(..., description="Direct URL to resource")
    description: Optional[str] = Field(None, description="Brief description")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "PDF",
                "title": "Introduction to Algorithms Lecture Notes",
                "source": "MIT OpenCourseWare",
                "url": "https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/resources/mit6_006s20_lec1/",
                "description": "Comprehensive lecture notes covering algorithm basics"
            }
        }


class JobStatusResponse(BaseModel):
    """Response model for job status queries"""

    job_id: str = Field(..., description="UUID of the job")
    status: str = Field(..., description="Job status (pending, running, completed, failed)")
    status_message: Optional[str] = Field(None, description="Current progress message")
    search_title: Optional[str] = Field(None, description="User-friendly job name")
    results: Optional[List[Resource]] = Field(None, description="List of resources (if completed)")
    raw_output: Optional[str] = Field(None, description="Raw markdown output from crew")
    error: Optional[str] = Field(None, description="Error message (if failed)")
    metadata: Optional[dict] = Field(None, description="Additional job metadata")
    created_at: str = Field(..., description="ISO timestamp of job creation")
    completed_at: Optional[str] = Field(None, description="ISO timestamp of completion")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "completed",
                "status_message": "Resource discovery completed successfully",
                "search_title": "MIT Introduction to Algorithms",
                "results": [
                    {
                        "type": "PDF",
                        "title": "OpenStax Algorithms Textbook",
                        "source": "OpenStax",
                        "url": "https://openstax.org/details/books/introduction-algorithms",
                        "description": "Free open textbook on algorithms"
                    }
                ],
                "created_at": "2025-01-15T10:30:00Z",
                "completed_at": "2025-01-15T10:33:45Z"
            }
        }


class HealthResponse(BaseModel):
    """Response model for health check"""

    status: str = Field(..., description="API health status")
    version: str = Field(..., description="API version")
    database: str = Field(..., description="Database connection status")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "0.1.0",
                "database": "connected"
            }
        }
