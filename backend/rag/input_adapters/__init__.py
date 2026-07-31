"""Input routing for the ScholarSource v2 normalization boundary."""

from backend.rag.input_adapters.dispatcher import (
    AdapterDispatcher,
    InputAdapter,
    PrimaryInputSelection,
    select_primary_input,
)
from backend.rag.input_adapters.references import InputSourceReference
from backend.rag.input_adapters.topic_list import TopicListAdapter

__all__ = [
    "AdapterDispatcher",
    "InputAdapter",
    "InputSourceReference",
    "PrimaryInputSelection",
    "TopicListAdapter",
    "select_primary_input",
]
