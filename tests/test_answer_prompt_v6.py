"""answer_v6 = answer_v4 + rule 12 only (card 016); the baseline chain fills {question} and {context} and nothing else."""

import re

from rag.prompts import fill, load_prompt


def test_v6_differs_from_v4_by_rule_12_only():
    v4, v6 = load_prompt("prompts/answer_v4.md"), load_prompt("prompts/answer_v6.md")
    lines = v6["system"].splitlines()
    rule = [line for line in lines if line.startswith("12. ")]
    assert len(rule) == 1
    assert "\n".join(line for line in lines if not line.startswith("12. ")) == v4["system"]
    assert v6["user"] == v4["user"]


def test_v6_placeholders_are_question_and_context():
    user = load_prompt("prompts/answer_v6.md")["user"]
    assert set(re.findall(r"\{([a-z_]+)\}", user)) == {"question", "context"}
    assert not re.search(r"\{[a-z_]+\}", fill(user, question="q", context="c"))
