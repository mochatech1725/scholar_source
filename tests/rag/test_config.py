from backend.rag.config import DEFAULT_SETTINGS


def test_initial_chunking_settings_are_recorded() -> None:
    assert DEFAULT_SETTINGS.chunk_target_chars == 1400
    assert DEFAULT_SETTINGS.chunk_overlap_chars == 200
    assert DEFAULT_SETTINGS.chunk_min_chars == 200


def test_chunk_overlap_is_useful_but_bounded() -> None:
    assert DEFAULT_SETTINGS.chunk_overlap_chars >= DEFAULT_SETTINGS.chunk_min_chars
    assert DEFAULT_SETTINGS.chunk_overlap_chars < DEFAULT_SETTINGS.chunk_target_chars


def test_input_adapter_version_is_centralized() -> None:
    assert DEFAULT_SETTINGS.topic_list_adapter_version == "v1"


def test_outline_input_budget_is_recorded_and_bounded() -> None:
    assert DEFAULT_SETTINGS.max_outline_input_chars == 60_000
    assert DEFAULT_SETTINGS.max_outline_input_chars < DEFAULT_SETTINGS.max_fetch_bytes


def test_topic_grounding_thresholds_are_centralized() -> None:
    assert 0.0 < DEFAULT_SETTINGS.min_topic_evidence_coverage <= 1.0
    assert DEFAULT_SETTINGS.max_topic_chars == 120
    assert DEFAULT_SETTINGS.max_topic_chars < DEFAULT_SETTINGS.max_outline_input_chars
