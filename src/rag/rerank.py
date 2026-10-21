"""LLM rerank (card 013): choose the k chunks that answer the question from a larger pool (retrieval.rerank_pool).
One call with prompts/rerank_v1.md. Invalid or duplicate numbers are dropped and the pool order fills the rest, so
a failed call degrades to the plain top-k. steps["rerank"] records the pool, the pick and whether the call failed."""

from pydantic import BaseModel

from . import llm
from .prompts import fill, load_prompt

RERANK_PROMPT = "prompts/rerank_v1.md"


class RerankOut(BaseModel):
    ranked: list[int]


def pick(ranked: list[int], n: int, k: int) -> list[int]:
    """0-based pool indexes: valid unique numbers from `ranked` in order, topped up with the pool order."""
    seen: list[int] = []
    for number in ranked:
        if 1 <= number <= n and number - 1 not in seen:
            seen.append(number - 1)
    seen = seen[:k]
    return seen + [i for i in range(n) if i not in seen][:k - len(seen)]


def rerank(question: str, pool: list[dict], k: int, model: str, cfg: dict, steps: dict) -> list[dict]:
    prompt = load_prompt(RERANK_PROMPT)
    context = "\n\n".join(f"[{i}] ({u['source']}, p.{u['page']})\n{u['content']}" for i, u in enumerate(pool, 1))
    ranked, failed = [], False
    try:
        a = cfg["answer"]
        ranked = llm.generate_json(model=model, system=fill(prompt["system"], k=str(k)),
                                   user=fill(prompt["user"], question=question, context=context, k=str(k)),
                                   schema=RerankOut, temperature=a.get("temperature"), thinking_level=a.get("thinking_level"),
                                   steps=steps, node="rerank", retries=cfg["run"]["max_retries"],
                                   timeout_s=cfg["run"]["timeout_s"]).ranked
    except Exception as e:  # a rerank failure must not lose the question: fall back to the pool order
        failed = True
        steps["rerank_error"] = repr(e)[:200]
    idx = pick(ranked, len(pool), k)
    steps["rerank"] = {"pool": [u["chunk_id"] for u in pool], "picked": [pool[i]["chunk_id"] for i in idx],
                       "failed": failed}
    return [pool[i] for i in idx]
