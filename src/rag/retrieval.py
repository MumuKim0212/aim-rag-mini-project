"""Index building and the search tool. Methods are registered by name (retrieval.method).

Search result: list of chunk units (see chunking), best first, length k, each with a `score`.
Each scope (A, B) has its own index under out/index/<index_key>/; the key changes whenever anything that
shapes the index changes (corpus text, chunking, embedding), so variants never reuse a stale index and a
variant that changes only retrieval reuses the baseline index.

out/index/<key>/
    chunks.jsonl   every chunk unit
    chroma/        vectors (cosine), ids = chunk_id
    build.json     {"n_chunks", "chars", "tokens", "tokens_per_char", "calls": [...], ...}
"""

import hashlib
import json
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

import chromadb
from chromadb.config import Settings

from . import ROOT, llm
from .ingest import title_of

INDEX_ROOT = ROOT / "out" / "index"
INDEX_KEYS = ("corpus", "chunking", "embedding")
EMBED_BATCH = 50

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


def document_text(chunk: dict, cfg: dict) -> str:
    """What is embedded for a chunk (embedding.text_format); the stored content stays the chunk text."""
    fmt = cfg["embedding"].get("text_format") or "none"
    if fmt == "gemini2_qa":
        return f"title: {title_of(chunk['source'], cfg)} | text: {chunk['content']}"
    if fmt == "none":
        return chunk["content"]
    raise KeyError(f"unknown embedding.text_format {fmt!r}")


def query_text(query: str, cfg: dict) -> str:
    fmt = cfg["embedding"].get("text_format") or "none"
    if fmt == "gemini2_qa":
        return f"task: question answering | query: {query}"
    if fmt == "none":
        return query
    raise KeyError(f"unknown embedding.text_format {fmt!r}")


def _collection(path: Path):
    db = chromadb.PersistentClient(path=str(path / "chroma"), settings=Settings(anonymized_telemetry=False))
    return db.get_or_create_collection("chunks", metadata={"hnsw:space": "cosine"})


def build_index(chunks: list[dict], cfg: dict, scope: str) -> dict:
    """Embed chunks into index_dir(cfg, scope). Token counts come from count_tokens (embed_content
    reports none); every embedding call is recorded in build.json for index_build_usd."""
    target = index_dir(cfg, scope)
    if (target / "build.json").exists():
        raise FileExistsError(f"{target} already built")
    shutil.rmtree(target, ignore_errors=True)  # leftovers of a failed build
    target.mkdir(parents=True)
    steps, model, collection = {"calls": []}, cfg["embedding"]["model"], None
    try:
        collection = _collection(target)
        for i in range(0, len(chunks), EMBED_BATCH):
            batch = chunks[i:i + EMBED_BATCH]
            texts = [document_text(c, cfg) for c in batch]
            tokens = llm.count_tokens(texts, model)
            vectors = llm.embed(texts, embedding_cfg=cfg["embedding"], purpose="document", steps=steps,
                                node="index", tokens=tokens)
            collection.add(ids=[c["chunk_id"] for c in batch], embeddings=vectors,
                           documents=[c["content"] for c in batch],
                           metadatas=[{"source": c["source"], "page": c["page"]} for c in batch])
    except BaseException:
        collection = None  # release the handle before removing the folder
        shutil.rmtree(target, ignore_errors=True)
        raise
    with (target / "chunks.jsonl").open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    chars = sum(len(document_text(c, cfg)) for c in chunks)
    tokens = sum(c["input_tokens"] for c in steps["calls"])
    info = {"scope": scope, "index_key": target.name, "n_chunks": len(chunks), "chars": chars, "tokens": tokens,
            "tokens_per_char": tokens / chars if chars else None, "settings": {k: cfg[k] for k in INDEX_KEYS},
            "calls": steps["calls"], "created_at": datetime.now().isoformat(timespec="seconds")}
    (target / "build.json").write_text(json.dumps(info, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return info


def load_retriever(cfg: dict, scope: str):
    """Return an object with .search(query, steps=None) -> list[unit] for retrieval.method."""
    method = cfg["retrieval"]["method"]
    if method not in RETRIEVERS:
        raise KeyError(f"unknown retrieval.method {method!r}; registered: {sorted(RETRIEVERS)}")
    return RETRIEVERS[method](cfg, scope)


@register("vector")
class VectorRetriever:
    def __init__(self, cfg: dict, scope: str):
        if cfg["retrieval"].get("mmr"):
            raise NotImplementedError("retrieval.mmr — card 005")
        self.cfg, self.dir = cfg, index_dir(cfg, scope)
        build = self.dir / "build.json"
        if not build.exists():
            raise FileNotFoundError(f"no index for scope {scope} ({self.dir}); run scripts/build_index.py first")
        self.tokens_per_char = json.loads(build.read_text(encoding="utf-8"))["tokens_per_char"] or 0.0
        with (self.dir / "chunks.jsonl").open(encoding="utf-8") as f:
            self.chunks = {c["chunk_id"]: c for c in map(json.loads, f)}
        self.collection = _collection(self.dir)
        self._lock = threading.Lock()

    def search(self, query: str, steps: dict | None = None) -> list[dict]:
        steps = steps if steps is not None else {}
        start = time.perf_counter()
        text = query_text(query, self.cfg)
        [vector] = llm.embed([text], embedding_cfg=self.cfg["embedding"], purpose="query", steps=steps,
                             node="query_embed", tokens=round(len(text) * self.tokens_per_char), estimated=True)
        with self._lock:
            hits = self.collection.query(query_embeddings=[vector], n_results=self.cfg["retrieval"]["k"],
                                         include=["distances"])
        units = [{**self.chunks[cid], "score": round(1 - dist, 4)}
                 for cid, dist in zip(hits["ids"][0], hits["distances"][0])]
        steps.setdefault("search_seconds", []).append(round(time.perf_counter() - start, 3))
        return units


@register("bm25")
class BM25Retriever:
    def __init__(self, cfg: dict, scope: str):
        raise NotImplementedError("card 004")


@register("hybrid")
class HybridRetriever:
    def __init__(self, cfg: dict, scope: str):
        raise NotImplementedError("card 004")
