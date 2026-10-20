"""The interface every system implements, and the factory scripts use (config `system`).

A system answers one question within one index scope and returns a result dict whose keys are
evalkit.runlog COLUMNS. scripts/run.py adds system, config, question, and latency_s.

    {
      "status": "answered | abstained | clarify | refused",   # prompts/answer_v1.md
      "answer": "...",                                          # final text incl. source list
      "searches": [{"query": "...", "chunk_ids": [...], "seconds": 0.4}],
      "context": [unit, ...],          # exactly what the answer step received (evalkit unit)
      "citations": [{"chunk_id", "source", "page"}],
      "steps": {"calls": [...], ...},  # llm.record_call; agents add decisions, "first_context", etc.
      "n_searches": 1, "n_llm_calls": 1,
    }

retrieve() is the search alone, used for LLM-free comparisons (run.py --retrieval-only).
"""

from typing import Protocol


class System(Protocol):
    def retrieve(self, question: str, scope: str) -> list[dict]: ...

    def run(self, question: str, scope: str) -> dict: ...


def build_system(cfg: dict) -> System:
    name = cfg["system"]
    if name == "rag":
        from .rag import BaselineRAG
        return BaselineRAG(cfg)
    if name == "agent":
        from .agent import Agent
        return Agent(cfg)
    raise KeyError(f"unknown system {name!r}")
