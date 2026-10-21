"""Checks for a change that only touches part of the corpus (cards 002, 003), without LLM calls.

    python scripts/scope_check.py noise dev_000_baseline dev_000_baseline_r2 --sets base_positive,base_negative
    python scripts/scope_check.py exposure dev_000_baseline dev_002_structure_B_retrieval --sets life_guide,additional

noise     questions of the given golden sets whose graded score differs between two runs of the same setting (the
          noise of that population; the project-wide number is PROCESS.md section 4).
exposure  for the given sets, how many questions have a glossary / standard-terms chunk among the top-5 contexts, and
          for how many the top-5 list differs between two experiments. Scope B contains the scope-A documents, so a
          chunking change for those documents can reach scope-B questions; "no change" has to be checked, not assumed.
"""

import argparse
import json
import re
import sys

import _paths  # noqa: F401
from evalkit.runlog import RunLog
from rag import ROOT


def metrics(experiment: str) -> dict:
    path = ROOT / "results" / experiment / "metrics.jsonl"
    return {r["qid"]: r for r in map(json.loads, path.open(encoding="utf-8"))}


def scope_a_source(source: str) -> bool:
    return source.startswith("financial_glossary") or bool(re.match(r"\d\d_", source))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["noise", "exposure"])
    parser.add_argument("a")
    parser.add_argument("b")
    parser.add_argument("--sets", required=True)
    args = parser.parse_args()
    sets = set(args.sets.split(","))
    meta = metrics(args.a)
    qids = [q for q, r in meta.items() if r["set"] in sets]
    if args.mode == "noise":
        grades = {n: {r["qid"]: r["correctness"] for r in map(json.loads, (ROOT / "results" / n / "grades.jsonl").open(encoding="utf-8"))}
                  for n in (args.a, args.b)}
        changed = sorted(q for q in qids if grades[args.a][q] != grades[args.b][q])
        print(f"{len(qids)} questions in {sorted(sets)}, score differs between runs for {len(changed)}: {changed}")
        return
    log = RunLog(ROOT / "out" / "runs.db")
    ctx = {n: {r["qid"]: [(u["source"], u["page"], u["content"]) for u in r["context"]] for r in log.latest(n)}
           for n in (args.a, args.b)}
    qids = [q for q in qids if q in ctx[args.b]]
    for name in (args.a, args.b):
        exposed = [q for q in qids if any(scope_a_source(u[0]) for u in ctx[name][q])]
        print(f"{name}: {len(exposed)} / {len(qids)} questions have a glossary/terms chunk in the top 5 {exposed}")
    differs = [q for q in qids if ctx[args.a][q] != ctx[args.b][q]]
    print(f"top-5 contexts differ for {len(differs)} questions: {differs}")


if __name__ == "__main__":
    main()
