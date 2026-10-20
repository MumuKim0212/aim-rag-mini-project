"""PDF -> pages. Output: corpus/pages.jsonl (committed), one page per line:

    {"file": "01_매매거래계좌설정약관.pdf", "path": "standard_terms/01_매매거래계좌설정약관.pdf",
     "page": 1, "text": "...", "chars": 1234, "images": 0}

- `file` (NFC) is what chunks carry as `source` and golden targets use; `path` is relative to corpus.pdf_dir
  and is what corpus.scopes patterns match.
- `page` is 1-based (PDF viewer numbering, as in the provided answers).
- Extraction is fixed once golden evidence quotes are matched against it; changing it means re-matching
  every quote and rebuilding every index.
- With the visual supplement (configs/extraction.yaml), pages of the listed files also carry
  "text_layer" (original text), "visual" (VLM output or null), "visual_mode"; "text" is the text layer
  followed by the separator line and the supplement. Quotes from the text layer therefore still match.
"""

import fnmatch
import hashlib
import json
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pymupdf

from . import llm
from .prompts import fill, load_prompt


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


# ---------------------------------------------------------------- visual supplement (configs/extraction.yaml)

def needs_visual(page: dict, xcfg: dict) -> bool:
    return any(fnmatch.fnmatch(nfc(page["path"]), pattern) for pattern in xcfg["paths"])


def render_png(pdf_dir: Path, page: dict, dpi: int) -> bytes:
    with pymupdf.open(Path(pdf_dir) / page["path"]) as doc:  # opened per call: documents are not thread-safe
        return doc[page["page"] - 1].get_pixmap(dpi=dpi).tobytes("png")


def _cache_key(page: dict, xcfg: dict, prompt: dict) -> str:
    blob = json.dumps({"path": page["path"], "page": page["page"], "text": page["text"], "model": xcfg["model"],
                       "dpi": xcfg["dpi"], "thinking": xcfg.get("thinking_level"), "prompt": prompt},
                      sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


def describe_page(page: dict, pdf_dir: Path, xcfg: dict, prompt: dict, cache_dir: Path) -> dict:
    """VLM supplement for one page, cached. Returns {"visual", "mode", "finish", "calls"}; mode is
    "added" | "skip" | "fallback" (first answer blocked or empty, fallback prompt used) | "empty"."""
    cache = Path(cache_dir) / f"{_cache_key(page, xcfg, prompt)}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    png = render_png(pdf_dir, page, xcfg["dpi"])
    steps = {"calls": []}
    text_layer = page["text"].strip() or "(비어 있음)"
    kw = dict(model=xcfg["model"], system=prompt["system"], png=png, thinking_level=xcfg.get("thinking_level"),
              steps=steps, node="vlm_page", retries=xcfg.get("max_retries", 2), timeout_s=xcfg.get("timeout_s"))
    text, finish = llm.describe_image(user=fill(prompt["user"], text_layer=text_layer), **kw)
    mode = "added"
    if not text:
        text, finish = llm.describe_image(user=fill(prompt["fallback"], text_layer=text_layer), **kw)
        mode = "fallback"
    if text.strip().upper() == "SKIP":
        text, mode = "", "skip"
    elif not text:
        mode = "empty"
    result = {"visual": text or None, "mode": mode, "finish": finish, "calls": steps["calls"],
              "file": page["file"], "page": page["page"]}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result


def supplement_visuals(pages: list[dict], pdf_dir: Path, xcfg: dict, cache_dir: Path,
                       only: set | None = None) -> tuple[list[dict], list[dict]]:
    """Append the VLM supplement to pages matching xcfg["paths"] (or the (file, page) pairs in `only`).
    page["text_layer"] keeps the original text; page["text"] = text layer + separator + supplement.
    Returns (pages, results) where results hold every page's mode and recorded calls."""
    prompt = load_prompt(xcfg["prompt"], required=("system", "user", "fallback"))
    targets = [p for p in pages if needs_visual(p, xcfg) and (only is None or (p["file"], p["page"]) in only)]
    with ThreadPoolExecutor(max_workers=xcfg.get("concurrency", 4)) as pool:
        results = list(pool.map(lambda p: describe_page(p, pdf_dir, xcfg, prompt, cache_dir), targets))
    by_key = {(r["file"], r["page"]): r for r in results}
    out = []
    for page in pages:
        page = {**page, "text_layer": page["text"], "visual": None}
        r = by_key.get((page["file"], page["page"]))
        if r:
            page["visual_mode"] = r["mode"]
            if r["visual"]:
                page["visual"] = r["visual"]
                page["text"] = page["text_layer"].rstrip() + f"\n\n{xcfg['separator']}\n" + r["visual"] + "\n"
        out.append(page)
    return out, results


def write_pages(pages: list[dict], out_path: Path) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for page in pages:
            f.write(json.dumps(page, ensure_ascii=False) + "\n")
