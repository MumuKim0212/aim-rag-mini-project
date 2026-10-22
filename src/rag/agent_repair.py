"""Context-repair agent (card 015): the T3 agent (rag.agent.Agent) with its grade node replaced by a diagnose node
that says why evidence is missing, and two repair nodes. rag.agent is not changed; config `system: agent_repair`.

    classify -> retrieve -> diagnose ─answer (sufficient, or re-search budget used)→ generate -> cite_check -> END
                              ├─cut→ expand_context -> diagnose      (re-check on the repaired context)
                              ├─not_found→ rewrite -> retrieve
                              └─garbled→ flag_page -> generate

- diagnose (prompts/agent_diagnose_v1.md): sufficient + cause cut | not_found | garbled + relevant result numbers
- expand_context (code): relevant chunks -> their whole page from corpus/pages.jsonl (agent.max_expand rounds,
  agent.max_expand_pages pages per round, total context <= agent.max_context_chars); a page unit's chunk_id is
  "<first chunk_id>#page" so citations still map to file and page
- flag_page (code): pages of the relevant results go to steps["repair_queue"] for offline re-extraction and
  re-chunking (a new card), never inside the graph: re-chunking changes the index mid-experiment

Instrumentation on top of rag.agent: steps["expanded_pages"], steps["repair_queue"], and decisions entries for
diagnose / expand_context / flag_page.

    python scripts/show_graph.py --config configs/015-context-repair.yaml
"""

from typing import Literal

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from . import ROOT
from .agent import SKIP_GRADE, Agent, State
from .ingest import load_pages
from .rag import render_context

DIAGNOSE_PROMPT = "prompts/agent_diagnose_v1.md"
PAGE_MARK = "#page"


class DiagnoseOut(BaseModel):
    sufficient: bool
    cause: Literal["none", "cut", "not_found", "garbled"]
    relevant: list[int]
    missing: str


class RepairState(State, total=False):
    cause: str
    relevant: list
    expand: int
    expanded: list


def render(units: list[dict]) -> str:
    """The answer step's rendering, with expanded pages marked so diagnose knows they are whole pages."""
    text = render_context(units)
    for i, u in enumerate(units, 1):
        if u["chunk_id"].endswith(PAGE_MARK):
            head = f"[{i}] ({u['source']}, p.{u['page']})"
            text = text.replace(head + "\n", head + " (페이지 전체)\n", 1)
    return text


class RepairAgent(Agent):
    def __init__(self, cfg: dict):
        self._pages = None
        super().__init__(cfg)

    def pages(self) -> dict:
        if self._pages is None:
            self._pages = {(p["file"], p["page"]): p["text"]
                           for p in load_pages(ROOT / self.cfg["corpus"]["pages"])}
        return self._pages

    def _build(self):
        g = StateGraph(RepairState)
        for name in ("classify", "retrieve", "diagnose", "expand_context", "flag_page", "rewrite", "generate",
                     "cite_check"):
            g.add_node(name, getattr(self, "_" + name))
        g.add_edge(START, "classify")
        g.add_edge("classify", "retrieve")
        g.add_edge("retrieve", "diagnose")
        g.add_conditional_edges("diagnose", self._after_diagnose,
                                {"answer": "generate", "cut": "expand_context",
                                 "not_found": "rewrite", "garbled": "flag_page"})
        g.add_edge("expand_context", "diagnose")
        g.add_edge("flag_page", "generate")
        g.add_edge("rewrite", "retrieve")
        g.add_edge("generate", "cite_check")
        g.add_conditional_edges("cite_check", self._after_cite, {"generate": "generate", "end": END})
        return g.compile()

    # ---- nodes
    def _classify(self, s: RepairState) -> dict:
        return {**super()._classify(s), "cause": "", "relevant": [], "expand": 0, "expanded": []}

    def _retrieve(self, s: RepairState) -> dict:
        out = super()._retrieve(s)
        whole = set(map(tuple, s["expanded"]))  # a re-search must not bring back chunks of a page shown whole
        out["units"] = [u for u in out["units"]
                        if u["chunk_id"].endswith(PAGE_MARK) or (u["source"], u["page"]) not in whole]
        return out

    def _diagnose(self, s: RepairState) -> dict:
        if s["qtype"] in SKIP_GRADE:
            s["steps"]["decisions"].append({"node": "diagnose", "skipped": s["qtype"]})
            return {"sufficient": True, "missing": "", "cause": "none", "relevant": []}
        out = self._call("diagnose", DIAGNOSE_PROMPT, DiagnoseOut, s["steps"], question=s["question"],
                         context=render(s["units"]) or "(없음)")
        relevant = [n for n in dict.fromkeys(out.relevant) if 1 <= n <= len(s["units"])]
        cause = "none" if out.sufficient else out.cause
        s["steps"]["decisions"].append({"node": "diagnose", "sufficient": out.sufficient, "cause": cause,
                                        "relevant": relevant, "missing": out.missing, "research": s["research"],
                                        "expand": s["expand"]})
        return {"sufficient": out.sufficient, "missing": out.missing, "cause": cause, "relevant": relevant}

    def _expandable(self, s: RepairState) -> list[tuple[str, int]]:
        done = set(map(tuple, s["expanded"]))
        pages = [(s["units"][n - 1]["source"], s["units"][n - 1]["page"]) for n in s["relevant"]
                 if not s["units"][n - 1]["chunk_id"].endswith(PAGE_MARK)]
        return [p for p in dict.fromkeys(pages) if p not in done and p in self.pages()]

    def _after_diagnose(self, s: RepairState) -> str:
        a = self.cfg["agent"]
        if s["sufficient"]:
            return "answer"
        if s["cause"] == "cut" and s["expand"] < a.get("max_expand", 1) and self._expandable(s):
            return "cut"
        if s["cause"] == "garbled" and s["relevant"]:
            return "garbled"
        return "not_found" if s["research"] < a["max_research"] else "answer"  # re-search budget used

    def _with_page(self, units: list[dict], key: tuple[str, int]) -> list[dict]:
        """The first chunk of page `key` becomes the whole page; the page's other chunks are dropped."""
        out, placed = [], False
        for u in units:
            if (u["source"], u["page"]) != key:
                out.append(u)
            elif not placed:
                out.append({**u, "chunk_id": u["chunk_id"] + PAGE_MARK, "content": self.pages()[key],
                            "pages": [u["page"]]})
                placed = True
        return out

    def _expand_context(self, s: RepairState) -> dict:
        a = self.cfg["agent"]
        units, expanded = s["units"], []
        for key in self._expandable(s)[:a.get("max_expand_pages", 3)]:
            trial = self._with_page(units, key)
            if sum(len(u["content"]) for u in trial) <= a.get("max_context_chars", 20000):
                units, expanded = trial, expanded + [list(key)]
        s["steps"].setdefault("expanded_pages", []).extend(expanded)
        s["steps"]["decisions"].append({"node": "expand_context", "pages": expanded,
                                        "chars": sum(len(u["content"]) for u in units)})
        return {"units": units, "expand": s["expand"] + 1, "expanded": s["expanded"] + expanded}

    def _flag_page(self, s: RepairState) -> dict:
        pages = list(dict.fromkeys((s["units"][n - 1]["source"], s["units"][n - 1]["page"]) for n in s["relevant"]))
        s["steps"].setdefault("repair_queue", []).extend({"file": f, "page": p, "reason": s["missing"]}
                                                         for f, p in pages)
        s["steps"]["decisions"].append({"node": "flag_page", "pages": [list(p) for p in pages]})
        return {}
