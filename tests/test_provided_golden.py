"""Guards for the frozen provided golden set (golden/provided.jsonl, written by scripts/convert_golden.py)."""

import json
from collections import Counter

import pytest

from evalkit.metrics import squash
from rag import ROOT
from rag.golden import load_golden

PATH = ROOT / "golden" / "provided.jsonl"
pytestmark = pytest.mark.skipif(not PATH.exists(), reason="golden/provided.jsonl not built yet")


def test_split_and_sets():
    items = load_golden(files=["provided.jsonl"])
    assert len(items) == 180
    assert Counter(i["split"] for i in items) == {"dev": 90, "test": 90}
    per_set = Counter((i["set"], i["split"]) for i in items)
    for s, n in {"base_positive": 30, "base_negative": 20, "life_guide": 10, "additional": 30}.items():
        assert per_set[(s, "dev")] == per_set[(s, "test")] == n


def test_every_quote_matches_its_page():
    with (ROOT / "corpus" / "pages.jsonl").open(encoding="utf-8") as f:
        pages = {(p["file"], p["page"]): squash(p["text"]) for p in map(json.loads, f)}
    for item in load_golden(files=["provided.jsonl"]):
        assert bool(item["evidence"]) == item["answerable"], item["qid"]
        for quote, where in zip(item["evidence"], item["evidence_pages"]):
            page = pages[(where["file"], where["page"])]
            assert all(squash(line) in page for line in quote.splitlines()), (item["qid"], quote[:40])
        evidence_pages = {(w["file"], w["page"]) for w in item["evidence_pages"]}
        assert evidence_pages <= {(t["file"], t["page"]) for t in item["targets"]}, item["qid"]
