"""VLM page supplement with a fake VLM (no network): selection, append-only text, SKIP, fallback, cache."""

import pymupdf
import pytest

from evalkit.metrics import squash
from rag import llm
from rag.ingest import extract_pages, supplement_visuals
from rag.prompts import load_prompt

XCFG = {"paths": ["additional/*.pdf"], "model": "gemini-3.8-flash", "prompt": "prompts/vlm_page_v1.md",
        "thinking_level": "low", "dpi": 50, "concurrency": 2, "separator": "[표·그림 정리]"}


@pytest.fixture
def pdfs(tmp_path):
    (tmp_path / "additional").mkdir()
    doc = pymupdf.open()
    for text in ["chart page", "logo page", "blocked page"]:
        doc.new_page().insert_text((72, 72), text)
    doc.save(tmp_path / "additional" / "x.pdf")
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Article 1")
    doc.save(tmp_path / "terms.pdf")
    return tmp_path


@pytest.fixture
def fake_vlm(monkeypatch):
    seen = []

    def describe_image(*, model, system, user, png, thinking_level, steps, node, retries=2, timeout_s=None):
        assert png[:4] == b"\x89PNG" and "규칙" in system
        seen.append(user)
        llm.record_call(steps, node=node, model=model, input_tokens=1000, output_tokens=50)
        if "logo page" in user:
            return "SKIP", "STOP"
        if "blocked page" in user:
            return ("[그림] 요약 수치 10%", "STOP") if "그대로 옮기지 말고" in user else ("", "RECITATION")
        return "| 연도 | 값 |\n|---|---|\n| 2025 | 10 |", "STOP"

    monkeypatch.setattr(llm, "describe_image", describe_image)
    return seen


def test_prompt_has_all_sections():
    prompt = load_prompt(XCFG["prompt"], required=("system", "user", "fallback"))
    assert "{text_layer}" in prompt["user"] and "{text_layer}" in prompt["fallback"]


def test_supplement_appends_and_caches(pdfs, tmp_path, fake_vlm):
    pages = extract_pages(pdfs, tmp_path / "pages.jsonl")
    out, results = supplement_visuals(pages, pdfs, XCFG, tmp_path / "cache")
    assert len(results) == 3 and len(fake_vlm) == 4                      # terms.pdf not sent; one fallback retry
    by = {(p["path"], p["page"]): p for p in out}
    chart, logo, blocked = (by[("additional/x.pdf", n)] for n in (1, 2, 3))
    assert chart["visual_mode"] == "added" and chart["text"].startswith(chart["text_layer"].rstrip())
    assert "[표·그림 정리]\n| 연도 | 값 |" in chart["text"]
    assert squash("chart page") in squash(chart["text"])                  # text-layer quotes still match
    assert logo["visual_mode"] == "skip" and logo["visual"] is None and logo["text"] == logo["text_layer"]
    assert blocked["visual_mode"] == "fallback" and "요약 수치" in blocked["text"]
    assert len(results[2]["calls"]) == 2
    terms = by[("terms.pdf", 1)]
    assert terms["visual"] is None and "visual_mode" not in terms and terms["text"] == terms["text_layer"]

    fake_vlm.clear()
    supplement_visuals(pages, pdfs, XCFG, tmp_path / "cache")             # rerun: everything from cache
    assert fake_vlm == []


def test_only_limits_vlm_pages(pdfs, tmp_path, fake_vlm):
    pages = extract_pages(pdfs, tmp_path / "pages.jsonl")
    out, results = supplement_visuals(pages, pdfs, XCFG, tmp_path / "cache", only={("x.pdf", 1)})
    assert [(r["file"], r["page"]) for r in results] == [("x.pdf", 1)]
    assert sum(1 for p in out if p.get("visual")) == 1
