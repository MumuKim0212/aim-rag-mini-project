"""Extract every PDF page's text layer -> corpus/pages.jsonl, and print a diagnosis for workflow step 1.

    python scripts/extract_pages.py                       # writes corpus/pages.jsonl
    python scripts/extract_pages.py --out scratch/pages.jsonl

The diagnosis lists pages with little text (image-only or table-as-image candidates) and image counts per
file; check those pages against the PDF before freezing the extraction (golden evidence quotes are matched
against this file, and every index is built from it).
"""

import argparse
from collections import defaultdict

import _paths  # noqa: F401
from rag import ROOT
from rag.config import BASELINE, load_config
from rag.ingest import extract_pages, in_scope


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out")
    p.add_argument("--low-text", type=int, default=80, help="flag pages with fewer characters than this")
    args = p.parse_args()
    cfg = load_config(BASELINE)
    out = ROOT / (args.out or cfg["corpus"]["pages"])
    pages = extract_pages(ROOT / cfg["corpus"]["pdf_dir"], out)

    by_file = defaultdict(list)
    for page in pages:
        by_file[page["path"]].append(page)
    print(f"{len(pages)} pages from {len(by_file)} PDFs -> {out}\n")
    print(f"{'scope':5} {'pages':>5} {'chars':>8} {'images':>6}  low-text pages  file")
    for path, ps in by_file.items():
        scope = "A" if in_scope(ps[0], cfg, "A") else "B"
        low = [pg["page"] for pg in ps if pg["chars"] < args.low_text]
        print(f"{scope:5} {len(ps):5} {sum(pg['chars'] for pg in ps):8} {sum(pg['images'] for pg in ps):6}  "
              f"{(','.join(map(str, low)) or '-'):14}  {path}")


if __name__ == "__main__":
    main()
