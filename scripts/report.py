"""Collect results/*/summary.json into results/SUMMARY.md (committed, readable on GitHub) and
out/report.html (local, sortable; open it in a browser).

    python scripts/report.py
    python scripts/report.py --include-test --final   # workflow step 8 only
"""

import argparse

import _paths  # noqa: F401
from rag.harness import build_report


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--include-test", action="store_true")
    p.add_argument("--final", action="store_true")
    args = p.parse_args()
    print(build_report(include_test=args.include_test, final=args.final))


if __name__ == "__main__":
    main()
