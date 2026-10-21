"""Compare two answer models that were each run more than once on the same questions (card 007 section 8),
without LLM calls. Needs graded results in results/<experiment>/grades.jsonl.

    python scripts/model_rerun_compare.py --a dev_007_flash38 dev_007_flash38_r2 --b dev_007_lite31 dev_007_lite31_r2

Scores are the graded correctness (0/1/2) divided by 2. Reported:
- per run: mean score
- noise of each model: |mean(run 1) - mean(run 2)|, and how many questions changed between its two runs
- delta_i = mean(A run i) - mean(B run i) for each pair of same-numbered runs, and the average delta
- verdict (rule fixed before the runs, experiments/007-answer-model.md section 8): A is higher than B if the
  average delta is larger than the larger of the two models' noise AND every pair has delta_i > 0; B is higher
  if the mirror image holds; otherwise the models are not distinguished.
- by golden set and by answerability: the average delta of each group (report only)
"""

import argparse
import json
import sys

import _paths  # noqa: F401
from rag import ROOT


def grades(experiment: str) -> dict:
    path = ROOT / "results" / experiment / "grades.jsonl"
    return {r["qid"]: r["correctness"] / 2 for r in map(json.loads, path.open(encoding="utf-8"))}


def meta() -> dict:
    return {g["qid"]: g for g in map(json.loads, (ROOT / "golden" / "provided.jsonl").open(encoding="utf-8"))}


def mean(values) -> float:
    values = list(values)
    return sum(values) / len(values)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--a", nargs="+", required=True)
    parser.add_argument("--b", nargs="+", required=True)
    args = parser.parse_args()
    if len(args.a) != len(args.b):
        sys.exit("--a and --b need the same number of runs")
    A, B = [grades(e) for e in args.a], [grades(e) for e in args.b]
    qids = sorted(set.intersection(*[set(g) for g in A + B]))
    info = meta()
    print(f"{len(qids)} questions common to all {len(A) + len(B)} runs")
    noise = {}
    for label, runs, names in (("A", A, args.a), ("B", B, args.b)):
        means = [mean(g[q] for q in qids) for g in runs]
        print(f"{label}: " + "  ".join(f"{n} {m:.3f}" for n, m in zip(names, means)))
        if len(runs) > 1:
            changed = sum(runs[0][q] != runs[1][q] for q in qids)
            better = sum(runs[1][q] > runs[0][q] for q in qids)
            worse = sum(runs[1][q] < runs[0][q] for q in qids)
            noise[label] = abs(means[0] - means[1])
            print(f"   rerun noise: |run1 - run2| = {noise[label]:.3f}; {changed} questions changed (run 2 better {better} / worse {worse})")
    deltas = [mean(a[q] for q in qids) - mean(b[q] for q in qids) for a, b in zip(A, B)]
    average = mean(deltas)
    threshold = max(noise.values()) if noise else 0.0
    print("delta (A - B) per run pair: " + "  ".join(f"{d:+.3f}" for d in deltas) + f"   average {average:+.3f}   noise threshold {threshold:.3f}")
    if average > threshold and all(d > 0 for d in deltas):
        verdict = "A is higher than B"
    elif -average > threshold and all(d < 0 for d in deltas):
        verdict = "B is higher than A"
    else:
        verdict = "not distinguished"
    print("verdict:", verdict)
    per_question = {q: mean(a[q] for a in A) - mean(b[q] for b in B) for q in qids}
    print(f"questions with A's average score higher: {sum(v > 0 for v in per_question.values())}, "
          f"lower: {sum(v < 0 for v in per_question.values())}, equal: {sum(v == 0 for v in per_question.values())}")
    groups = {}
    for q in qids:
        for key in (info[q]["set"], "answerable" if info[q]["answerable"] else "not answerable", info[q]["difficulty"]):
            groups.setdefault(key, []).append(q)
    for key in sorted(groups):
        qs = groups[key]
        print(f"  {key:16s} n={len(qs):2d}  average delta {mean(per_question[q] for q in qs):+.3f}")


if __name__ == "__main__":
    main()
