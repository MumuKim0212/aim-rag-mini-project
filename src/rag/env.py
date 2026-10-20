"""Process setup shared by every script: load .env and force tracing off before any LangChain import."""

import os

from dotenv import load_dotenv

from . import ROOT

TRACING_VARS = ("LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2")


def setup() -> None:
    load_dotenv(ROOT / ".env")
    for var in TRACING_VARS:  # batch runs would send thousands of traces; .env cannot turn this back on
        os.environ[var] = "false"


def require_api_key() -> str:
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key or key.startswith("your-"):
        raise RuntimeError("GOOGLE_API_KEY is not set: copy .env.example to .env and fill in your own key")
    return key
