"""Card 002: the `structure` chunker (glossary term, terms article, recursive for the rest)."""

import json
import re
from collections import defaultdict

import pytest

from rag import ROOT, chunking
from rag.config import BASELINE, load_config
from rag.ingest import in_scope, indexable, load_pages
from evalkit.metrics import is_gold, squash

GLOSSARY = chunking.GLOSSARY


def page(file, path, n, text):
    return {"file": file, "path": path, "page": n, "text": text}


@pytest.fixture
def cfg(tmp_path):
    cfg = load_config(BASELINE)
    cfg["chunking"].update(method="structure", max_chars=60)
    cfg["corpus"].update(pages=str(tmp_path / "pages.jsonl"), exclude_pages={GLOSSARY: [3, 3]})
    return cfg


def test_structure_units(cfg, tmp_path):
    terms = "01_a.pdf"
    pages = [
        page(GLOSSARY, GLOSSARY, 1, "1\n금융용어 모음\n가나\n가나 정의 첫 줄\n계속\n다라\n다라 정의"),
        page(GLOSSARY, GLOSSARY, 2, "2\n이어짐\n마바\n마바 정의"),
        page(GLOSSARY, GLOSSARY, 3, "3\n출처 목록\n가나 / 용어 설명 / http://x\n다라 / 용어 설명 / http://x\n마바 / 용어 설명 / http://x"),
        page(terms, f"standard_terms/{terms}", 1, "1\n약관 제목\n버전: 1\n제1조(적용)\n본문 하나\n제2조 (통지)\n① 첫째 항 " + "가" * 30 +
             "\n② 둘째 항 " + "나" * 30),
        page(terms, f"standard_terms/{terms}", 2, "2\n③ 셋째 항 계속\n제1조(적용)에 따라 통지한다\n제2조의2(추가)\n본문"),
        page("x.pdf", "additional/x.pdf", 1, "3 그 밖의 문서\n본문"),
    ]
    (tmp_path / "pages.jsonl").write_text("\n".join(json.dumps(p, ensure_ascii=False) for p in pages), encoding="utf-8")
    chunks = chunking.chunk_pages([p for p in pages if indexable(p, cfg)], cfg)

    glossary = [c for c in chunks if c["source"] == GLOSSARY]
    assert [c["content"].split("\n")[0] for c in glossary] == ["가나", "다라", "마바"]
    assert glossary[1]["pages"] == [1, 2] and glossary[1]["content"].endswith("이어짐")  # runs over the page break
    assert "금융용어 모음" not in glossary[0]["content"]

    art = [c for c in chunks if c["source"] == terms]
    assert art[0]["content"].startswith("약관 제목") and "제1조" not in art[0]["content"]  # preamble kept
    heads = [c["content"].split("\n")[0] for c in art]
    # "제1조(적용)에 따라" on page 2 is a sentence, not a heading (number does not increase); 제2조 is cut
    # before ② because it is over max_chars; 제2조의2 is a heading
    assert heads == ["약관 제목", "제1조(적용)", "제2조 (통지)", "② 둘째 항 " + "나" * 30, "제2조의2(추가)"]
    assert "제1조(적용)에 따라" in art[2]["content"] or "제1조(적용)에 따라" in art[3]["content"]
    assert len({c["chunk_id"] for c in chunks}) == len(chunks)
    assert [c["source"] for c in chunks if c["source"] == "x.pdf"] == ["x.pdf"]  # recursive for the rest


def test_glossary_term_missing_fails_loudly(cfg, tmp_path):
    pages = [page(GLOSSARY, GLOSSARY, 1, "1\n가나\n정의"),
             page(GLOSSARY, GLOSSARY, 3, "3\n가나 / 용어 설명 / u\n없는용어 / 용어 설명 / u")]
    (tmp_path / "pages.jsonl").write_text("\n".join(json.dumps(p, ensure_ascii=False) for p in pages), encoding="utf-8")
    with pytest.raises(ValueError, match="없는용어"):
        chunking.chunk_pages(pages[:1], cfg)


def test_is_gold_counts_every_page_of_a_unit():
    unit = {"source": "a.pdf", "page": 3, "pages": [3, 4]}
    assert is_gold(unit, {("a.pdf", 4)}) and not is_gold(unit, {("a.pdf", 5)})
    assert is_gold({"source": "a.pdf", "page": 3}, {("a.pdf", 3)})  # units without `pages` (agent pages, old runs)


def test_real_corpus_invariants():
    """Every term in the glossary source list and every article in each source list is a chunk start, and
    nothing but page numbers (and the glossary title) is lost."""
    cfg = load_config(ROOT / "configs" / "002-structure.yaml")
    allp = load_pages(ROOT / cfg["corpus"]["pages"])
    chunks = chunking.chunk_pages([p for p in allp if indexable(p, cfg) and in_scope(p, cfg, "A")], cfg)
    by_file = defaultdict(list)
    for c in chunks:
        by_file[c["source"]].append(c)
    assert len([c for c in by_file[GLOSSARY]]) == 228
    for file, group in by_file.items():
        pages = sorted((p for p in allp if p["file"] == file and indexable(p, cfg)), key=lambda p: p["page"])
        body = "".join(re.sub(r"\A\d+\n", "", p["text"]) for p in pages).replace("금융용어 모음", "", file == GLOSSARY)
        assert squash("".join(c["content"] for c in group)) == squash(body), file
        if file[:2].isdigit():
            first, last = cfg["corpus"]["exclude_pages"][file]
            listing = "\n".join(p["text"] for p in allp if p["file"] == file and first <= p["page"] <= last)
            assert len([c for c in group if chunking.ARTICLE.match(c["content"])]) == \
                len(re.findall(r" / 제\s?\d+\s?조", listing)), file


def test_answer_step_shows_every_page_of_a_unit():
    from rag import rag
    from rag.judge import citation_check
    one = {"chunk_id": "c1", "source": "a.pdf", "page": 3, "pages": [3], "content": "x"}
    two = {"chunk_id": "c2", "source": "a.pdf", "page": 3, "pages": [3, 4], "content": "y"}
    assert rag.render_context([one, two]) == "[1] (a.pdf, p.3)\nx\n\n[2] (a.pdf, p.3-4)\ny"
    citations, _ = rag.map_citations([1, 2], [one, two])
    assert "pages" not in citations[0] and citations[1]["pages"] == [3, 4]  # single-page citations unchanged
    assert rag.format_answer("답", citations).endswith("- a.pdf p.3\n- a.pdf p.4")
    item = {"targets": [{"file": "a.pdf", "page": 4}]}
    assert citation_check(item, {"citations": citations[1:], "context": [two]})["on_target"] == 1
    assert citation_check(item, {"citations": citations[:1], "context": [one]})["on_target"] == 0
