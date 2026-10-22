"""Tables and images per PDF page -> out/doc_assets.json (read by the lab app's "문서와 페이지 추출" page).

    python scripts/doc_assets.py          # about 1.5 minutes, no API calls

Per page: tables found in the PDF itself (PyMuPDF find_tables, with rows x columns), embedded images (PyMuPDF),
and what the VLM supplement in corpus/pages.jsonl wrote for that page: tables (markdown "| ... |" blocks) and
figures ("[그림 ..." entries). The VLM ran only on scope-B pages that have tables, charts or images
(configs/extraction.yaml), so glossary and terms pages have no VLM entries.
"""

import json
import re

import _paths  # noqa: F401
import pymupdf
from rag import ROOT

OUT = ROOT / "out" / "doc_assets.json"


def vlm_counts(text: str) -> tuple[int, int]:
    tables = len(re.findall(r"(?m)^\|[ -:|]*---[ -:|]*\|\s*$", text or ""))  # one separator row per markdown table
    figures = len(re.findall(r"\[그림", text or ""))
    return tables, figures


def main():
    pages = [json.loads(line) for line in (ROOT / "corpus" / "pages.jsonl").read_text(encoding="utf-8").splitlines()]
    docs, out = {}, []
    for p in pages:
        doc = docs.get(p["path"]) or docs.setdefault(p["path"], pymupdf.open(ROOT / "01_data" / p["path"]))
        page = doc[p["page"] - 1]
        tables = page.find_tables().tables
        vt, vf = vlm_counts(p.get("visual") or "")
        out.append({"file": p["file"], "page": p["page"], "pdf_tables": len(tables),
                    "pdf_table_shapes": [f"{t.row_count}x{t.col_count}" for t in tables], "images": len(page.get_images()),
                    "vlm": p.get("visual_mode") or "", "vlm_tables": vt, "vlm_figures": vf})
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"-> {OUT}: {len(out)} pages, {sum(r['pdf_tables'] for r in out)} PDF tables, {sum(r['images'] for r in out)} images, "
          f"{sum(r['vlm_tables'] for r in out)} VLM tables, {sum(r['vlm_figures'] for r in out)} VLM figures")


if __name__ == "__main__":
    main()
