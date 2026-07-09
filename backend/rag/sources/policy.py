"""Source quality policy: which candidate URLs are eligible for extraction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from backend.rag.models import QualityStatus, SourceRecord
from backend.security_utils import validate_url

MatchType = Literal["domain", "suffix"]
PolicyAction = Literal["rejected", "preferred"]

TRACKING_PARAM_PREFIXES: tuple[str, ...] = ("utm_", "fbclid", "gclid", "ref")


@dataclass(frozen=True)
class DomainRule:
    """One row from rag_domain_policies.

    A 'domain' rule matches the domain and all of its subdomains; a 'suffix'
    rule matches any host ending with the pattern (e.g. '.edu').
    """

    pattern: str
    match_type: MatchType
    policy: PolicyAction
    reason: str | None = None

    def matches(self, domain: str) -> bool:
        if self.match_type == "suffix":
            return domain.endswith(self.pattern)
        return domain == self.pattern or domain.endswith(f".{self.pattern}")


@dataclass(frozen=True)
class DomainPolicy:
    """The full rule set for one pipeline run, loaded from rag_domain_policies."""

    rules: tuple[DomainRule, ...]

    def first_match(self, domain: str, policy: PolicyAction) -> DomainRule | None:
        return next(
            (rule for rule in self.rules if rule.policy == policy and rule.matches(domain)),
            None,
        )


def normalize_url(url: str) -> str:
    """Canonicalize a URL so the same page always maps to one source row.

    Lowercases scheme and host, drops fragments and tracking parameters, and
    strips a trailing slash. This is the dedupe key for rag_sources.
    """
    parts = urlsplit(url.strip())
    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.casefold().startswith(TRACKING_PARAM_PREFIXES)
    ]
    normalized = urlunsplit(
        (
            parts.scheme.casefold(),
            parts.netloc.casefold(),
            parts.path.rstrip("/") or "/",
            urlencode(query_pairs),
            "",
        )
    )
    return normalized


def registered_domain(normalized_url: str) -> str:
    """Return the host with any www prefix removed."""
    host = urlsplit(normalized_url).netloc
    return host.removeprefix("www.")


def evaluate_source(source: SourceRecord, policy: DomainPolicy) -> SourceRecord:
    """Apply the accept/reject policy and return the updated record."""
    if not validate_url(source.url):
        return _decided(source, QualityStatus.REJECTED, "URL failed safety validation.")

    normalized_url = normalize_url(source.url)
    source = source.model_copy(update={"normalized_url": normalized_url})
    domain = registered_domain(normalized_url)
    rejected = policy.first_match(domain, "rejected")
    if rejected is not None:
        detail = rejected.reason or "on the rejected list"
        return _decided(source, QualityStatus.REJECTED, f"Domain {domain} rejected: {detail}.")

    if policy.first_match(domain, "preferred") is not None:
        return _decided(source, QualityStatus.ACCEPTED, f"Domain {domain} is a preferred education source.")

    return _decided(source, QualityStatus.ACCEPTED, f"Domain {domain} passed default checks.")


def _decided(source: SourceRecord, status: QualityStatus, reason: str) -> SourceRecord:
    return source.model_copy(update={"quality_status": status, "quality_reason": reason})
