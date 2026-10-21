"""Chunk statistics without any API call: how many chunks, how long, and how many dev evidence quotes
no single chunk contains in full ("cut quotes", card 002). Dev split only.

    python scripts/chunk_stats.py --config configs/002-structure.yaml
"""

import argparse
import statistics

import _paths  # noqa: F401
from evalkit.metrics import squash
from rag import ROOT
from rag.chunking import chunk_pages
from rag.config import load_config
from rag.golden import load_golden, scope_of
from rag.ingest import in_scope, indexable, load_pages


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", required=True)
    args = p.parse_args()
    cfg = load_config(args.config)
    pages = [pg for pg in load_pages(ROOT / cfg["corpus"]["pages"]) if indexable(pg, cfg)]
    items = [i for i in load_golden(split="dev") if i.get("targets")]
    for scope in ("A", "B"):
        chunks = chunk_pages([pg for pg in pages if in_scope(pg, cfg, scope)], cfg)
        text = [squash(c["content"]) for c in chunks]
        sizes = [len(c["content"]) for c in chunks]
        cut, total, qids = 0, 0, set()
        for item in (i for i in items if scope_of(i, cfg) == scope):
            for quote in item["evidence"]:
                total += 1
                if not any(squash(quote) in t for t in text):
                    cut += 1
                    qids.add(item["qid"])
        print(f"{cfg['name']} scope {scope}: {len(chunks)} chunks, chars median {statistics.median(sizes):.0f} "
              f"max {max(sizes)}, dev quotes cut {cut}/{total} in {len(qids)} questions: {' '.join(sorted(qids))}")


if __name__ == "__main__":
    main()
