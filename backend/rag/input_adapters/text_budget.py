"""Bound extracted text before it is handed to a chat model.

Extraction can produce far more text than a chat model can accept: a fetched
page is capped only by `max_fetch_bytes`, and an uploaded book is capped only
by `max_upload_pdf_bytes`. Truncation happens here, once, so every adapter
shortens text the same way and reports the same visible warning instead of
silently sending an oversized prompt.
"""

from __future__ import annotations

from dataclasses import dataclass

# How far back a truncation point may move to land on a line boundary. Cutting
# mid-sentence is acceptable; walking back further than this would discard
# usable text just to find a newline.
LINE_BOUNDARY_LOOKBACK_CHARS = 500


@dataclass(frozen=True, slots=True)
class BudgetedText:
    """Extracted text shortened to fit the outline model's input budget."""

    text: str
    original_chars: int
    budget_chars: int

    @property
    def is_truncated(self) -> bool:
        """Return whether any extracted text was dropped to fit the budget."""

        return len(self.text) < self.original_chars

    @property
    def warning(self) -> str | None:
        """Return a user-visible warning when the outline saw partial text."""

        if not self.is_truncated:
            return None
        return (
            f"Only the first {len(self.text)} of {self.original_chars} extracted characters were used to "
            "derive the learning outline; it may be incomplete."
        )


def apply_text_budget(text: str, *, budget_chars: int) -> BudgetedText:
    """Return `text` shortened to at most `budget_chars` characters."""

    if budget_chars <= 0:
        raise ValueError("Extracted-text budget must be positive.")
    if len(text) <= budget_chars:
        return BudgetedText(text=text, original_chars=len(text), budget_chars=budget_chars)
    head = text[:budget_chars]
    boundary = head.rfind("\n")
    if boundary > 0 and boundary >= budget_chars - LINE_BOUNDARY_LOOKBACK_CHARS and head[:boundary].strip():
        head = head[:boundary]
    return BudgetedText(text=head.rstrip(), original_chars=len(text), budget_chars=budget_chars)
