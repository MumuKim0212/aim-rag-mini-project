"""Paired comparison of two experiments from results/, with cost and latency next to the score.

    python scripts/compare.py dev_000_baseline dev_007_lite31                      # answer score (grades)
    python scripts/compare.py dev_000_baseline dev_004_hybrid_retrieval --metric gold@5 --noise 5

Score comparisons use grades.jsonl (correctness, max 2); --metric compares a metrics.jsonl column
(max 1, or k for gold@k). Before an answer run, use evalkit.headroom on the same metrics files.
"""

import argparse
import json

import _paths  # noqa: F401
from evalkit import load_jsonl, to_map
from evalkit.paired import compare, report
from rag.harness import RESULTS_DIR

COST_ROWS = (("USD/question", "cost", "usd_per_question"), ("tokens/question", "cost", "tokens_per_question"),
             ("LLM calls/question", "calls", "llm_per_question"), ("p90 latency s", "latency_s", "p90"))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("a")
    p.add_argument("b")
    p.add_argument("--metric", help="metrics.jsonl column instead of the graded score")
    p.add_argument("--max-score", type=float)
    p.add_argument("--noise", type=int)
    args = p.parse_args()
    if args.metric:
        file, field = "metrics.jsonl", args.metric
        max_score = args.max_score or (float(field.split("@")[1]) if field.startswith("gold@") else 1.0)
    else:
        file, field, max_score = "grades.jsonl", "correctness", args.max_score or 2.0
    a = to_map(load_jsonl(RESULTS_DIR / args.a / file), field)
    b = to_map(load_jsonl(RESULTS_DIR / args.b / file), field)
    print(report(compare(a, b, max_score=max_score), args.a, args.b, noise=args.noise))
    sa, sb = (json.loads((RESULTS_DIR / x / "summary.json").read_text(encoding="utf-8")) for x in (args.a, args.b))
    for label, group, key in COST_ROWS:
        va, vb = (sa.get(group) or {}).get(key), (sb.get(group) or {}).get(key)
        ratio = f"  ({vb / va:.2f}x)" if va and vb is not None else ""
        print(f"{label:>20}: {va} -> {vb}{ratio}")


if __name__ == "__main__":
    main()
