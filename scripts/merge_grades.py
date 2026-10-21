"""Merge graded answers of two experiments into one grades file by golden set, so `evalkit.headroom` and
`evalkit.paired` can use a baseline that was graded in two runs (no LLM calls).

    python scripts/merge_grades.py --a dev_002_structure --sets-a base_positive,base_negative \
        --b dev_000_baseline --sets-b life_guide,additional --out out/grades/structure_base_merged.jsonl

Use it only when the two experiments give the same retrieval for the sets taken from each (e.g. card 004: the
structure chunking changes only the scope-A documents, so for the scope-B questions the Recursive baseline's
answers are valid baseline answers; card 002 section 7 lists the one exception, ADD-RP04).
"""

import argparse
import json
import sys

import _paths  # noqa: F401
from rag import ROOT


def rows(experiment: str, sets: set[str]) -> list[dict]:
    folder = ROOT / "results" / experiment
    meta = {r["qid"]: r["set"] for r in map(json.loads, (folder / "metrics.jsonl").open(encoding="utf-8"))}
    return [r for r in map(json.loads, (folder / "grades.jsonl").open(encoding="utf-8")) if meta.get(r["qid"]) in sets]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--a", required=True)
    parser.add_argument("--sets-a", required=True)
    parser.add_argument("--b", required=True)
    parser.add_argument("--sets-b", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    merged = rows(args.a, set(args.sets_a.split(","))) + rows(args.b, set(args.sets_b.split(",")))
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for row in merged:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"{len(merged)} graded rows ({args.a}: {args.sets_a}; {args.b}: {args.sets_b}) -> {out}")


if __name__ == "__main__":
    main()
