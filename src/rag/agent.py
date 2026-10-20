"""LangGraph agent (submission/AGENT_GRAPH.md): classify -> retrieve -> grade -> (rewrite -> retrieve)* ->
generate -> cite_check. The generate node must call rag.generate_answer / map_citations / format_answer
(the baseline's answer step), and retrieve must use retrieval.load_retriever like rag.BaselineRAG.

Instrumentation (decided before building, AGENT_GRAPH.md §5): put the first search's units in
steps["first_context"], node decisions in steps["decisions"], and record every call with llm.record_call.
retrieve() must equal the baseline's first search for the same question.
"""


class Agent:
    def __init__(self, cfg: dict):
        self.cfg = cfg

    def retrieve(self, question: str, scope: str, steps: dict | None = None) -> list[dict]:
        raise NotImplementedError("card 008")

    def run(self, question: str, scope: str) -> dict:
        raise NotImplementedError("card 008")
