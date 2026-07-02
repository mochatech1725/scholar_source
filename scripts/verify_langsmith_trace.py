"""One-off check for Phase 0.4.3/0.4.4: make a single traced LLM call and
confirm it lands in the LangSmith dashboard with timing and token usage.

Run: .venv/bin/python3 scripts/verify_langsmith_trace.py
"""

import os
import sys

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

REQUIRED_ENV_VARS = (
    "LANGSMITH_TRACING",
    "LANGSMITH_API_KEY",
    "LANGSMITH_PROJECT",
    "OPENAI_API_KEY",
)


def _check_env() -> None:
    load_dotenv(".env.local")
    missing = [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]
    if missing:
        print(f"Missing required env vars: {', '.join(missing)}")
        sys.exit(1)


def main() -> None:
    _check_env()
    project = os.environ["LANGSMITH_PROJECT"]

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    response = llm.invoke("Reply with exactly one word: pong")

    print(f"Model replied: {response.content!r}")
    print(f"Check smith.langchain.com -> Projects -> {project} for the new trace.")


if __name__ == "__main__":
    main()
