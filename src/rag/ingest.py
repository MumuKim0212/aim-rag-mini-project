"""PDF -> pages. Output: corpus/pages.jsonl (committed), one page per line:

    {"file": "01_매매거래계좌설정약관.pdf", "path": "standard_terms/01_매매거래계좌설정약관.pdf",
     "page": 1, "text": "...", "chars": 1234, "images": 0}

- `file` (NFC) is what chunks carry as `source` and golden targets use; `path` is relative to corpus.pdf_dir
  and is what corpus.scopes patterns match.
- `page` is 1-based (PDF viewer numbering, as in the provided answers).
- Extraction is fixed once golden evidence quotes are matched against it; changing it means re-matching
  every quote and rebuilding every index.
"""

import fnmatch
import json
import unicodedata
from pathlib import Path

import pymupdf


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def extract_pages(pdf_dir: Path, out_path: Path) -> list[dict]:
    """Plain text layer of every PDF under pdf_dir, page by page (PyMuPDF). No OCR / VLM."""
    pdf_dir = Path(pdf_dir)
    pages = []
    for pdf in sorted(pdf_dir.rglob("*.pdf"), key=lambda p: nfc(p.relative_to(pdf_dir).as_posix())):
        rel = nfc(pdf.relative_to(pdf_dir).as_posix())
        with pymupdf.open(pdf) as doc:
            for number, page in enumerate(doc, start=1):
                text = page.get_text("text")
                pages.append({"file": nfc(pdf.name), "path": rel, "page": number, "text": text,
                              "chars": len(text.strip()), "images": len(page.get_images())})
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for page in pages:
            f.write(json.dumps(page, ensure_ascii=False) + "\n")
    return pages


def load_pages(path: Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def in_scope(page: dict, cfg: dict, scope: str) -> bool:
    return any(fnmatch.fnmatch(nfc(page["path"]), pattern) for pattern in cfg["corpus"]["scopes"][scope])


def title_of(file: str, cfg: dict) -> str:
    titles = cfg["corpus"].get("titles") or {}
    if file in titles:
        return titles[file]
    stem = file.rsplit(".", 1)[0]
    head, _, rest = stem.partition("_")
    return rest if head.isdigit() and rest else stem


def indexable(page: dict, cfg: dict) -> bool:
    excluded = cfg["corpus"].get("exclude_pages", {}).get(page["file"])
    return not (excluded and excluded[0] <= page["page"] <= excluded[1])
