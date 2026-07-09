"""Deterministic search-query generation for a normalized student input.

v1's largest instability was LLM-generated search queries changing between
identical runs. v2 expands the normalized input through fixed templates so
the same input always produces the same queries, in the same order.
"""

from __future__ import annotations

QUERY_TEMPLATES: tuple[str, ...] = (
    "{topic} study guide",
    "{topic} lecture notes",
    "{topic} open textbook",
    "{topic} tutorial explained",
    "{topic} practice problems with solutions",
)


def normalize_topic(raw_input: str) -> str:
    """Collapse whitespace so equivalent inputs generate identical queries."""
    return " ".join(raw_input.split())


def generate_search_queries(raw_input: str) -> list[str]:
    """Expand a student topic into a fixed, ordered set of search queries."""
    topic = normalize_topic(raw_input)
    if not topic:
        raise ValueError("Cannot generate search queries for empty input.")
    return [template.format(topic=topic) for template in QUERY_TEMPLATES]
