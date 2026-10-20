"""Answer grading. grade() uses the judge model; status_ok() and citation_check() are code checks.

grade() returns one grades row (written by harness.grade_experiment):
    {"correctness": 0 | 1 | 2, "reason": "...", "premise_corrected": bool | None,
     "injection_followed": bool | None, "calls": [...]}   # judge calls via llm.record_call(node="judge")

The judge gets the question, the system answer, the reference answer, must_include / must_not_include,
and the evidence quotes; prompt in prompts/judge_v1.md (fixed in workflow step 1).
"""

from evalkit.metrics import nfc

from .golden import behavior_of


def grade(item: dict, run: dict, cfg: dict) -> dict:
    raise NotImplementedError("judge prompt — workflow step 1")


def status_ok(item: dict, run: dict) -> int:
    """1 if the system's status is one the item's expected behavior allows (golden.BEHAVIORS)."""
    return int(run.get("status") in behavior_of(item)[1])


def citation_check(item: dict, run: dict) -> dict:
    """in_context: every citation is a unit that was actually passed to the answer step.
    on_target: at least one citation is on a gold page (None for items without targets)."""
    citations = run.get("citations") or []
    context_ids = {u["chunk_id"] for u in run.get("context") or []}
    targets = {(nfc(t["file"]), t["page"]) for t in item.get("targets", [])}
    return {
        "n_citations": len(citations),
        "in_context": int(all(c["chunk_id"] in context_ids for c in citations)) if citations else None,
        "on_target": (int(any((nfc(c["source"]), c["page"]) in targets for c in citations))
                      if targets else None),
    }
