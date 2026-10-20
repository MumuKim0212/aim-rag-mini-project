"""Run a system over golden questions; every run goes to out/runs.db. Interrupted batches resume.

    python scripts/run.py --config configs/baseline.yaml --split dev
    python scripts/run.py --config configs/004-hybrid.yaml --split dev --retrieval-only   # LLM-free comparison
    python scripts/run.py --config configs/baseline.yaml --split dev --limit 3            # smoke test
    python scripts/run.py --config configs/baseline.yaml --split dev --name dev_000_baseline_r2   # noise (a)

Experiment name: <split>_<config name>[_retrieval]. The test split needs --final (workflow step 8 only).
Answer runs other than the baseline and noise runs need an experiment card with passed gates (CLAUDE.md).
"""

import argparse

import _paths  # noqa: F401
from rag.config import experiment_name, load_config
from rag.env import require_api_key, setup
from rag.harness import run_experiment


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", required=True)
    p.add_argument("--split", required=True, choices=["dev", "test"])
    p.add_argument("--sets", help="comma-separated golden sets, e.g. base_positive,base_negative")
    p.add_argument("--limit", type=int)
    p.add_argument("--retrieval-only", action="store_true")
    p.add_argument("--name", help="experiment name override (noise rerun)")
    p.add_argument("--final", action="store_true", help="allow the test split (workflow step 8)")
    args = p.parse_args()
    setup()
    require_api_key()
    cfg = load_config(args.config)
    experiment = args.name or experiment_name(cfg, args.split, args.retrieval_only)
    print(f"{experiment}: changed vs baseline = {cfg['changed'] or 'nothing'}")
    result = run_experiment(cfg, args.split, experiment=experiment,
                            sets=args.sets.split(",") if args.sets else None, limit=args.limit,
                            retrieval_only=args.retrieval_only, final=args.final)
    print(result)


if __name__ == "__main__":
    main()
