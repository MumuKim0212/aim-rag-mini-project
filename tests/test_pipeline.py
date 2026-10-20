"""Baseline pipeline pieces with fake embeddings and a fake LLM (no network): extraction, chunking,
index build + vector search, and the RAG answer step."""

import hashlib
import json

import pymupdf
import pytest

from rag import chunking, llm, rag, retrieval
from rag.config import BASELINE, load_config
from rag.ingest import extract_pages, in_scope, indexable


@pytest.fixture
def cfg():
    return load_config(BASELINE)


def fake_vector(text: str) -> list[float]:
    """Deterministic 8-d vector from character trigrams, so similar texts get similar vectors."""
    v = [0.0] * 8
    for i in range(len(text) - 2):
        v[int(hashlib.md5(text[i:i + 3].encode()).hexdigest(), 16) % 8] += 1.0
    return v


@pytest.fixture
def fake_llm(monkeypatch):
    monkeypatch.setattr(llm, "count_tokens", lambda texts, model, retries=2: sum(len(t) for t in texts) // 2)

    def embed(texts, *, embedding_cfg, purpose, steps, node, tokens, estimated=False, retries=2):
        llm.record_call(steps, node=node, model=embedding_cfg["model"], kind="embedding", input_tokens=tokens,
                        estimated=estimated)
        return [fake_vector(t) for t in texts]

    monkeypatch.setattr(llm, "embed", embed)


def test_extract_pages_and_scope(tmp_path, cfg):
    (tmp_path / "standard_terms").mkdir()
    for rel, texts in {"financial_glossary_readable.pdf": ["term one definition", "source list"],
                       "standard_terms/01_a.pdf": ["Article 1 applies"], "additional/x.pdf": ["other doc"]}.items():
        (tmp_path / rel).parent.mkdir(exist_ok=True)
        doc = pymupdf.open()
        for text in texts:
            doc.new_page().insert_text((72, 72), text)
        doc.save(tmp_path / rel)
    pages = extract_pages(tmp_path, tmp_path / "pages.jsonl")
    assert [(p["path"], p["page"]) for p in pages] == [
        ("additional/x.pdf", 1), ("financial_glossary_readable.pdf", 1), ("financial_glossary_readable.pdf", 2),
        ("standard_terms/01_a.pdf", 1)]
    assert pages[1]["text"].strip() == "term one definition" and pages[1]["file"] == "financial_glossary_readable.pdf"
    assert [p["path"] for p in pages if in_scope(p, cfg, "A")] == [
        "financial_glossary_readable.pdf", "financial_glossary_readable.pdf", "standard_terms/01_a.pdf"]
    assert all(in_scope(p, cfg, "B") for p in pages)
    glossary_20 = {"file": "financial_glossary_readable.pdf", "page": 20}
    assert not indexable(glossary_20, cfg) and indexable({**glossary_20, "page": 19}, cfg)


def test_recursive_chunks_stay_on_their_page(cfg):
    cfg["chunking"].update(chunk_size=50, chunk_overlap=10)
    pages = [{"file": "a.pdf", "page": 1, "text": "가나다라마바사 " * 20}, {"file": "a.pdf", "page": 2, "text": "짧은 쪽"}]
    chunks = chunking.chunk_pages(pages, cfg)
    assert len(chunks) > 2 and all(len(c["content"]) <= 50 for c in chunks)
    assert chunks[-1] == {"chunk_id": f"{chunking.doc_id('a.pdf')}-p002-00", "source": "a.pdf", "page": 2,
                          "content": "짧은 쪽", "pages": [2]}
    cfg["chunking"]["add_header"] = True
    with pytest.raises(NotImplementedError):
        chunking.chunk_pages(pages, cfg)


def test_build_index_and_search(tmp_path, monkeypatch, cfg, fake_llm):
    monkeypatch.setattr(retrieval, "INDEX_ROOT", tmp_path / "index")
    cfg["retrieval"]["k"] = 2
    cfg["embedding"]["text_format"] = "none"  # fake vectors: prefixes would dominate the trigram counts
    chunks = [{"chunk_id": f"c{i}", "source": "a.pdf", "page": i, "content": text, "pages": [i]}
              for i, text in enumerate(["휴면성 증권계좌는 6개월 이상 매매가 없는 계좌", "신용거래의 철회기간은 14일",
                                        "연금저축 승계는 배우자만 가능"], 1)]
    info = retrieval.build_index(chunks, cfg, "A")
    assert info["n_chunks"] == 3 and info["tokens"] > 0 and info["calls"][0]["kind"] == "embedding"
    with pytest.raises(FileExistsError):
        retrieval.build_index(chunks, cfg, "A")
    steps = {}
    units = retrieval.load_retriever(cfg, "A").search("휴면성 증권계좌는 어떤 계좌", steps)
    assert len(units) == 2 and units[0]["chunk_id"] == "c1" and units[0]["content"] == chunks[0]["content"]
    assert steps["calls"][0]["node"] == "query_embed" and steps["calls"][0]["estimated"] is True
    with pytest.raises(FileNotFoundError):
        retrieval.load_retriever(cfg, "B")


def test_prompt_and_answer_step(cfg, monkeypatch):
    prompt = rag.load_prompt(cfg["answer"]["prompt"])
    assert "{question}" in prompt["user"] and "{context}" in prompt["user"] and "status" in prompt["system"]
    units = [{"chunk_id": "c1", "source": "a.pdf", "page": 3, "content": "휴면성 증권계좌 정의"},
             {"chunk_id": "c2", "source": "b.pdf", "page": 1, "content": "다른 내용"}]
    assert rag.render_context(units).startswith("[1] (a.pdf, p.3)\n휴면성")
    citations, invalid = rag.map_citations([1, 1, 5], units)
    assert citations == [{"chunk_id": "c1", "source": "a.pdf", "page": 3}] and invalid == [5]
    assert rag.format_answer("답", citations).endswith("출처:\n- a.pdf p.3")
    seen = {}

    def generate_json(**kw):
        seen.update(kw)
        llm.record_call(kw["steps"], node=kw["node"], model=kw["model"], input_tokens=100, output_tokens=20)
        return rag.AnswerOut(status="answered", answer="6개월 이상 [1]", citations=[1, 9])

    class FakeRetriever:
        def search(self, query, steps=None):
            llm.record_call(steps, node="query_embed", model=cfg["embedding"]["model"], kind="embedding", input_tokens=5)
            return units

    monkeypatch.setattr(llm, "generate_json", generate_json)
    monkeypatch.setattr(rag, "load_retriever", lambda c, scope: FakeRetriever())
    result = rag.BaselineRAG(cfg).run("휴면성 증권계좌는?", "A")
    assert seen["model"] == "gemini-3.5-flash-lite" and seen["thinking_level"] == "low"
    assert "[1] (a.pdf, p.3)" in seen["user"] and "휴면성 증권계좌는?" in seen["user"]
    assert result["status"] == "answered" and result["citations"] == citations
    assert result["steps"]["invalid_citations"] == [9] and result["n_llm_calls"] == 1
    assert [c["kind"] for c in result["steps"]["calls"]] == ["embedding", "llm"]
    assert result["answer"].endswith("- a.pdf p.3") and result["searches"][0]["chunk_ids"] == ["c1", "c2"]
    json.dumps(result, ensure_ascii=False)  # must be storable in the run log


def test_embed_rejects_merged_batch(monkeypatch):
    """gemini-embedding-2 merges a list[str] into one vector; embed must send Content objects and check counts."""
    sent = {}

    class Models:
        def embed_content(self, model, contents, config):
            sent["contents"] = contents
            return type("R", (), {"embeddings": [type("E", (), {"values": [0.1]})()]})()

    monkeypatch.setattr(llm, "client", lambda timeout_s=None: type("C", (), {"models": Models()})())
    emb = {"model": "gemini-embedding-2", "dimensions": 8, "task_type": None}
    with pytest.raises(ValueError, match="1 vectors for 2 texts"):
        llm.embed(["a", "b"], embedding_cfg=emb, purpose="document", steps={}, node="index", tokens=2)
    assert [c.parts[0].text for c in sent["contents"]] == ["a", "b"]


def test_embedding_text_format(cfg):
    from rag.ingest import title_of
    chunk = {"source": "01_매매거래계좌설정약관.pdf", "content": "제1조"}
    assert title_of("01_매매거래계좌설정약관.pdf", cfg) == "매매거래계좌설정약관"
    assert title_of("financial_glossary_readable.pdf", cfg) == "금융용어 모음"
    assert retrieval.document_text(chunk, cfg) == "title: 매매거래계좌설정약관 | text: 제1조"
    assert retrieval.query_text("휴면성?", cfg) == "task: question answering | query: 휴면성?"
    cfg["embedding"]["text_format"] = "none"
    assert retrieval.document_text(chunk, cfg) == "제1조" and retrieval.query_text("q", cfg) == "q"
