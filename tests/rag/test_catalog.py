from backend.rag.sources.catalog import CatalogSourceCollector


def test_same_topic_returns_identical_records() -> None:
    collector = CatalogSourceCollector()
    first = collector.collect("  Engineering   Mechanics Statics ")
    second = collector.collect("engineering mechanics statics")
    assert first == second
    assert len(first) >= 3


def test_records_carry_required_metadata() -> None:
    records = CatalogSourceCollector().collect("cellular respiration")
    assert records
    for record in records:
        assert record.source_type == "seed_catalog"
        assert record.normalized_url
        assert record.title
        assert record.metadata["collector"] == "catalog"


def test_unknown_topic_returns_empty_not_error() -> None:
    assert CatalogSourceCollector().collect("underwater basket weaving") == []
