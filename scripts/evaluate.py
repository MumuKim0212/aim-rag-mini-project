"""Score an experiment without LLM calls and export it to results/<experiment>/ (see results/README.md).

    python scripts/evaluate.py --experiment dev_004_hybrid_retrieval
    python scripts/evaluate.py --experiment dev_000_baseline --with-runs   # baseline, adopted, final test, 007, 008
"""

import argparse

import _paths  # noqa: F401
from rag.env import setup
from rag.harness import evaluate_experiment


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--experiment", required=True)
    p.add_argument("--with-runs", action="store_true", help="also export runs.jsonl")
    p.add_argument("--overwrite", action="store_true", help="only for folders not yet used in a decision")
    p.add_argument("--final", action="store_true", help="allow test experiments (workflow step 8)")
    args = p.parse_args()
    setup()
    s = evaluate_experiment(args.experiment, with_runs=args.with_runs, final=args.final, overwrite=args.overwrite)
    print({k: s[k] for k in ("experiment", "n_questions", "n_errors", "n_graded", "scores", "retrieval", "cost")})


if __name__ == "__main__":
    main()
