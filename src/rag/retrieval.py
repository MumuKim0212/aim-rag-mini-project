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
import numpy as np
from chromadb.config import Settings
from rank_bm25 import BM25Okapi

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


def _load_chunks(cfg: dict, scope: str) -> tuple[Path, dict]:
    directory = index_dir(cfg, scope)
    if not (directory / "build.json").exists():
        raise FileNotFoundError(f"no index for scope {scope} ({directory}); run scripts/build_index.py first")
    with (directory / "chunks.jsonl").open(encoding="utf-8") as f:
        return directory, {c["chunk_id"]: c for c in map(json.loads, f)}


@register("vector")
class VectorRetriever:
    def __init__(self, cfg: dict, scope: str):
        self.cfg = cfg
        self.dir, self.chunks = _load_chunks(cfg, scope)
        self.tokens_per_char = json.loads((self.dir / "build.json").read_text(encoding="utf-8"))["tokens_per_char"] or 0.0
        self.collection = _collection(self.dir)
        self._lock = threading.Lock()

    def _embed_query(self, query: str, steps: dict) -> list[float]:
        text = query_text(query, self.cfg)
        [vector] = llm.embed([text], embedding_cfg=self.cfg["embedding"], purpose="query", steps=steps,
                             node="query_embed", tokens=round(len(text) * self.tokens_per_char), estimated=True)
        return vector

    def search_n(self, query: str, n: int, steps: dict) -> list[dict]:
        """The n nearest chunks by cosine similarity, best first (score = similarity)."""
        vector = self._embed_query(query, steps)
        with self._lock:
            hits = self.collection.query(query_embeddings=[vector], n_results=n, include=["distances"])
        return [{**self.chunks[cid], "score": round(1 - dist, 4)} for cid, dist in zip(hits["ids"][0], hits["distances"][0])]

    def _mmr(self, query: str, k: int, steps: dict) -> list[dict]:
        """Maximal marginal relevance over the nearest max(4k, 20) chunks: pick the chunk that maximises
        lambda * sim(query, chunk) - (1 - lambda) * max sim(chunk, already picked)."""
        weight = self.cfg["retrieval"]["mmr_lambda"]
        vector = self._embed_query(query, steps)
        with self._lock:
            hits = self.collection.query(query_embeddings=[vector], n_results=max(4 * k, 20),
                                         include=["distances", "embeddings"])
        ids = hits["ids"][0]
        vectors = np.asarray(hits["embeddings"][0], dtype=float)
        vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        relevance = [1 - d for d in hits["distances"][0]]
        picked: list[int] = []
        while len(picked) < min(k, len(ids)):
            best, best_score = None, -np.inf
            for j in range(len(ids)):
                if j in picked:
                    continue
                redundancy = max((float(vectors[j] @ vectors[i]) for i in picked), default=0.0)
                score = weight * relevance[j] - (1 - weight) * redundancy
                if score > best_score:
                    best, best_score = j, score
            picked.append(best)
        return [{**self.chunks[ids[j]], "score": round(relevance[j], 4)} for j in picked]

    def search(self, query: str, steps: dict | None = None) -> list[dict]:
        steps = steps if steps is not None else {}
        start = time.perf_counter()
        r = self.cfg["retrieval"]
        units = self._mmr(query, r["k"], steps) if r.get("mmr") else self.search_n(query, r["k"], steps)
        steps.setdefault("search_seconds", []).append(round(time.perf_counter() - start, 3))
        return units


KEEP_TAGS = ("NNG", "NNP", "VV", "VA", "XR", "SL", "SN")  # content morphemes; particles and endings are dropped
_KIWI = None
_KIWI_LOCK = threading.Lock()


def kiwi_tokens(text: str) -> list[str]:
    """Content morphemes of a Korean text (Kiwi): common/proper nouns, verb/adjective stems, roots, foreign
    words, numbers. Latin words are lower-cased."""
    global _KIWI
    with _KIWI_LOCK:
        if _KIWI is None:
            from kiwipiepy import Kiwi
            _KIWI = Kiwi()
        tokens = _KIWI.tokenize(text)
    return [t.form.lower() for t in tokens if t.tag in KEEP_TAGS]


