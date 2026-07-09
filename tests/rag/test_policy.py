from backend.rag.models import SourceRecord
from backend.rag.sources.policy import DomainPolicy, DomainRule, evaluate_source, normalize_url

POLICY = DomainPolicy(
    rules=(
        DomainRule(pattern="chegg.com", match_type="domain", policy="rejected", reason="paywalled answer mill"),
        DomainRule(pattern=".edu", match_type="suffix", policy="preferred"),
    )
)


def _source(url: str) -> SourceRecord:
    return SourceRecord(url=url, normalized_url=normalize_url(url), title="t", source_type="web_search")


def test_answer_mills_are_rejected() -> None:
    decided = evaluate_source(_source("https://www.chegg.com/homework-help/statics"), POLICY)
    assert decided.quality_status.value == "rejected"
    assert "paywalled answer mill" in decided.quality_reason


def test_edu_domains_are_accepted() -> None:
    decided = evaluate_source(_source("https://ocw.mit.edu/courses/statics"), POLICY)
    assert decided.quality_status.value == "accepted"


def test_unlisted_domains_still_pass_default_checks() -> None:
    decided = evaluate_source(_source("https://statics-notes.example.org/lectures"), POLICY)
    assert decided.quality_status.value == "accepted"


def test_normalize_url_strips_tracking_and_fragments() -> None:
    url = "https://Example.edu/Notes/?utm_source=x&topic=statics#section-2"
    assert normalize_url(url) == "https://example.edu/Notes?topic=statics"
