"""Distinct pages and distinct documents per question in the contexts of logged runs, without LLM calls
(card 005: does MMR spread the context over more pages?).

    python scripts/context_diversity.py dev_002_structure_all_retrieval dev_005_mmr_retrieval
"""

import statistics
import sys

import _paths  # noqa: F401
from evalkit.runlog import RunLog
from rag import ROOT


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    log = RunLog(ROOT / "out" / "runs.db")
    for experiment in sys.argv[1:]:
        runs = [r for r in log.latest(experiment) if r.get("context")]
        pages = [len({(u["source"], u["page"]) for u in r["context"]}) for r in runs]
        docs = [len({u["source"] for u in r["context"]}) for r in runs]
        sizes = [len(r["context"]) for r in runs]
        print(f"{experiment}: {len(runs)} questions, chunks {statistics.mean(sizes):.2f}, "
              f"distinct pages {statistics.mean(pages):.2f}, distinct documents {statistics.mean(docs):.2f}")


if __name__ == "__main__":
    main()
