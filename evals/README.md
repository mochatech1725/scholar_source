# ScholarSource RAG Evals

This directory contains the evaluation harness for ScholarSource's RAG pipeline.

Normal tests answer: "Did the code behave as expected?"

Evals answer: "Were the retrieved sources and generated answer good enough?"

For ScholarSource, evals judge retrieval quality, source quality, citation coverage, weak-evidence behavior, and whether the final synthesis is grounded in stored evidence.

## Layout

```text
evals/
├── golden_cases.json
├── run_evals.py
├── README.md
└── results/
```

## Files

- `golden_cases.json`: representative student queries with expected source domains, forbidden source domains, and expected concepts.
- `run_evals.py`: local eval entrypoint. It currently validates the golden-case schema and reports suite readiness. It will call the RAG pipeline once `backend/rag/` exists.
- `results/`: generated eval summaries. Commit only small baseline summaries. Do not commit raw traces, private user content, provider responses, secrets, or large artifacts.

## Golden Case Schema

Each case must include:

- `id`: stable snake-case identifier.
- `input`: query payload shaped like a ScholarSource submission.
- `expected_domains`: credible domains that a good result may include.
- `forbidden_domains`: domains that should never appear in final cited sources.
- `expected_concepts`: concepts that should appear in grounded synthesis when evidence supports them.
- `notes`: short human-readable explanation of what the case is testing.

## Current Status

This is a scaffold. The current runner validates `golden_cases.json` but does not score the RAG pipeline yet.

Phase 3 should expand the seed set to 20 cases, then add scoring for:

- expected domain coverage
- forbidden domain exclusion
- citation coverage
- retrieved evidence relevance
- answer groundedness
- weak-evidence handling

## Local Usage

From the repo root:

```bash
uv run --extra dev run-evals
```

Write a small local summary:

```bash
uv run --extra dev run-evals --write-summary
```

The underlying file can still be run directly when debugging:

```bash
uv run --extra dev python evals/run_evals.py
```

If `just` is installed, the project also exposes package.json-style aliases:

```bash
just evals
just evals-summary
```

## CI Usage

Once the RAG pipeline is implemented, GitHub Actions should run:

```bash
uv run --extra dev run-evals
```

The command should fail when retrieval or generation quality drops below the agreed thresholds.
