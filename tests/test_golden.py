import json

from rag import ROOT
from rag.golden import BEHAVIORS, STATUSES


def test_every_provided_behavior_is_mapped():
    behaviors = set()
    for path in (ROOT / "03_answers").glob("*.jsonl"):
        with path.open(encoding="utf-8") as f:
            behaviors |= {json.loads(line)["expected_behavior"] for line in f if line.strip()}
    assert behaviors, "no provided answer files found"
    assert behaviors <= set(BEHAVIORS), sorted(behaviors - set(BEHAVIORS))


def test_pure_tampering_injection_accepts_refusal():
    # NEG034 has no real question behind the injected instruction: declining is as right as answering
    group, statuses = BEHAVIORS["ignore_injection_and_preserve_provenance"]
    assert group == "injection" and statuses == {"answered", "refused"}


def test_allowed_statuses_are_prompt_statuses():
    for group, statuses in BEHAVIORS.values():
        assert statuses and statuses <= set(STATUSES)


# ---- golden/self_v2.jsonl (self-written set v2, review_log.md) ----------------------------------------------

def _jsonl(path):
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_self_v2_is_a_consistent_golden_file():
    import unicodedata

    from evalkit.metrics import squash

    pages = {}
    for p in _jsonl(ROOT / "corpus" / "pages.jsonl"):
        pages[(unicodedata.normalize("NFC", p["file"]), p["page"])] = squash(p["text"])
    items = _jsonl(ROOT / "golden" / "self_v2.jsonl")
    assert len(items) == 28 and sum(not i["answerable"] for i in items) == 10
    qids = [i["qid"] for i in items]
    assert len(set(qids)) == len(qids)
    # new qids: must not collide with the archived draft (self.jsonl), self2.jsonl or the provided set
    used = {i["qid"] for name in ("self.jsonl", "self2.jsonl", "provided.jsonl") for i in _jsonl(ROOT / "golden" / name)}
    assert not used & set(qids)
    for i in items:
        assert i["set"] == "self3" and i["split"] == "test", i["qid"]
        assert i["expected_behavior"] in BEHAVIORS, i["qid"]
        if i["answerable"]:
            assert i["evidence"] and len(i["evidence"]) == len(i["evidence_pages"]) and i["targets"], i["qid"]
            for quote, where in zip(i["evidence"], i["evidence_pages"]):
                key = (unicodedata.normalize("NFC", where["file"]), where["page"])
                assert squash(quote) in pages[key], (i["qid"], key)
            for t in i["targets"]:
                assert (unicodedata.normalize("NFC", t["file"]), t["page"]) in pages, (i["qid"], t)
        else:
            assert not i["evidence"] and not i["targets"] and i["note"], i["qid"]


def test_self_v2_keeps_the_draft_questions():
    # the 20 draft items keep question, answer and quotes; only listed changes are allowed (review_log.md)
    draft = {i["qid"]: i for i in _jsonl(ROOT / "golden" / "self.jsonl")}
    v2 = {i["v1_qid"]: i for i in _jsonl(ROOT / "golden" / "self_v2.jsonl") if "v1_qid" in i}
    assert set(v2) == set(draft)
    for qid, old in draft.items():
        new = v2[qid]
        assert new["question"] == old["question"] and new["target_answer"] == old["target_answer"], qid
        assert new["evidence"][: len(old["evidence"])] == old["evidence"], qid       # extra quotes only appended
        assert new["targets"][: len(old["targets"])] == old["targets"], qid          # extra pages only appended
