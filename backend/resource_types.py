"""Shared resource type definitions for API and worker validation."""

from typing import Literal

type ResourceType = Literal[
    "textbooks",
    "practice_problem_sets",
    "practice_exams_tests",
    "lecture_videos",
    "lecture_notes",
    "online_courses",
    "reference_materials",
]

ALLOWED_RESOURCE_TYPES: tuple[ResourceType, ...] = (
    "textbooks",
    "practice_problem_sets",
    "practice_exams_tests",
    "lecture_videos",
    "lecture_notes",
    "online_courses",
    "reference_materials",
)

ALLOWED_RESOURCE_TYPE_SET = set(ALLOWED_RESOURCE_TYPES)
