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
