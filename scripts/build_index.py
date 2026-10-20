"""Build the index for a config, per scope (A, B), under out/index/<index_key>/.

    python scripts/build_index.py --config configs/baseline.yaml [--scopes A,B]

The key covers corpus, chunking, and embedding settings, so a variant that changes only retrieval
reuses the baseline index and one that changes chunking builds its own.
"""

import argparse

import _paths  # noqa: F401
from rag import ROOT
from rag.chunking import chunk_pages
from rag.config import load_config
from rag.env import require_api_key, setup
from rag.ingest import in_scope, indexable, load_pages
from rag.retrieval import build_index, index_dir


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", required=True)
    p.add_argument("--scopes", default="A,B")
    args = p.parse_args()
    setup()
    require_api_key()
    cfg = load_config(args.config)
    pages = [pg for pg in load_pages(ROOT / cfg["corpus"]["pages"]) if indexable(pg, cfg)]
    for scope in args.scopes.split(","):
        target = index_dir(cfg, scope)
        if (target / "build.json").exists():
            print(f"{scope}: exists, skipped -> {target}")
            continue
        chunks = chunk_pages([pg for pg in pages if in_scope(pg, cfg, scope)], cfg)
        info = build_index(chunks, cfg, scope)
        print(f"{scope}: {info.get('n_chunks')} chunks -> {target}")


if __name__ == "__main__":
    main()
