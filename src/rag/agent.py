"""LangGraph agent (submission/AGENT_GRAPH.md): classify -> retrieve -> grade -> (rewrite -> retrieve)* ->
generate -> cite_check (-> generate once more). The generate node is the baseline's answer step
(rag.generate_answer / map_citations / format_answer with prompts/answer_v1.md) and retrieve is the
baseline's search (BaselineRAG.retrieve), so the first search equals the baseline's for the same question.

Differences from the draft in AGENT_GRAPH.md §2 (reasons in §6 there): there are no separate refuse /
clarify / abstain nodes; every question is retrieved and the shared answer step chooses the status.

Instrumentation (AGENT_GRAPH.md §5): steps["first_context"] = units of the first search,
steps["decisions"] = one entry per node decision, steps["cited_only_from_research"] = whether a citation
points at a chunk the first search did not return; every LLM call is recorded by llm.generate_json.
"""

import time
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from . import llm
from .prompts import fill, load_prompt
from .rag import BaselineRAG, format_answer, generate_answer, map_citations, render_context

CLASSIFY_PROMPT = "prompts/agent_classify_v1.md"
GRADE_PROMPT = "prompts/agent_grade_v1.md"
REWRITE_PROMPT = "prompts/agent_rewrite_v1.md"
SKIP_GRADE = ("needs_info", "inappropriate")  # the answer step handles these without more evidence
DEFAULT_MAX_CONTEXT = 10                       # chunks passed to the answer step after re-search


class ClassifyOut(BaseModel):
    type: Literal["document", "needs_info", "inappropriate", "injection"]
    reason: str


class GradeOut(BaseModel):
    sufficient: bool
    missing: str


class RewriteOut(BaseModel):
    query: str


class State(TypedDict, total=False):
    question: str
    scope: str
    steps: dict
    qtype: str
    query: str
    queries: list
    searches: list
    units: list
    sufficient: bool
    missing: str
    research: int
    cite_retry: int
    out: object
    citations: list
    invalid: list


class Agent(BaselineRAG):
    def __init__(self, cfg: dict):
        super().__init__(cfg)
        self.graph = self._build()

    def _call(self, node: str, prompt_path: str, schema, steps: dict, **values):
        prompt = load_prompt(prompt_path)
        model = (self.cfg["agent"].get("node_models") or {}).get(node) or self.cfg["answer"]["model"]
        a = self.cfg["answer"]
        return llm.generate_json(model=model, system=prompt["system"], user=fill(prompt["user"], **values),
                                 schema=schema, temperature=a.get("temperature"),
                                 thinking_level=a.get("thinking_level"), steps=steps, node=node,
                                 retries=self.cfg["run"]["max_retries"], timeout_s=self.cfg["run"]["timeout_s"])

    def _build(self):
        g = StateGraph(State)
        for name in ("classify", "retrieve", "grade", "rewrite", "generate", "cite_check"):
            g.add_node(name, getattr(self, "_" + name))
        g.add_edge(START, "classify")
        g.add_edge("classify", "retrieve")
        g.add_edge("retrieve", "grade")
        g.add_conditional_edges("grade", self._after_grade, {"rewrite": "rewrite", "generate": "generate"})
        g.add_edge("rewrite", "retrieve")
        g.add_edge("generate", "cite_check")
        g.add_conditional_edges("cite_check", self._after_cite, {"generate": "generate", "end": END})
        return g.compile()

    # ---- nodes: each returns only the keys it changes; `steps` is mutated in place
    def _classify(self, s: State) -> dict:
        out = self._call("classify", CLASSIFY_PROMPT, ClassifyOut, s["steps"], question=s["question"])
        s["steps"].setdefault("decisions", []).append({"node": "classify", "type": out.type, "reason": out.reason})
        return {"qtype": out.type, "query": s["question"], "queries": [], "searches": [], "units": [],
                "research": 0, "cite_retry": 0}

    def _retrieve(self, s: State) -> dict:
        start = time.perf_counter()
        found = self.retrieve(s["query"], s["scope"], s["steps"])  # includes the rerank step when retrieval.rerank_pool is set
        if not s["searches"]:
            s["steps"]["first_context"] = found
        have = {u["chunk_id"] for u in s["units"]}
        room = self.cfg["agent"].get("max_context", DEFAULT_MAX_CONTEXT) - len(s["units"])
        new = [u for u in found if u["chunk_id"] not in have][:max(room, 0)]
        search = {"query": s["query"], "chunk_ids": [u["chunk_id"] for u in found],
                  "seconds": round(time.perf_counter() - start, 3)}
        return {"units": s["units"] + new, "searches": s["searches"] + [search], "queries": s["queries"] + [s["query"]]}

    def _grade(self, s: State) -> dict:
        if s["qtype"] in SKIP_GRADE:
            s["steps"]["decisions"].append({"node": "grade", "skipped": s["qtype"]})
            return {"sufficient": True, "missing": ""}
        out = self._call("grade", GRADE_PROMPT, GradeOut, s["steps"], question=s["question"],
                         context=render_context(s["units"]) or "(없음)")
        s["steps"]["decisions"].append({"node": "grade", "sufficient": out.sufficient, "missing": out.missing,
                                        "research": s["research"]})
        return {"sufficient": out.sufficient, "missing": out.missing}

    def _after_grade(self, s: State) -> str:
        return "generate" if s["sufficient"] or s["research"] >= self.cfg["agent"]["max_research"] else "rewrite"

    def _rewrite(self, s: State) -> dict:
        out = self._call("rewrite", REWRITE_PROMPT, RewriteOut, s["steps"], question=s["question"],
                         previous="\n".join(s["queries"]), missing=s["missing"])
        s["steps"]["decisions"].append({"node": "rewrite", "query": out.query})
        return {"query": out.query.strip() or s["question"], "research": s["research"] + 1}

    def _generate(self, s: State) -> dict:
        out = generate_answer(s["question"], s["units"], self.cfg, s["steps"])
        citations, invalid = map_citations(out.citations, s["units"])
        return {"out": out, "citations": citations, "invalid": invalid}

    def _cite_check(self, s: State) -> dict:
        ok = not s["invalid"] and (s["out"].status != "answered" or bool(s["citations"]))
        s["steps"]["decisions"].append({"node": "cite_check", "ok": ok, "retry": s["cite_retry"]})
        return {"cite_retry": s["cite_retry"] + (0 if ok else 1)}

    def _after_cite(self, s: State) -> str:
        decision = s["steps"]["decisions"][-1]
        return "end" if decision["ok"] or decision["retry"] >= self.cfg["agent"]["max_cite_retry"] else "generate"

    def run(self, question: str, scope: str) -> dict:
        steps = {"calls": []}
        s = self.graph.invoke({"question": question, "scope": scope, "steps": steps})
        if s["invalid"]:
            steps["invalid_citations"] = s["invalid"]
        first = {u["chunk_id"] for u in steps["first_context"]}
        steps["cited_only_from_research"] = bool(s["citations"]) and all(c["chunk_id"] not in first for c in s["citations"])
        steps["cited_research_chunk"] = any(c["chunk_id"] not in first for c in s["citations"])
        return {"status": s["out"].status, "answer": format_answer(s["out"].answer, s["citations"]),
                "searches": s["searches"], "context": s["units"], "citations": s["citations"], "steps": steps,
                "n_searches": len(s["searches"]), "n_llm_calls": sum(1 for c in steps["calls"] if c["kind"] == "llm")}
