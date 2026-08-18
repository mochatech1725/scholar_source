"""Retrieval RPC hardening tests (plan step 0.6.9).

The privileges themselves can only be proven against a running Postgres
(completion criterion 0.7.6 covers that check by hand). These tests are the
CI-runnable guard that the SQL which grants them cannot be quietly dropped or
reverted from either the incremental migration or the bootstrap schema.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HARDENING_MIGRATION = REPO_ROOT / "migrations" / "006_harden_rag_search_functions.sql"
BOOTSTRAP_SCHEMA = REPO_ROOT / "supabase_schema.sql"

RETRIEVAL_FUNCTIONS = (
    "match_rag_chunks(vector(1536), INT, TEXT)",
    "search_rag_chunks_lexical(TEXT, INT)",
)

SQL_FILES = (HARDENING_MIGRATION, BOOTSTRAP_SCHEMA)


@pytest.fixture(params=SQL_FILES, ids=lambda path: path.name)
def sql(request: pytest.FixtureRequest) -> str:
    return request.param.read_text()


@pytest.mark.parametrize("signature", RETRIEVAL_FUNCTIONS)
def test_public_execute_grant_is_revoked(sql: str, signature: str) -> None:
    assert f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC;" in sql


@pytest.mark.parametrize("signature", RETRIEVAL_FUNCTIONS)
def test_supabase_api_roles_are_revoked(sql: str, signature: str) -> None:
    # Supabase default privileges grant EXECUTE to `anon` and `authenticated`
    # directly, so revoking from PUBLIC alone would leave them able to call
    # the RPCs. The revoke runs per role through a format() template.
    assert "ARRAY['anon', 'authenticated']" in sql
    assert f"'REVOKE ALL ON FUNCTION {signature} FROM %I'," in sql


@pytest.mark.parametrize("signature", RETRIEVAL_FUNCTIONS)
def test_only_the_service_role_is_granted_execute(sql: str, signature: str) -> None:
    assert f"GRANT EXECUTE ON FUNCTION {signature} TO service_role;" in sql
    assert f"GRANT EXECUTE ON FUNCTION {signature} TO authenticated" not in sql
    assert f"GRANT EXECUTE ON FUNCTION {signature} TO anon" not in sql
    assert f"GRANT EXECUTE ON FUNCTION {signature} TO PUBLIC" not in sql


def test_both_functions_pin_their_search_path(sql: str) -> None:
    assert sql.count("SET search_path = public, extensions, pg_temp") == len(RETRIEVAL_FUNCTIONS)


def test_both_functions_are_security_invoker(sql: str) -> None:
    assert sql.count("SECURITY INVOKER") == len(RETRIEVAL_FUNCTIONS)
    assert "SECURITY DEFINER" not in sql


def test_match_limit_is_bounded(sql: str) -> None:
    clamp = "LIMIT LEAST(GREATEST(COALESCE(match_limit, 12), 1), 100);"
    assert sql.count(clamp) == len(RETRIEVAL_FUNCTIONS)
    assert "LIMIT match_limit;" not in sql
