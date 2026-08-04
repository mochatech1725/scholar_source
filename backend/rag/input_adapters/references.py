"""Stable provenance references shared by input normalization adapters."""

from enum import StrEnum


class InputSourceReference(StrEnum):
    """Validated request fields and logical field groups used in provenance."""

    TOPICS_LIST = "topics_list"
    COURSE_NAME = "course_name"
    UNIVERSITY_NAME = "university_name"
    SUBJECT = "subject"
    CHAPTER = "chapter"
    SECTIONS = "sections"
    DESIRED_RESOURCE_TYPES = "desired_resource_types"
    EXCLUDED_SITES = "excluded_sites"
    TARGETED_SITES = "targeted_sites"
    PREFERRED_CREATORS = "preferred_creators"
    RESOURCE_PREFERENCES = "resource_preferences"
    COURSE_URL = "course_url"
    BOOK_URL = "book_url"
    ISBN = "isbn"
    BOOK_TITLE = "book_title"
    BOOK_AUTHOR = "book_author"
    BOOK_EDITION = "book_edition"
    TEXTBOOK = "textbook"
