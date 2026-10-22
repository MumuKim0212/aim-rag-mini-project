"""Collect the data for the chunker comparison page: Serin's structure chunker (aim-rag-serin, branch
serin-91/chunking-cards-001-002) vs the mixed chunker (chunking_sum.py, this worktree), same config 001e.

    python app/chunk_compare_data.py      # writes out/chunk_compare.json
"""

import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERIN = ROOT.parent / "aim-rag-serin"
OUT = ROOT / "out" / "chunk_compare.json"


def chunks_with(src_root: Path, cfg_name: str) -> list[dict]:
    """Chunk the corpus with the code under src_root (fresh import each time, so two versions can run)."""
    for m in [m for m in sys.modules if m == "rag" or m.startswith("rag.")]:
        del sys.modules[m]
    sys.path[:0] = [str(src_root / "src"), str(src_root)]
    try:
        rag = importlib.import_module("rag")
        rag.ROOT = ROOT                                  # same corpus/pages.jsonl for both
        cfg = importlib.import_module("rag.config").load_config(ROOT / "configs" / cfg_name)
        ingest = importlib.import_module("rag.ingest")
        chunking = importlib.import_module("rag.chunking")
        chunking.ROOT = ROOT
        pages = [p for p in ingest.load_pages(ROOT / cfg["corpus"]["pages"]) if ingest.indexable(p, cfg)]
        pages = [p for p in pages if ingest.in_scope(p, cfg, "B")]
        return chunking.chunk_pages(pages, cfg)
    finally:
        del sys.path[:2]


def stats(chunks: list[dict], max_chars: int) -> dict:
    lens = sorted(len(c["content"]) for c in chunks)
    return {"n": len(chunks), "mean": sum(lens) / len(lens), "median": lens[len(lens) // 2], "max": lens[-1],
            "over_max": sum(n > max_chars for n in lens), "lens": lens}


def main():
    serin = chunks_with(SERIN, "001e-chunk950-chain.yaml")
    mixed = chunks_with(ROOT, "014-mixed-chunk.yaml")
    header = chunks_with(ROOT, "014b-mixed-chunk-header.yaml")
    OUT.parent.mkdir(exist_ok=True)
    data = {"stats": {"serin": stats(serin, 1600), "mixed": stats(mixed, 1600), "header": stats(header, 1600)},
            "chunks": {"serin": serin, "mixed": mixed, "header": header}}
    OUT.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    for k, s in data["stats"].items():
        print(k, {x: v for x, v in s.items() if x != "lens"})


if __name__ == "__main__":
    main()
