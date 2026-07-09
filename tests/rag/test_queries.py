from backend.rag.sources.queries import generate_search_queries


def test_same_input_generates_identical_queries() -> None:
    first = generate_search_queries("  Engineering   Mechanics Statics ")
    second = generate_search_queries("Engineering Mechanics Statics")
    assert first == second


def test_queries_preserve_template_order() -> None:
    queries = generate_search_queries("linear algebra")
    assert queries[0] == "linear algebra study guide"
    assert len(queries) == 5
