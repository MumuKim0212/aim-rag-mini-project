import re

from rag import judge
from rag.golden import BEHAVIORS
from rag.prompts import fill, load_prompt


def test_every_behavior_group_has_a_rule():
    assert {group for group, _ in BEHAVIORS.values()} == set(judge.BEHAVIOR_RULES)


def test_judge_prompt_placeholders_are_all_filled(monkeypatch):
    seen = {}

    def fake_generate_json(**kwargs):
        seen.update(kwargs)
        return judge.GradeOut(reason="ok", correctness=2, premise_corrected=True, injection_followed=None)

    monkeypatch.setattr(judge.llm, "generate_json", fake_generate_json)
    item = {"qid": "NEG999", "question": "q", "expected_behavior": "correct_with_citation", "target_answer": "ref",
            "must_include": ["a"], "must_not_include": [], "evidence": ["quote"]}
    cfg = {"judge": {"model": "m", "prompt": "prompts/judge_v1.md", "temperature": 0, "thinking_level": "low"},
           "run": {"max_retries": 0, "timeout_s": 10}}
    row = judge.grade(item, {"status": "answered", "answer": "ans"}, cfg)
    assert not re.search(r"\{[a-z_]+\}", seen["user"])
    assert row["correctness"] == 2 and row["premise_corrected"] is True and row["injection_followed"] is None
    assert row["behavior_group"] == "correct"


def test_prompts_frozen_sections():
    for path in ("prompts/judge_v1.md", "prompts/answer_v1.md"):
        p = load_prompt(path)
        assert fill(p["user"]) and p["system"]
