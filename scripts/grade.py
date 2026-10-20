"""Grade an experiment's latest run per question with the fixed judge -> out/grades/<experiment>.jsonl.

    python scripts/grade.py --experiment dev_000_baseline
    python scripts/grade.py --experiment dev_000_baseline --suffix __regrade1   # noise (b): same answers again
"""

import argparse

import _paths  # noqa: F401
from rag.env import require_api_key, setup
from rag.harness import grade_experiment


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--experiment", required=True)
    p.add_argument("--suffix", default="")
    p.add_argument("--final", action="store_true", help="allow test experiments (workflow step 8)")
    args = p.parse_args()
    setup()
    require_api_key()
    print(grade_experiment(args.experiment, suffix=args.suffix, final=args.final))


if __name__ == "__main__":
    main()
