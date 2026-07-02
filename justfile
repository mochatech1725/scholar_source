set dotenv-load := false

default:
    just --list

lint:
    uv run --extra dev ruff check .

format-check:
    uv run --extra dev ruff format --check .

format:
    uv run --extra dev ruff format .

test:
    uv run --extra dev pytest tests/ -x

frontend-lint:
    cd web && npm run lint

frontend-test:
    cd web && npm run test:run

evals:
    uv run --extra dev run-evals

evals-summary:
    uv run --extra dev run-evals --write-summary

validate:
    uv run --extra dev ruff check .
    uv run --extra dev ruff format --check .
    uv run --extra dev pytest tests/ -x
    cd web && npm run lint
    cd web && npm run test:run
    uv run --extra dev run-evals
