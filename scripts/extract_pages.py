"""Extract every PDF page -> corpus/pages.jsonl, optionally with the VLM supplement, and print a diagnosis.

    python scripts/extract_pages.py                                  # text layer only
    python scripts/extract_pages.py --vlm                            # + VLM supplement (configs/extraction.yaml)
    python scripts/extract_pages.py --vlm --only "financial_life_guide.pdf:23,26" --out scratch/pilot.jsonl

--only limits the VLM to the listed pages (pilot); every page's text layer is still written.
With --vlm, a run summary (model, prompt, pages per mode, tokens, USD) goes next to the output as
extraction.json. Results are cached per page in out/vlm_cache, so a rerun resumes for free.
corpus/pages.jsonl is frozen once golden evidence is matched against it (see configs/extraction.yaml).
"""

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from importlib import metadata

import _paths  # noqa: F401
import yaml
from rag import ROOT
from rag.config import BASELINE, load_config
from rag.cost import load_prices, totals
from rag.env import require_api_key, setup
from rag.ingest import extract_pages, in_scope, nfc, supplement_visuals, write_pages

EXTRACTION = ROOT / "configs" / "extraction.yaml"


def parse_only(spec: str) -> set:
    pairs = set()
    for part in spec.split(";"):
        file, pages = part.rsplit(":", 1)
        pairs |= {(nfc(file.strip()), int(n)) for n in pages.split(",")}
    return pairs


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out")
    p.add_argument("--vlm", action="store_true", help="add the VLM supplement (configs/extraction.yaml)")
    p.add_argument("--only", help='pilot: "file.pdf:1,2;other.pdf:5" — VLM only on these pages')
    p.add_argument("--low-text", type=int, default=80, help="flag pages with fewer characters than this")
    args = p.parse_args()
    setup()
    cfg = load_config(BASELINE)
    out = ROOT / (args.out or cfg["corpus"]["pages"])
    pdf_dir = ROOT / cfg["corpus"]["pdf_dir"]
    pages = extract_pages(pdf_dir, out)

    if args.vlm:
        require_api_key()
        xcfg = yaml.safe_load(EXTRACTION.read_text(encoding="utf-8"))["visual"]
        pages, results = supplement_visuals(pages, pdf_dir, xcfg, ROOT / xcfg["cache_dir"],
                                            only=parse_only(args.only) if args.only else None)
        write_pages(pages, out)
        calls = [c for r in results for c in r["calls"]]
        cost = totals(calls, load_prices())
        modes = Counter(r["mode"] for r in results)
        summary = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "output": out.relative_to(ROOT).as_posix(),
            "pages": len(pages), "vlm_pages": len(results), "modes": dict(modes),
            "pilot_only": args.only,
            "visual": xcfg, "prompt_sha1": hashlib.sha1((ROOT / xcfg["prompt"]).read_bytes()).hexdigest()[:12],
            "pymupdf": metadata.version("pymupdf"),
            "calls": cost["llm_calls"], "input_tokens": cost["input_tokens"], "output_tokens": cost["output_tokens"],
            "thinking_tokens": cost["thinking_tokens"], "usd": round(cost["usd"], 4),
            "finish_reasons": dict(Counter(c.get("finish_reason") for c in calls)),
        }
        (out.parent / "extraction.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"VLM: {len(results)} pages {dict(modes)}, {cost['llm_calls']} calls, "
              f"in {cost['input_tokens']} / out {cost['output_tokens']} tokens, ${cost['usd']:.4f}")

    by_file = defaultdict(list)
    for page in pages:
        by_file[page["path"]].append(page)
    print(f"{len(pages)} pages from {len(by_file)} PDFs -> {out}\n")
    print(f"{'scope':5} {'pages':>5} {'chars':>8} {'images':>6} {'vlm+':>5}  low-text pages  file")
    for path, ps in by_file.items():
        scope = "A" if in_scope(ps[0], cfg, "A") else "B"
        low = [pg["page"] for pg in ps if pg["chars"] < args.low_text]
        added = sum(1 for pg in ps if pg.get("visual"))
        print(f"{scope:5} {len(ps):5} {sum(pg['chars'] for pg in ps):8} {sum(pg['images'] for pg in ps):6} "
              f"{added:5}  {(','.join(map(str, low)) or '-'):14}  {path}")


if __name__ == "__main__":
    main()
