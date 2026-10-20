"""Baseline RAG (PLAN §3.1): one search, one answer call with prompts/answer_v1.md.

retrieve: retrieval.load_retriever(cfg, scope).search(question)
run:      retrieve -> render numbered context -> answer model -> parse JSON {status, answer, citations}
          -> map citation numbers to {chunk_id, source, page} in code -> append source list to answer.
Record the answer call with llm.record_call(node="generate"). Return the dict described in systems.py.
"""


class BaselineRAG:
    def __init__(self, cfg: dict):
        self.cfg = cfg

    def retrieve(self, question: str, scope: str) -> list[dict]:
        raise NotImplementedError("baseline RAG — PLAN §3.1")

    def run(self, question: str, scope: str) -> dict:
        raise NotImplementedError("baseline RAG — PLAN §3.1")
