"""Input routing for the ScholarSource v2 normalization boundary."""

from backend.rag.input_adapters.dispatcher import (
    AdapterDispatcher,
    InputAdapter,
    PrimaryInputSelection,
    select_primary_input,
)

__all__ = [
    "AdapterDispatcher",
    "InputAdapter",
    "PrimaryInputSelection",
    "select_primary_input",
]
