"""Guards for the self-written golden set (golden/self2.jsonl, made by scripts/make_self2.py)."""

import json

from evalkit.metrics import squash
from rag import ROOT
from rag.golden import BEHAVIORS, load_golden


def test_self2_items_are_consistent():
    items = load_golden(files=["self2.jsonl"])
    assert len(items) == 41 and {i["split"] for i in items} == {"test"} and {i["set"] for i in items} == {"self2"}
    with (ROOT / "corpus" / "pages.jsonl").open(encoding="utf-8") as f:
        pages = {(p["file"], p["page"]): squash(p["text"]) for p in map(json.loads, f)}
    for item in items:
        assert item["expected_behavior"] in BEHAVIORS, item["qid"]
        assert bool(item["evidence"]) == item["answerable"] == bool(item["targets"]), item["qid"]
        for quote, where in zip(item["evidence"], item["evidence_pages"]):
            for line in filter(squash, quote.split("\n")):
                assert squash(line) in pages[(where["file"], where["page"])], (item["qid"], line[:30])
