"""Keep derived learning topics tied to the text the outline model saw.

Page and PDF text is attacker-controlled, and derived topics flow straight
into search-query generation. A topic the extracted content does not support
is therefore not merely a quality problem: it is either a hallucination or
content the model was talked into emitting. This module is the deterministic
gate that drops those topics before they leave normalization.

The matching rule is intentionally crude and symmetric: both sides are reduced
to word stems the same way, so a topic matches itself, tolerates plurals, and
tolerates nothing else. It is a support check, not a semantic similarity
score — an abstractive paraphrase that shares no vocabulary with the page is
exactly what this is meant to catch.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

# Words carrying no topical meaning. A topic is judged on the rest, so
# "The theory of relativity" stands or falls on "theory" and "relativity".
TOPIC_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "into",
        "is",
        "its",
        "of",
        "on",
        "or",
        "the",
        "their",
        "this",
        "to",
        "with",
    }
)

# Unicode word characters minus the underscore: keeps accented terms whole
# while splitting on punctuation, markup remnants, and symbols.
_WORD_PATTERN = re.compile(r"[^\W_]+")

# A topic is a concept to search for, never an address. A URL-shaped topic
# would carry an attacker's destination into query generation even though
# every one of its words appears on the page.
_ADDRESS_PATTERN = re.compile(r"(?i)https?://|www\.|\S+@\S+")


@dataclass(frozen=True, slots=True)
class SupportedTopics:
    """Derived topics that survived the evidence check, and how many did not."""

    topics: list[str]
    dropped_count: int

    @property
    def warning(self) -> str | None:
        """Return a user-visible warning when derived topics were dropped."""

        if not self.dropped_count:
            return None
        return f"{self.dropped_count} derived topic(s) were dropped because the extracted content did not support them."


def filter_supported_topics(
    topics: Iterable[str],
    *,
    evidence_text: str,
    min_coverage: float,
    max_topic_chars: int,
) -> SupportedTopics:
    """Return only the topics `evidence_text` supports, in their original order."""

    if not 0.0 < min_coverage <= 1.0:
        raise ValueError("Topic evidence coverage must be greater than 0 and at most 1.")
    if max_topic_chars <= 0:
        raise ValueError("Maximum topic length must be positive.")

    evidence_stems = _stems(evidence_text)
    supported: list[str] = []
    dropped = 0
    for topic in topics:
        if _is_supported(topic, evidence_stems, min_coverage=min_coverage, max_topic_chars=max_topic_chars):
            supported.append(topic)
        else:
            dropped += 1
    return SupportedTopics(topics=supported, dropped_count=dropped)


def _is_supported(
    topic: str,
    evidence_stems: set[str],
    *,
    min_coverage: float,
    max_topic_chars: int,
) -> bool:
    candidate = topic.strip()
    if not candidate or len(candidate) > max_topic_chars:
        return False
    # Line breaks and addresses are instruction and payload shapes, not the
    # shape of a concept a student searches for.
    if "\n" in candidate or "\r" in candidate or _ADDRESS_PATTERN.search(candidate):
        return False
    topic_stems = _stems(candidate)
    if not topic_stems:
        return False
    matched = len(topic_stems & evidence_stems)
    return matched / len(topic_stems) >= min_coverage


def _stems(text: str) -> set[str]:
    return {stem for word in _WORD_PATTERN.findall(text.casefold()) if (stem := _stem(word)) not in TOPIC_STOPWORDS}


def _stem(word: str) -> str:
    # One trailing plural "s", nothing more. Applied identically to evidence
    # and topics, so this can only ever merge a word with its own plural.
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word
