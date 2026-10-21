"""Where are the remaining answer-score points lost? No LLM calls; reads results/ only.

    python scripts/loss_breakdown.py --runs dev_011_lite31_prompt2 dev_011_lite31_prompt2_r2 \
        --retrieval dev_002_structure_all_retrieval

Scores are graded correctness / 2, averaged over the given runs of one configuration. Questions are split by what
the answer step received: answerable with complete evidence in the context (loss = answer step), answerable with
incomplete evidence (loss related to retrieval), and not answerable (loss = clarify / refuse / abstain behaviour).
Also prints the reason the judge gave for each answerable question that had complete evidence but lost a point,
and the score the incomplete-evidence questions would reach if they scored like the complete ones (an optimistic
bound: submission/PROCESS.md section 7, "남은 개선 여지").
"""

import argparse
import json
import statistics as st
import sys

import _paths  # noqa: F401
from rag import ROOT


def read(experiment: str, name: str) -> dict:
    path = ROOT / "results" / experiment / name
    return {r["qid"]: r for r in map(json.loads, path.open(encoding="utf-8"))}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", nargs="+", required=True)
    parser.add_argument("--retrieval", required=True)
    args = parser.parse_args()
    gold = {g["qid"]: g for g in map(json.loads, (ROOT / "golden" / "provided.jsonl").open(encoding="utf-8"))}
    grades = [read(run, "grades.jsonl") for run in args.runs]
    evid = {q: r["evid"] for q, r in read(args.retrieval, "metrics.jsonl").items() if r.get("evid") is not None}
    score = {q: st.mean(g[q]["correctness"] for g in grades) / 2 for q in grades[0]}
    answerable = [q for q in score if gold[q]["answerable"]]
    complete = [q for q in answerable if evid.get(q) == 1]
    incomplete = [q for q in answerable if q in evid and evid[q] < 1]
    not_answerable = [q for q in score if not gold[q]["answerable"]]
    total_loss = len(score) - sum(score.values())
    print(f"runs {args.runs}: mean {st.mean(score.values()):.3f}, points lost {total_loss:.1f} of {len(score)}")
    for label, qs in (("answerable, evidence complete (answer-step loss)", complete),
                      ("answerable, evidence incomplete (retrieval-related loss)", incomplete),
                      ("not answerable (behaviour loss)", not_answerable)):
        lost = sum(1 - score[q] for q in qs)
        print(f"  {label:58s} n={len(qs):2d}  mean {st.mean(score[q] for q in qs):.3f}  lost {lost:4.1f} ({lost / total_loss:.0%})")
    gain = sum(st.mean(score[q] for q in complete) - score[q] for q in incomplete)
    print(f"  if incomplete-evidence questions scored like complete ones: +{gain:.1f} points -> mean "
          f"{(sum(score.values()) + gain) / len(score):.3f} (optimistic bound)")
    print("\nanswerable questions with complete evidence that lost points (judge reason, first run):")
    for q in sorted((q for q in complete if score[q] < 1), key=lambda q: score[q]):
        print(f"  {q} score {score[q]:.2f}: {grades[0][q]['reason'][:160]}")


if __name__ == "__main__":
    main()
