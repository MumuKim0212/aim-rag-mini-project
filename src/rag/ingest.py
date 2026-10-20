"""PDF -> pages. Output: corpus/pages.jsonl (committed), one page per line:

    {"file": "01_매매거래계좌설정약관.pdf", "path": "standard_terms/01_매매거래계좌설정약관.pdf",
     "page": 1, "text": "...", "chars": 1234, "images": 0}

- `file` (NFC) is what chunks carry as `source` and golden targets use; `path` is relative to corpus.pdf_dir
  and is what corpus.scopes patterns match.
- `page` is 1-based (PDF viewer numbering, as in the provided answers).
- Extraction is fixed once golden evidence quotes are matched against it; changing it means re-matching.
"""

import fnmatch
import json
import unicodedata
from pathlib import Path


def extract_pages(pdf_dir: Path, out_path: Path) -> list[dict]:
    """Extract every PDF under pdf_dir page by page (PyMuPDF) and write out_path. Workflow step 1."""
    raise NotImplementedError("step 1: page extraction — see submission/PROCESS.md status table")


def load_pages(path: Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def in_scope(page: dict, cfg: dict, scope: str) -> bool:
    path = unicodedata.normalize("NFC", page["path"])
    return any(fnmatch.fnmatch(path, pattern) for pattern in cfg["corpus"]["scopes"][scope])


def indexable(page: dict, cfg: dict) -> bool:
    excluded = cfg["corpus"].get("exclude_pages", {}).get(page["file"])
    return not (excluded and excluded[0] <= page["page"] <= excluded[1])