@register("bm25")
class BM25Retriever:
    """BM25 (Okapi, rank_bm25 defaults) over Kiwi tokens of the chunks of the scope's index. It reads the same
    chunks.jsonl as the vector retriever, so it needs the index of the config's chunking/embedding but makes
    no embedding calls."""

    def __init__(self, cfg: dict, scope: str):
        if cfg["retrieval"].get("mmr"):
            raise NotImplementedError("retrieval.mmr is implemented for method 'vector' only")
        if cfg["retrieval"].get("bm25_tokenizer", "kiwi") != "kiwi":
            raise KeyError(f"unknown retrieval.bm25_tokenizer {cfg['retrieval']['bm25_tokenizer']!r}")
        self.cfg = cfg
        _, self.chunks = _load_chunks(cfg, scope)
        self.ids = list(self.chunks)
        self.bm25 = BM25Okapi([kiwi_tokens(self.chunks[i]["content"]) or ["_"] for i in self.ids])

    def search_n(self, query: str, n: int, steps: dict | None = None) -> list[dict]:
        scores = self.bm25.get_scores(kiwi_tokens(query))
        order = sorted(range(len(self.ids)), key=lambda i: (-scores[i], i))[:n]  # ties: earlier chunk first
        return [{**self.chunks[self.ids[i]], "score": round(float(scores[i]), 4)} for i in order]

    def search(self, query: str, steps: dict | None = None) -> list[dict]:
        steps = steps if steps is not None else {}
        start = time.perf_counter()
        units = self.search_n(query, self.cfg["retrieval"]["k"])
        steps.setdefault("search_seconds", []).append(round(time.perf_counter() - start, 3))
        return units


def min_max(units: list[dict]) -> dict[str, float]:
    """chunk_id -> score scaled to [0, 1] within one ranked list (1.0 for all if the scores are equal)."""
    if not units:
        return {}
    low, high = min(u["score"] for u in units), max(u["score"] for u in units)
    return {u["chunk_id"]: (u["score"] - low) / (high - low) if high > low else 1.0 for u in units}


@register("hybrid")
class HybridRetriever:
    """Weighted score fusion: alpha * vector + (1 - alpha) * BM25, each min-max scaled within its own list of
    candidates (retrieval.hybrid_alpha); a chunk missing from one list scores 0 there. Each list holds the
    top max(4k, 20) chunks."""

    def __init__(self, cfg: dict, scope: str):
        if cfg["retrieval"].get("mmr"):
            raise NotImplementedError("retrieval.mmr is implemented for method 'vector' only")
        self.cfg = cfg
        self.vector, self.bm25 = VectorRetriever(cfg, scope), BM25Retriever(cfg, scope)

    def search(self, query: str, steps: dict | None = None) -> list[dict]:
        steps = steps if steps is not None else {}
        start = time.perf_counter()
        r = self.cfg["retrieval"]
        n = max(4 * r["k"], 20)
        from_vector, from_bm25 = self.vector.search_n(query, n, steps), self.bm25.search_n(query, n)
        scaled_v, scaled_b = min_max(from_vector), min_max(from_bm25)
        units = {u["chunk_id"]: u for u in from_vector + from_bm25}
        fused = {cid: r["hybrid_alpha"] * scaled_v.get(cid, 0.0) + (1 - r["hybrid_alpha"]) * scaled_b.get(cid, 0.0)
                 for cid in units}
        best = sorted(fused, key=lambda cid: (-fused[cid], -scaled_v.get(cid, 0.0), cid))[:r["k"]]
        result = [{**units[cid], "score": round(fused[cid], 4)} for cid in best]
        steps.setdefault("search_seconds", []).append(round(time.perf_counter() - start, 3))
        return result
