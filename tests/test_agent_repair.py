"""Card 015: the context-repair agent with a fake LLM, fake retriever and fake pages (no network)."""

import json

import pytest

from rag import llm
from rag.agent import ClassifyOut, RewriteOut
from rag.agent_repair import PAGE_MARK, DiagnoseOut, RepairAgent
from rag.config import ROOT, load_config
from rag.rag import AnswerOut


def unit(i, page=1):
    return {"chunk_id": f"c{i}", "source": "a.pdf", "page": page, "pages": [page], "content": f"text {i}", "score": 0.5}


PAGES = {("a.pdf", 1): "page one whole text", ("a.pdf", 2): "page two whole text", ("a.pdf", 3): "x" * 30000}


class Script:
    def __init__(self, diagnoses, answers=None, classify="document"):
        self.diagnoses, self.classify = list(diagnoses), classify
        self.answers = list(answers or [AnswerOut(status="answered", answer="답 [1]", citations=[1])])
        self.nodes, self.users = [], []

    def __call__(self, *, model, system, user, schema, temperature, thinking_level, steps, node, retries=2, timeout_s=None):
        self.nodes.append(node)
        self.users.append(user)
        llm.record_call(steps, node=node, model=model, input_tokens=10, output_tokens=5)
        if schema is ClassifyOut:
            return ClassifyOut(type=self.classify, reason="r")
        if schema is DiagnoseOut:
            return self.diagnoses.pop(0)
        if schema is RewriteOut:
            return RewriteOut(query=f"새 검색어 {self.nodes.count('rewrite')}")
        return self.answers.pop(0)


def d(sufficient=False, cause="none", relevant=(), missing=""):
    return DiagnoseOut(sufficient=sufficient, cause=cause, relevant=list(relevant), missing=missing)


@pytest.fixture
def cfg():
    c = load_config(ROOT / "configs" / "015-context-repair.yaml")
    c["retrieval"]["rerank_pool"] = None  # the LLM rerank inside retrieve is card 013's; the graph is tested alone
    return c


def make(cfg, monkeypatch, script, results):
    monkeypatch.setattr(llm, "generate_json", script)
    ag = RepairAgent(cfg)
    ag._pages = PAGES
    searched = []

    class Retriever:
        def search(self, query, steps=None, k=None):
            searched.append(query)
            return results[min(len(searched), len(results)) - 1]

    monkeypatch.setattr(ag, "_retriever", lambda scope: Retriever())
    return ag, searched


def test_graph_has_repair_nodes(cfg, monkeypatch):
    ag, _ = make(cfg, monkeypatch, Script([]), [[unit(1)]])
    assert {"diagnose", "expand_context", "flag_page", "rewrite"} <= set(ag.graph.get_graph().nodes)
    assert "grade" not in ag.graph.get_graph().nodes


def test_sufficient_answers_without_repair(cfg, monkeypatch):
    script = Script([d(True)])
    ag, searched = make(cfg, monkeypatch, script, [[unit(1), unit(2)]])
    result = ag.run("질문", "A")
    assert script.nodes == ["classify", "diagnose", "generate"] and searched == ["질문"]
    assert "expanded_pages" not in result["steps"] and result["status"] == "answered"
    json.dumps(result, ensure_ascii=False)


def test_cut_expands_page_once_then_rechecks(cfg, monkeypatch):
    script = Script([d(cause="cut", relevant=[1, 9]), d(cause="cut", relevant=[1]), d(True)])
    ag, searched = make(cfg, monkeypatch, script, [[unit(1, 1), unit(2, 1), unit(3, 2)], [unit(4, 2)]])
    result = ag.run("질문", "A")
    # page 1: c1 becomes the whole page, c2 (same page) is dropped; the re-check is the second diagnose
    assert result["steps"]["expanded_pages"] == [["a.pdf", 1]]
    assert script.nodes[:3] == ["classify", "diagnose", "diagnose"]
    assert "[1] (a.pdf, p.1) (페이지 전체)" in script.users[2]
    # max_expand 1: the second "cut" falls back to re-search
    assert searched == ["질문", "새 검색어 1"]
    ids = [u["chunk_id"] for u in result["context"]]
    assert ids == ["c1" + PAGE_MARK, "c3", "c4"]
    assert result["context"][0]["content"] == "page one whole text"
    assert result["citations"] == [{"chunk_id": "c1" + PAGE_MARK, "source": "a.pdf", "page": 1}]


def test_expansion_respects_char_cap(cfg, monkeypatch):
    script = Script([d(cause="cut", relevant=[1]), d(True)])
    ag, _ = make(cfg, monkeypatch, script, [[unit(1, 3), unit(2, 1)]])
    result = ag.run("질문", "A")
    assert result["steps"]["expanded_pages"] == [] and result["context"][0]["chunk_id"] == "c1"


def test_garbled_flags_page_and_answers(cfg, monkeypatch):
    script = Script([d(cause="garbled", relevant=[2], missing="표가 깨짐")])
    ag, searched = make(cfg, monkeypatch, script, [[unit(1, 1), unit(2, 2)]])
    result = ag.run("질문", "A")
    assert result["steps"]["repair_queue"] == [{"file": "a.pdf", "page": 2, "reason": "표가 깨짐"}]
    assert script.nodes == ["classify", "diagnose", "generate"] and searched == ["질문"]


def test_not_found_researches_until_budget(cfg, monkeypatch):
    script = Script([d(cause="not_found")] * 3)
    ag, searched = make(cfg, monkeypatch, script, [[unit(1)], [unit(2)], [unit(3)]])
    result = ag.run("질문", "A")
    assert searched == ["질문", "새 검색어 1", "새 검색어 2"] and script.nodes.count("diagnose") == 3
    assert result["steps"]["termination_reason"] == "insufficient_evidence"


def test_research_does_not_bring_back_chunks_of_an_expanded_page(cfg, monkeypatch):
    script = Script([d(cause="cut", relevant=[1]), d(cause="not_found"), d(True)])
    ag, _ = make(cfg, monkeypatch, script, [[unit(1, 1)], [unit(5, 1), unit(6, 2)]])
    result = ag.run("질문", "A")
    assert [u["chunk_id"] for u in result["context"]] == ["c1" + PAGE_MARK, "c6"]


def test_skip_types_do_not_diagnose(cfg, monkeypatch):
    script = Script([], answers=[AnswerOut(status="refused", answer="거절", citations=[])], classify="inappropriate")
    ag, _ = make(cfg, monkeypatch, script, [[unit(1)]])
    assert ag.run("질문", "A")["status"] == "refused" and "diagnose" not in script.nodes
