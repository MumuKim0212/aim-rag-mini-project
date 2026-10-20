"""Paired per-question comparison of two graded runs on the same questions. No LLM calls.

Use it for every A/B decision and for measuring noise (workflow step 3): compare two runs of the SAME
config (total noise), or two gradings of the SAME answers (judge noise). The number of questions that
changed there is the smallest difference worth acting on; pass it as --noise to later comparisons.

    python -m evalkit.paired grades_base.jsonl grades_new.jsonl --field correctness --max-score 2
    python -m evalkit.paired grades_base.jsonl grades_new.jsonl --max-score 2 --noise 5

Each file is JSONL with a `qid` and a score field. --where filters rows of both files (key=value,
compared as strings); --where-a / --where-b filter one file. Compare answerable questions only, or score
refusals separately: an abstention on an unanswerable question is a success, not a 0.
"""

import argparse
import random

from . import load_jsonl, parse_where, to_map


def bootstrap_ci(diffs: list[float], n_boot: int = 5000, seed: int = 0, alpha: float = 0.05) -> tuple[float, float]:
    """Percentile bootstrap CI of the mean paired difference."""
    rng = random.Random(seed)
    n = len(diffs)
    means = sorted(sum(rng.choices(diffs, k=n)) / n for _ in range(n_boot))
    return means[int(n_boot * alpha / 2)], means[min(n_boot - 1, int(n_boot * (1 - alpha / 2)))]


def compare(a: dict, b: dict, max_score: float = 1.0, n_boot: int = 5000, seed: int = 0) -> dict:
    """a, b: {qid: score}. Only questions present in both are compared. Means are divided by max_score."""
    qids = sorted(a.keys() & b.keys())
    if not qids:
        raise ValueError("the two runs share no question ids")
    diffs = [(b[q] - a[q]) / max_score for q in qids]
    low, high = bootstrap_ci(diffs, n_boot, seed)
    return {
        "n": len(qids),
        "mean_a": sum(a[q] for q in qids) / len(qids) / max_score,
        "mean_b": sum(b[q] for q in qids) / len(qids) / max_score,
        "diff": sum(diffs) / len(diffs),
        "ci95": (low, high),
        "b_better": [q for q, d in zip(qids, diffs) if d > 0],
        "a_better": [q for q, d in zip(qids, diffs) if d < 0],
        "same": sum(1 for d in diffs if d == 0),
        "only_in_a": len(a.keys() - b.keys()),
        "only_in_b": len(b.keys() - a.keys()),
    }


def report(r: dict, name_a: str = "A", name_b: str = "B", noise: int | None = None) -> str:
    lines = [
        f"n={r['n']}  {name_a} {r['mean_a']:.3f}  {name_b} {r['mean_b']:.3f}  "
        f"diff {r['diff']:+.3f}  95% CI [{r['ci95'][0]:+.3f}, {r['ci95'][1]:+.3f}]",
        f"{name_b} better {len(r['b_better'])} / {name_a} better {len(r['a_better'])} / same {r['same']}",
        f"  {name_b} better: {' '.join(r['b_better'])}",
        f"  {name_a} better: {' '.join(r['a_better'])}",
    ]
    if r["only_in_a"] or r["only_in_b"]:
        lines.append(f"not compared: only in {name_a} {r['only_in_a']}, only in {name_b} {r['only_in_b']}")
    if noise is not None:
        net = len(r["b_better"]) - len(r["a_better"])
        verdict = "larger than noise" if abs(net) > noise else "within noise: do not read it as a difference"
        lines.append(f"net {net:+d} questions vs noise {noise}: {verdict}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Paired comparison of two graded runs.")
    parser.add_argument("a", help="graded run A (JSONL)")
    parser.add_argument("b", help="graded run B (JSONL)")
    parser.add_argument("--field", default="correctness", help="score field (default: correctness)")
    parser.add_argument("--max-score", type=float, default=1.0, help="divide scores by this (2 for 0/1/2)")
    parser.add_argument("--where", nargs="*", default=[], help="key=value filters for both files")
    parser.add_argument("--where-a", nargs="*", default=[], help="key=value filters for file A only")
    parser.add_argument("--where-b", nargs="*", default=[], help="key=value filters for file B only")
    parser.add_argument("--noise", type=int, default=None, help="questions changed in the step-3 noise run")
    parser.add_argument("--n-boot", type=int, default=5000)
    args = parser.parse_args()

    a = to_map(load_jsonl(args.a, parse_where(args.where, args.where_a)), args.field)
    b = to_map(load_jsonl(args.b, parse_where(args.where, args.where_b)), args.field)
    print(report(compare(a, b, args.max_score, args.n_boot), args.a, args.b, args.noise))


if __name__ == "__main__":
    main()
