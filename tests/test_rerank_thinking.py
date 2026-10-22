"""The rerank call follows answer.thinking_level unless retrieval.rerank_thinking_level is set (card 017)."""

from rag import rerank as rr


def pool(n=3):
    return [{"chunk_id": f"c{i}", "source": "a.pdf", "page": i, "content": f"text {i}"} for i in range(1, n + 1)]


def call(monkeypatch, retrieval, answer_level="high"):
    seen = {}

    class Out:
        ranked = [2, 1]

    def fake(**kw):
        seen.update(kw)
        return Out()

    monkeypatch.setattr(rr.llm, "generate_json", fake)
    cfg = {"answer": {"temperature": 0, "thinking_level": answer_level}, "retrieval": retrieval,
           "run": {"max_retries": 0, "timeout_s": 5}}
    steps = {}
    picked = rr.rerank("q?", pool(), 2, "m-rerank", cfg, steps)
    return seen, steps, picked


def test_rerank_follows_the_answer_thinking_by_default(monkeypatch):
    seen, _, _ = call(monkeypatch, {"rerank_pool": 3})
    assert seen["thinking_level"] == "high" and seen["model"] == "m-rerank"


def test_rerank_thinking_is_fixed_by_its_own_setting(monkeypatch):
    seen, steps, picked = call(monkeypatch, {"rerank_pool": 3, "rerank_thinking_level": "low"})
    assert seen["thinking_level"] == "low"
    assert [u["chunk_id"] for u in picked] == ["c2", "c1"] and steps["rerank"]["failed"] is False
