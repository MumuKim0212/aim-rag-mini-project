"""Index building and the search tool. Methods are registered by name (retrieval.method).

Search result: list of chunk units (see chunking), best first, length k. Each scope (A, B) has its own
index under out/index/<index_key>/; the key changes whenever anything that shapes the index changes,
so variants never reuse a stale index.
"""

import hashlib
import json
from pathlib import Path
from typing import Callable

from . import ROOT

INDEX_ROOT = ROOT / "out" / "index"
INDEX_KEYS = ("corpus", "chunking", "embedding")

RETRIEVERS: dict[str, Callable] = {}


def register(name: str):
    def wrap(cls):
        RETRIEVERS[name] = cls
        return cls
    return wrap


def index_key(cfg: dict, scope: str) -> str:
    pages = ROOT / cfg["corpus"]["pages"]
    pages_hash = hashlib.sha1(pages.read_bytes()).hexdigest()[:10] if pages.exists() else "missing"
    blob = json.dumps({"scope": scope, "pages": pages_hash, **{k: cfg[k] for k in INDEX_KEYS}},
                      sort_keys=True, ensure_ascii=False, default=str)
    return f"{scope}-" + hashlib.sha1(blob.encode("utf-8")).hexdigest()[:10]


def index_dir(cfg: dict, scope: str) -> Path:
    return INDEX_ROOT / index_key(cfg, scope)


def build_index(chunks: list[dict], cfg: dict, scope: str) -> dict:
    """Embed chunks into index_dir(cfg, scope); write chunks.jsonl and build.json there.
    build.json holds {"n_chunks", "calls": [...]} with every embedding call recorded via llm.record_call,
    so index cost is reported separately from per-question cost."""
    raise NotImplementedError("baseline index — PLAN §3.1")


def load_retriever(cfg: dict, scope: str):
    """Return an object with .search(query: str) -> list[unit] for retrieval.method."""
    method = cfg["retrieval"]["method"]
    if method not in RETRIEVERS:
        raise KeyError(f"unknown retrieval.method {method!r}; registered: {sorted(RETRIEVERS)}")
    return RETRIEVERS[method](cfg, scope)


@register("vector")
class VectorRetriever:
    def __init__(self, cfg: dict, scope: str):
        raise NotImplementedError("baseline retrieval — PLAN §3.1")


@register("bm25")
class BM25Retriever:
    def __init__(self, cfg: dict, scope: str):
        raise NotImplementedError("card 004")


@register("hybrid")
class HybridRetriever:
    def __init__(self, cfg: dict, scope: str):
        raise NotImplementedError("card 004")
