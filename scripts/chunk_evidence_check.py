"""Implementation check for a chunking variant, without LLM or embedding calls (card 002 section 1).

    python scripts/chunk_evidence_check.py --config configs/002-structure.yaml

Compares the variant with the baseline chunking on the same indexable pages:
1. Scope A text retention: every non-empty line of every scope-A page (page number line excluded) must appear in some
   chunk of its file. Lines that do not are printed (card 002: only the glossary title "금융용어 모음").
2. Evidence in one piece (dev split only; the test split is never read here): how many golden evidence quotes lie
   whole inside a single chunk on a gold page, baseline vs variant, and which questions changed.
"""

import argparse
import json
import sys

import _paths  # noqa: F401
from evalkit.metrics import nfc, squash
from rag import ROOT
from rag.chunking import chunk_pages
from rag.config import BASELINE, load_config
from rag.ingest import in_scope, indexable, load_pages


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    base, variant = load_config(BASELINE), load_config(args.config)
    pages = [p for p in load_pages(ROOT / base["corpus"]["pages"]) if indexable(p, base)]
    chunks = {(name, scope): chunk_pages([p for p in pages if in_scope(p, cfg, scope)], cfg)
              for name, cfg in (("baseline", base), ("variant", variant)) for scope in "AB"}

    by_file = {}
    for chunk in chunks[("variant", "A")]:
        by_file.setdefault(chunk["source"], []).append(squash(chunk["content"]))
    checked, missing = 0, []
    for page in (p for p in pages if in_scope(p, base, "A")):
        for n, line in enumerate(page["text"].split("\n")):
            text = squash(line)
            if not text or (n == 0 and text == str(page["page"])):
                continue
            checked += 1
            if not any(text in c for c in by_file.get(page["file"], [])):
                missing.append((page["file"], page["page"], line[:40]))
    print(f"scope A lines checked {checked}, not in any variant chunk {len(missing)}: {missing[:5]}")

    golden = [g for g in map(json.loads, (ROOT / "golden" / "provided.jsonl").open(encoding="utf-8"))
              if g["split"] == "dev" and g.get("evidence") and g.get("targets")]
    split = {}
    for name in ("baseline", "variant"):
        total = whole = 0
        split[name] = set()
        for g in golden:
            scope = base["corpus"]["set_scope"][g["set"]]
            targets = {(nfc(t["file"]), t["page"]) for t in g["targets"]}
            texts = [squash(c["content"]) for c in chunks[(name, scope)]
                     if any((nfc(c["source"]), pg) in targets for pg in c["pages"])]
            for quote in g["evidence"]:
                total += 1
                if any(squash(quote) in t for t in texts):
                    whole += 1
                else:
                    split[name].add(g["qid"])
        print(f"{name}: evidence quotes whole in one gold-page chunk {whole} / {total}")
    print("made whole by the variant:", sorted(split["baseline"] - split["variant"]),
          "| newly split:", sorted(split["variant"] - split["baseline"]))


if __name__ == "__main__":
    main()
