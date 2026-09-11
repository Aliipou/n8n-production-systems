"""Run mock-llm with uvicorn."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.environ.get("MOCK_LLM_HOST", "127.0.0.1")
    port = int(os.environ.get("MOCK_LLM_PORT", "8090"))
    uvicorn.run("mock_llm.main:app", host=host, port=port)


if __name__ == "__main__":
    main()
