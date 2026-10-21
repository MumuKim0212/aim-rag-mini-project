"""Baseline RAG (PLAN §3.1): one search, one answer call with the configured answer prompt.

The answer step is shared with the agent's generate node: load_prompt, render_context, generate_answer,
map_citations, and format_answer are the only implementation of "answer from retrieved chunks", so the two
systems differ only in the graph around it (PLAN §3.3). Change them only with a new prompt version or a
new experiment; after the baseline run, any behavior change here invalidates the baseline.
"""

import threading
import time
from typing import Literal

from pydantic import BaseModel

from . import llm
from .prompts import fill, load_prompt
from .rerank import rerank
from .retrieval import load_retriever


class AnswerOut(BaseModel):
    status: Literal["answered", "abstained", "clarify", "refused"]
    answer: str
    citations: list[int]


def page_label(unit: dict) -> str:
    pages = unit.get("pages") or [unit["page"]]
    return f"p.{pages[0]}" if len(pages) == 1 else f"p.{pages[0]}-{pages[-1]}"  # a unit can run over a page break


def render_context(units: list[dict]) -> str:
    return "\n\n".join(f"[{i}] ({u['source']}, {page_label(u)})\n{u['content']}" for i, u in enumerate(units, 1))


def generate_answer(question: str, units: list[dict], cfg: dict, steps: dict, node: str = "generate") -> AnswerOut:
    a = cfg["answer"]
    prompt = load_prompt(a["prompt"])
    user = fill(prompt["user"], question=question, context=render_context(units) or "(없음)")
    return llm.generate_json(model=a["model"], system=prompt["system"], user=user, schema=AnswerOut,
                             temperature=a.get("temperature"), thinking_level=a.get("thinking_level"),
                             steps=steps, node=node, retries=cfg["run"]["max_retries"],
                             timeout_s=cfg["run"]["timeout_s"])


def map_citations(numbers: list[int], units: list[dict]) -> tuple[list[dict], list[int]]:
    """Result numbers -> {chunk_id, source, page}, in order, deduplicated; out-of-range numbers returned."""
    citations, invalid, seen = [], [], set()
    for n in numbers:
        if not 1 <= n <= len(units):
            invalid.append(n)
        elif n not in seen:
            seen.add(n)
            u = units[n - 1]
            citations.append({"chunk_id": u["chunk_id"], "source": u["source"], "page": u["page"],
                              **({"pages": u["pages"]} if len(u.get("pages") or []) > 1 else {})})
    return citations, invalid


def format_answer(answer: str, citations: list[dict]) -> str:
    pages = list(dict.fromkeys((c["source"], p) for c in citations for p in c.get("pages") or [c["page"]]))
    if not pages:
        return answer
    return answer + "\n\n출처:\n" + "\n".join(f"- {source} p.{page}" for source, page in pages)


class BaselineRAG:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self._retrievers: dict = {}
        self._lock = threading.Lock()

    def _retriever(self, scope: str):
        with self._lock:
            if scope not in self._retrievers:
                self._retrievers[scope] = load_retriever(self.cfg, scope)
            return self._retrievers[scope]

    def retrieve(self, question: str, scope: str, steps: dict | None = None) -> list[dict]:
        r = self.cfg["retrieval"]
        if not r.get("rerank_pool"):
            return self._retriever(scope).search(question, steps)
        pool = self._retriever(scope).search(question, steps, k=r["rerank_pool"])
        return rerank(question, pool, r["k"], r.get("rerank_model") or self.cfg["answer"]["model"], self.cfg,
                      steps if steps is not None else {})

    def run(self, question: str, scope: str) -> dict:
        steps = {"calls": []}
        start = time.perf_counter()
        units = self.retrieve(question, scope, steps)
        search = {"query": question, "chunk_ids": [u["chunk_id"] for u in units],
                  "seconds": round(time.perf_counter() - start, 3)}
        out = generate_answer(question, units, self.cfg, steps)
        citations, invalid = map_citations(out.citations, units)
        if invalid:
            steps["invalid_citations"] = invalid
        return {"status": out.status, "answer": format_answer(out.answer, citations), "searches": [search],
                "context": units, "citations": citations, "steps": steps, "n_searches": 1,
                "n_llm_calls": sum(1 for c in steps["calls"] if c["kind"] == "llm")}
