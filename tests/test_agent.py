"""Card 008: the agent graph with a fake LLM and a fake retriever (no network)."""

import pytest

from rag import agent as agent_mod
from rag import llm
from rag.agent import Agent, ClassifyOut, GradeOut, RewriteOut
from rag.config import BASELINE, load_config
from rag.rag import AnswerOut


def unit(i, page=1):
    return {"chunk_id": f"c{i}", "source": "a.pdf", "page": page, "pages": [page], "content": f"text {i}", "score": 0.5}


class Script:
    """Fake llm.generate_json: answers by schema from queues, records every call like the real one."""

    def __init__(self, classify="document", grades=(True,), answers=None):
        self.classify, self.grades = classify, list(grades)
        self.answers = list(answers or [AnswerOut(status="answered", answer="답 [1]", citations=[1])])
        self.nodes = []

    def __call__(self, *, model, system, user, schema, temperature, thinking_level, steps, node, retries=2, timeout_s=None):
        self.nodes.append(node)
        llm.record_call(steps, node=node, model=model, input_tokens=10, output_tokens=5)
        if schema is ClassifyOut:
            return ClassifyOut(type=self.classify, reason="r")
        if schema is GradeOut:
            return GradeOut(sufficient=self.grades.pop(0), missing="용어 정의")
        if schema is RewriteOut:
            return RewriteOut(query=f"새 검색어 {self.nodes.count('rewrite')}")
        return self.answers.pop(0)


@pytest.fixture
def cfg():
    return load_config(BASELINE)


def make(cfg, monkeypatch, script, results):
    monkeypatch.setattr(llm, "generate_json", script)
    ag = Agent(cfg)
    searched = []

    class Retriever:
        def search(self, query, steps=None):
            searched.append(query)
            return results[len(searched) - 1]

    monkeypatch.setattr(ag, "_retriever", lambda scope: Retriever())
    return ag, searched


def test_sufficient_first_search_is_the_baseline_search(cfg, monkeypatch):
    script = Script()
    ag, searched = make(cfg, monkeypatch, script, [[unit(1), unit(2)]])
    out = ag.run("질문?", "A")
    assert script.nodes == ["classify", "grade", "generate"] and searched == ["질문?"]
    assert out["n_searches"] == 1 and out["n_llm_calls"] == 3 and out["status"] == "answered"
    assert out["steps"]["first_context"] == out["context"] and out["steps"]["cited_research_chunk"] is False


def test_insufficient_researches_twice_then_answers_with_deduplicated_context(cfg, monkeypatch):
    script = Script(grades=(False, False, False), answers=[AnswerOut(status="abstained", answer="없음", citations=[])])
    ag, searched = make(cfg, monkeypatch, script, [[unit(1), unit(2)], [unit(2), unit(3)], [unit(3), unit(4)]])
    out = ag.run("질문?", "A")
    assert script.nodes == ["classify", "grade", "rewrite", "grade", "rewrite", "grade", "generate"]
    assert searched == ["질문?", "새 검색어 1", "새 검색어 2"] and out["n_searches"] == 3
    assert [u["chunk_id"] for u in out["context"]] == ["c1", "c2", "c3", "c4"]  # no duplicates, new ones appended
    assert [u["chunk_id"] for u in out["steps"]["first_context"]] == ["c1", "c2"]


def test_context_is_capped_and_research_chunk_citation_is_flagged(cfg, monkeypatch):
    cfg["agent"]["max_context"] = 3
    script = Script(grades=(False, True), answers=[AnswerOut(status="answered", answer="답 [3]", citations=[3])])
    ag, _ = make(cfg, monkeypatch, script, [[unit(1), unit(2)], [unit(5), unit(6)]])
    out = ag.run("질문?", "A")
    assert [u["chunk_id"] for u in out["context"]] == ["c1", "c2", "c5"]
    assert out["steps"]["cited_research_chunk"] is True and out["steps"]["cited_only_from_research"] is True


@pytest.mark.parametrize("kind", ["needs_info", "inappropriate"])
def test_no_grading_for_questions_the_documents_cannot_settle(cfg, monkeypatch, kind):
    script = Script(classify=kind, answers=[AnswerOut(status="clarify", answer="무엇이 필요합니다", citations=[])])
    ag, searched = make(cfg, monkeypatch, script, [[unit(1)]])
    out = ag.run("질문?", "A")
    assert script.nodes == ["classify", "generate"] and out["status"] == "clarify" and out["n_searches"] == 1


def test_invalid_citation_gets_one_retry_only(cfg, monkeypatch):
    bad = AnswerOut(status="answered", answer="답 [9]", citations=[9])
    script = Script(answers=[bad, bad])
    ag, _ = make(cfg, monkeypatch, script, [[unit(1)]])
    out = ag.run("질문?", "A")
    assert script.nodes.count("generate") == 2 and out["steps"]["invalid_citations"] == [9]
    good = AnswerOut(status="answered", answer="답 [1]", citations=[1])
    script = Script(answers=[bad, good])
    ag, _ = make(cfg, monkeypatch, script, [[unit(1)]])
    out = ag.run("질문?", "A")
    assert script.nodes.count("generate") == 2 and out["citations"][0]["chunk_id"] == "c1" and "invalid_citations" not in out["steps"]
