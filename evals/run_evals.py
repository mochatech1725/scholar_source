"""Validate and summarize the ScholarSource RAG golden eval cases.

This is a scaffold runner. It validates the eval contract before the RAG
pipeline exists, then reports that scoring is not wired yet.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
GOLDEN_CASES_PATH = ROOT / "golden_cases.json"
RESULTS_DIR = ROOT / "results"

REQUIRED_CASE_FIELDS = (
    "id",
    "input",
    "expected_domains",
    "forbidden_domains",
    "expected_concepts",
    "notes",
)


@dataclass(frozen=True)
class EvalSuite:
    """Validated golden-case suite metadata."""

    version: int
    suite: str
    description: str
    cases: list[dict[str, Any]]


class GoldenCaseError(ValueError):
    """Raised when the golden-case file does not match the eval contract."""


def _load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError as exc:
        raise GoldenCaseError(f"Missing golden-case file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise GoldenCaseError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise GoldenCaseError("golden_cases.json must contain a JSON object.")

    return data


def _require_string(value: Any, field_name: str, case_id: str | None = None) -> str:
    if not isinstance(value, str) or not value.strip():
        target = f"case {case_id!r}" if case_id else "suite"
        raise GoldenCaseError(f"{target} field {field_name!r} must be a non-empty string.")
    return value


def _require_string_list(value: Any, field_name: str, case_id: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise GoldenCaseError(f"case {case_id!r} field {field_name!r} must be a non-empty list.")

    invalid_values = [item for item in value if not isinstance(item, str) or not item.strip()]
    if invalid_values:
        raise GoldenCaseError(f"case {case_id!r} field {field_name!r} contains non-string or empty values.")

    return value


def _validate_case(raw_case: Any, seen_ids: set[str]) -> dict[str, Any]:
    if not isinstance(raw_case, dict):
        raise GoldenCaseError("Each eval case must be a JSON object.")

    missing = [field for field in REQUIRED_CASE_FIELDS if field not in raw_case]
    if missing:
        raise GoldenCaseError(f"Eval case is missing required fields: {', '.join(missing)}")

    case_id = _require_string(raw_case["id"], "id")
    if case_id in seen_ids:
        raise GoldenCaseError(f"Duplicate eval case id: {case_id}")
    seen_ids.add(case_id)

    if not isinstance(raw_case["input"], dict) or not raw_case["input"]:
        raise GoldenCaseError(f"case {case_id!r} field 'input' must be a non-empty object.")

    _require_string_list(raw_case["expected_domains"], "expected_domains", case_id)
    _require_string_list(raw_case["forbidden_domains"], "forbidden_domains", case_id)
    _require_string_list(raw_case["expected_concepts"], "expected_concepts", case_id)
    _require_string(raw_case["notes"], "notes", case_id)

    return raw_case


def load_suite(path: Path = GOLDEN_CASES_PATH) -> EvalSuite:
    """Load and validate the golden-case suite."""

    data = _load_json(path)

    version = data.get("version")
    if not isinstance(version, int) or version < 1:
        raise GoldenCaseError("suite field 'version' must be a positive integer.")

    suite = _require_string(data.get("suite"), "suite")
    description = _require_string(data.get("description"), "description")

    raw_cases = data.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise GoldenCaseError("suite field 'cases' must be a non-empty list.")

    seen_ids: set[str] = set()
    cases = [_validate_case(raw_case, seen_ids) for raw_case in raw_cases]

    return EvalSuite(
        version=version,
        suite=suite,
        description=description,
        cases=cases,
    )


def _build_summary(suite: EvalSuite) -> dict[str, Any]:
    case_ids = [case["id"] for case in suite.cases]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "suite": suite.suite,
        "version": suite.version,
        "case_count": len(suite.cases),
        "case_ids": case_ids,
        "status": "schema_valid_pipeline_scoring_not_implemented",
    }


def _write_summary(summary: dict[str, Any]) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RESULTS_DIR / "latest_stub_summary.json"
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)
        file.write("\n")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ScholarSource RAG evals.")
    parser.add_argument(
        "--golden-cases",
        default=str(GOLDEN_CASES_PATH),
        help="Path to golden_cases.json.",
    )
    parser.add_argument(
        "--write-summary",
        action="store_true",
        help="Write a small scaffold summary to evals/results/latest_stub_summary.json.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    suite = load_suite(Path(args.golden_cases))
    summary = _build_summary(suite)

    print(f"Eval suite: {suite.suite} v{suite.version}")
    print(f"Golden cases: {len(suite.cases)}")
    print("Status: schema valid; RAG pipeline scoring is not implemented yet.")

    if args.write_summary:
        output_path = _write_summary(summary)
        print(f"Wrote scaffold summary: {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
