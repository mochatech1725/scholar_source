"""
Unit tests for crew input validation.
"""

import importlib
import sys
import types

import pytest


@pytest.fixture
def crew_runner(monkeypatch):
    """Import crew_runner without initializing database-backed job dependencies."""
    sys.modules.pop("backend.crew_runner", None)

    jobs_module = types.ModuleType("backend.jobs")
    jobs_module.get_job = lambda *args, **kwargs: None
    jobs_module.update_job_status = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "backend.jobs", jobs_module)

    module = importlib.import_module("backend.crew_runner")
    yield module

    sys.modules.pop("backend.crew_runner", None)


@pytest.mark.parametrize(
    "field,value",
    [
        ("course_name", "Calculus I"),
        ("university_name", "MIT"),
        ("course_url", "https://ocw.mit.edu/courses/math"),
        ("topics_list", "limits, derivatives, integrals"),
        ("textbook", "Stewart Calculus"),
        ("book_title", "Introduction to Algorithms"),
        ("book_author", "Cormen"),
        ("isbn", "978-0262046305"),
        ("book_pdf_path", "/tmp/scholar_uploads/user/book.pdf"),
        ("book_url", "https://example.com/book.pdf"),
    ],
)
def test_validate_crew_inputs_accepts_supported_request_fields(crew_runner, field, value):
    """Every meaningful request input field should satisfy minimum validation."""
    assert crew_runner.validate_crew_inputs({field: value}) is True


def test_validate_crew_inputs_rejects_empty_inputs(crew_runner):
    """Empty and whitespace-only fields should not satisfy minimum validation."""
    inputs = {
        "course_name": " ",
        "university_name": "",
        "course_url": None,
        "topics_list": "   ",
        "textbook": "",
        "book_title": " ",
        "book_author": "",
        "isbn": None,
        "book_pdf_path": "",
        "book_url": " ",
    }

    assert crew_runner.validate_crew_inputs(inputs) is False
