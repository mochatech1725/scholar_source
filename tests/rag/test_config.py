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


def test_uploaded_pdf_text_coverage_policy_is_recorded() -> None:
    assert DEFAULT_SETTINGS.uploaded_pdf_min_page_chars == 40
    assert DEFAULT_SETTINGS.uploaded_pdf_min_total_chars == 200
    assert DEFAULT_SETTINGS.uploaded_pdf_min_text_pages == 2
    assert DEFAULT_SETTINGS.uploaded_pdf_min_text_page_ratio == 0.2
