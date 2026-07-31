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
