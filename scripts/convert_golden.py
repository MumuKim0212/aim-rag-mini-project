"""Convert the provided question/answer set (03_answers/*.jsonl) -> golden/provided.jsonl (workflow step 1).

    python scripts/convert_golden.py            # writes golden/provided.jsonl, prints the check
    python scripts/convert_golden.py --check    # check only, writes nothing

What it does (submission/PLAN.md §2.2, golden/README.md "This project"):
1. Source IDs -> (file, page) on corpus/pages.jsonl:
   - fsc-glossary-N        glossary source list (p.20-) line with dicId=N -> term -> the page whose line is that term
   - kofia-terms-X-V-A     "버전: V" on page 1 of a standard-terms PDF -> file; A -> 제A조 -> pages the article spans
   - <file>-pdf-N          page N of <file>.pdf (life guide, additional)
2. Evidence: verbatim quotes from the target pages (corpus/pages.jsonl `text`: the PDF text layer, plus the VLM
   supplement for scope-B pages). Each quote is tagged `source` text / vlm; VLM quotes were checked against the
   page images (golden/review_log.md). golden/evidence.jsonl (reviewed by hand, one line per
   question) is used when present; otherwise sentences are picked automatically by overlap with the reference
   answer and must_include, and the item is reported as unreviewed.
3. Targets = the pages that contain the evidence quotes (an article can span two pages; only pages holding
   the quoted sentences count).
4. dev/test split: stratified by set x difficulty (x category for negatives, x source_file for additional),
   balanced 50:50 per set and per additional document;
   seed SEED. Each stratum is shuffled and alternated; which odd-sized strata give their extra question to dev
   is searched so difficulty, context type and negative category stay as even as possible (assign_split).

Every quote must auto-match its page after evalkit.metrics.squash; the check fails otherwise.
golden/provided.jsonl is frozen once a run has used it: a fix means provided_v2.jsonl and a PROCESS.md note.
"""

import argparse
import json
import random
import re
from collections import Counter, defaultdict
from itertools import combinations, product

import _paths  # noqa: F401
from evalkit.metrics import squash
from rag import ROOT
from rag.config import BASELINE, load_config
from rag.ingest import in_scope, indexable, load_pages, nfc

SEED = 20261020
ANSWERS = ROOT / "03_answers"
GOLDEN = ROOT / "golden"
ANSWER_FILES = {  # file -> golden `set`
    "positive_cases.jsonl": "base_positive",
    "negative_cases.jsonl": "base_negative",
    "positive_life_guide_cases.jsonl": "life_guide",
    "additional_cases.jsonl": "additional",
}
GLOSSARY = "financial_glossary_readable.pdf"
LIFE_GUIDE = "financial_life_guide.pdf"


class Corpus:
    def __init__(self, pages: list[dict]):
        self.pages = {(p["file"], p["page"]): p["text"] for p in pages}
        self.text_layer = {(p["file"], p["page"]): p.get("text_layer", p["text"]) for p in pages}
        self.page_rows = {(p["file"], p["page"]): p for p in pages}
        self.files = {p["file"] for p in pages}
        self.n_pages = Counter(p["file"] for p in pages)
        self.versions = {}  # standard-terms version -> file
        for p in pages:
            if p["path"].startswith("standard_terms/") and p["page"] == 1:
                m = re.search(r"버전:\s*(\d+)", p["text"])
                self.versions[m.group(1)] = p["file"]
        self.glossary_terms = {}  # dicId -> term
        for page in range(20, self.n_pages[GLOSSARY] + 1):
            for line in self.pages[(GLOSSARY, page)].splitlines():
                m = re.match(r"(.+?) / 용어 설명 / .*dicId=(\d+)", line)
                if m:
                    self.glossary_terms[m.group(2)] = m.group(1).strip()

    def lines(self, file: str, pages) -> list[tuple[int, str]]:
        return [(pg, line) for pg in pages for line in self.pages[(file, pg)].splitlines()]

    def glossary_unit(self, dic_id: str) -> tuple[str, list[tuple[int, str]]]:
        """(file, [(page, line)]) of the term heading and its definition lines."""
        term = self.glossary_terms[dic_id]
        terms = set(self.glossary_terms.values())
        lines = self.lines(GLOSSARY, range(1, 20))
        starts = [i for i, (_, line) in enumerate(lines) if line.strip() == term]
        # A term listed twice (공매도: dicId 1859, 1865) appears twice in the body; the source list follows
        # body order, so the n-th dicId with that term is the n-th occurrence.
        same = [d for d, t in self.glossary_terms.items() if t == term]
        if len(starts) != len(same):
            raise ValueError(f"glossary term {term!r}: {len(starts)} occurrences, {len(same)} source-list entries")
        start = starts[same.index(dic_id)]
        i = start + 1
        unit = [lines[start]]
        while i < len(lines) and lines[i][1].strip() not in terms and not re.fullmatch(r"\d+", lines[i][1].strip()):
            unit.append(lines[i])
            i += 1
        return GLOSSARY, unit

    def source_list(self, file: str) -> tuple[int, list[str]]:
        """(first page of the "출처 목록", article labels in list order). Every standard-terms PDF ends with
        a source list, one entry per article in body order: "<약관명> / 제N조(제목) / https://…"."""
        first = next(pg for pg in range(1, self.n_pages[file] + 1)
                     if self.pages[(file, pg)].lstrip("0123456789\n").startswith("출처 목록"))
        text = "".join(self.pages[(file, pg)].replace("\n", "") for pg in range(first, self.n_pages[file] + 1))
        labels = [re.match(r"제\s*\d+\s*조(?:\s*의\s*\d+)?", t).group(0)
                  for t in re.findall(r"/ ([^/]+?) / https://", text)]
        return first, [re.sub(r"\s", "", label) for label in labels]

    def article_unit(self, version: str, ordinal: int) -> tuple[str, list[tuple[int, str]]]:
        """(file, [(page, line)]) of the ordinal-th article, from its heading up to the next article heading.
        The last part of kofia-terms-X-V-A is the article's position in the source list, not its number:
        in 02_파생상품계좌설정약관 제10조의2 and 제10조의3 shift it (…-014 = 제12조)."""
        file = self.versions[version]
        list_start, labels = self.source_list(file)
        label = labels[ordinal - 1]
        lines = self.lines(file, range(1, list_start))
        starts = [i for i, (_, line) in enumerate(lines) if re.sub(r"\s", "", line).startswith(label + "(")]
        if len(starts) != 1:
            raise ValueError(f"{file}: {label} (article #{ordinal}) found {len(starts)} times")
        unit = [lines[starts[0]]]
        for pg, line in lines[starts[0] + 1:]:
            if re.match(r"\s*(제\s*\d+\s*조(의\s*\d+)?\s*\(|부\s*칙)", line):
                break
            if not re.fullmatch(r"\d+", line.strip()):
                unit.append((pg, line))
        return file, unit

    def page_unit(self, file: str, page: int) -> tuple[str, list[tuple[int, str]]]:
        return file, self.lines(file, [page])

    def resolve(self, source_id: str) -> tuple[str, list[tuple[int, str]]]:
        if m := re.fullmatch(r"fsc-glossary-(\d+)", source_id):
            return self.glossary_unit(m.group(1))
        if m := re.fullmatch(r"kofia-terms-\d+-(\d+)-(\d+)", source_id):
            return self.article_unit(m.group(1), int(m.group(2)))
        if m := re.fullmatch(r"fss-life-guide-pdf-(\d+)", source_id):
            return self.page_unit(LIFE_GUIDE, int(m.group(1)))
        if m := re.fullmatch(r"(.+)-pdf-(\d+)", source_id):
            return self.page_unit(nfc(m.group(1) + ".pdf"), int(m.group(2)))
        raise ValueError(f"unknown source id {source_id!r}")


# ---- evidence -------------------------------------------------------------------------------------------

SENTENCE_END = re.compile(r"(다|요|음|함|임|됨)\.$|[?!]$")
ITEM_START = re.compile(r"^\s*([①-⑳]|\d+\.\s|[가-하]\.\s|[○•·▶■□◦\-]\s?)")


def bigrams(text: str) -> set[str]:
    s = squash(re.sub(r"[^\w]", "", text))
    return {s[i:i + 2] for i in range(len(s) - 1)}


def sentences(unit: list[tuple[int, str]]) -> list[list[int]]:
    """Group unit line indices into sentences. A sentence ends at a line ending in a sentence end, before a
    line starting a numbered/circled item, or at a page change. Lines are kept whole (they are the quotes)."""
    groups, current = [], []
    for i, (page, line) in enumerate(unit):
        if current and (ITEM_START.match(line) or unit[current[-1]][0] != page):
            groups.append(current)
            current = []
        current.append(i)
        if SENTENCE_END.search(line.rstrip()) or len(line.strip()) < 25:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


def pick_evidence(row: dict, units: list[tuple[str, list[tuple[int, str]]]], max_sentences: int = 4) -> list[dict]:
    """Automatic pick: per must_include item the best-matching sentence, then sentences that add most of the
    reference answer's bigrams. Glossary units are short definitions and are quoted whole.
    Returns [{"file", "page", "quote"}] with quotes = runs of consecutive original lines."""
    picked: list[tuple[int, int]] = []  # (unit index, line index)
    candidates = []  # (unit index, line indices, bigram set)
    for u, (file, lines) in enumerate(units):
        if file == GLOSSARY:
            picked += [(u, i) for i in range(1, len(lines))]
            continue
        for group in sentences(lines):
            text = "".join(lines[i][1] for i in group)
            if len(squash(text)) >= 8:
                candidates.append((u, group, bigrams(text)))
    if candidates:
        chosen = []
        for phrase in row.get("must_include", []):
            want = bigrams(phrase)
            if not want:
                continue
            best = max(candidates, key=lambda c: len(want & c[2]) / len(want))
            if len(want & best[2]) / len(want) >= 0.5 and best not in chosen:
                chosen.append(best)
        want = bigrams(row["reference_answer"])
        covered = set().union(*(c[2] for c in chosen)) if chosen else set()
        while len(chosen) < max_sentences:
            best = max(candidates, key=lambda c: len((want - covered) & c[2]))
            gain = len((want - covered) & best[2])
            if gain < max(3, 0.1 * len(want)):
                break
            chosen.append(best)
            covered |= best[2]
        picked += [(u, i) for u, group, _ in chosen for i in group]
    quotes = []
    for u, i in sorted(set(picked)):
        file, lines = units[u]
        page, line = lines[i]
        if quotes and quotes[-1]["_u"] == u and quotes[-1]["_last"] == i - 1 and quotes[-1]["page"] == page:
            quotes[-1]["quote"] += "\n" + line
            quotes[-1]["_last"] = i
        else:
            quotes.append({"file": file, "page": page, "quote": line, "_u": u, "_last": i})
    return [{k: q[k] for k in ("file", "page", "quote")} for q in quotes]


def quote_matches(corpus: Corpus, ev: dict, layer: str = "text") -> bool:
    texts = corpus.pages if layer == "text" else corpus.text_layer
    page = squash(texts.get((ev["file"], ev["page"]), ""))
    return all(squash(line) in page for line in ev["quote"].splitlines() if squash(line))


def quote_source(corpus: Corpus, ev: dict) -> str:
    """"text" if the quote is in the PDF text layer, "vlm" if it needs the VLM supplement (corpus/pages.jsonl
    appends it after the text layer; its numbers were checked against the page images, golden/review_log.md)."""
    return "text" if quote_matches(corpus, ev, layer="text_layer") else "vlm"


# ---- split ----------------------------------------------------------------------------------------------

def stratum(item: dict) -> tuple:
    key = (item["set"], item["difficulty"])
    if item["set"] == "base_negative":
        key += (item["category"],)
    if item["set"] == "additional":
        key += (item["source_file"],)
    return key


def balance_group(item: dict) -> tuple:
    """Where dev and test must come out equal: per set, and per document in the additional set (PLAN §2.2)."""
    return (item["set"], item.get("source_file")) if item["set"] == "additional" else (item["set"],)


def margins(item: dict) -> list[tuple]:
    """Marginals kept as even as possible after the per-group balance: difficulty per set, context type
    (golden/README.md "Splits"), category for negatives."""
    keys = [("difficulty", item["set"], item["difficulty"]), ("context", item["context_type"])]
    if item["set"] == "base_negative":
        keys.append(("category", item["category"]))
    return keys


def assign_split(items: list[dict], seed: int = SEED) -> None:
    """Shuffle each stratum (seeded) and alternate dev/test. An odd-sized stratum has one extra question; within
    each balance group half of the odd strata give it to dev. Which half is chosen by exhaustive search to keep
    the margins() as even as possible (first best combination in sorted order, so the result is deterministic)."""
    rng = random.Random(seed)
    strata = defaultdict(list)
    for item in items:
        strata[stratum(item)].append(item)
    for key in sorted(strata):
        strata[key] = sorted(strata[key], key=lambda i: i["qid"])
        rng.shuffle(strata[key])
    odd = defaultdict(list)
    for key in sorted(strata):
        if len(strata[key]) % 2:
            odd[balance_group(strata[key][0])].append(key)
    options = [[set(c) for c in combinations(keys, len(keys) // 2)] for _, keys in sorted(odd.items())]

    def imbalance(extra_dev: set) -> int:
        diff = Counter()
        for keys in odd.values():
            for key in keys:
                for m in margins(strata[key][0]):
                    diff[m] += 1 if key in extra_dev else -1
        return sum(abs(v) for v in diff.values())

    best = min(product(*options), key=lambda choice: imbalance(set().union(*choice)))
    extra_dev = set().union(*best)
    for key, group in strata.items():
        first, second = ("dev", "test") if len(group) % 2 == 0 or key in extra_dev else ("test", "dev")
        for n, item in enumerate(group):
            item["split"] = first if n % 2 == 0 else second

    # Context type is not a stratum key (too many tiny strata), so even it out afterwards by swapping a dev and a
    # test question inside one stratum: every stratum count, and so every other margin, stays the same.
    def context_gap() -> int:
        diff = Counter()
        for item in items:
            diff[item["context_type"]] += 1 if item["split"] == "dev" else -1
        return sum(abs(v) for v in diff.values())

    improved = True
    while improved:
        improved = False
        for key in sorted(strata):
            for a in strata[key]:
                for b in strata[key]:
                    if a["split"] != "dev" or b["split"] != "test" or a["context_type"] == b["context_type"]:
                        continue
                    before = context_gap()
                    a["split"], b["split"] = "test", "dev"
                    if context_gap() < before:
                        improved = True
                    else:
                        a["split"], b["split"] = "dev", "test"


# ---- convert --------------------------------------------------------------------------------------------

def source_kind(source_ids: list[str]) -> str:
    kinds = sorted({"glossary" if s.startswith("fsc-glossary") else "terms" if s.startswith("kofia-terms")
                    else "page" for s in source_ids})
    return "+".join(kinds) or "none"


def load_reviewed(path=GOLDEN / "evidence.jsonl") -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return {r["qid"]: r for r in (json.loads(line) for line in f if line.strip())}


def convert(corpus: Corpus, reviewed: dict) -> list[dict]:
    items = []
    for name, set_name in ANSWER_FILES.items():
        with (ANSWERS / name).open(encoding="utf-8") as f:
            rows = [json.loads(line) for line in f if line.strip()]
        for row in rows:
            ids = row.get("expected_source_ids") or []
            units = [corpus.resolve(s) for s in ids]
            review = reviewed.get(row["case_id"])
            evidence = review["evidence"] if review else pick_evidence(row, units)
            files = {nfc(file) for file, _ in units}
            for ev in evidence:
                ev["file"] = nfc(ev["file"])
                if ev["file"] not in files:
                    raise ValueError(f"{row['case_id']}: evidence file {ev['file']} is not a source file")
            # extra_targets: the same content verbatim on a page outside the provided sources (golden/README.md
            # checklist "Same content elsewhere"); counted as a page hit, not quoted as evidence.
            extra = [(nfc(t["file"]), t["page"]) for t in (review or {}).get("extra_targets", [])]
            targets = sorted({(ev["file"], ev["page"]) for ev in evidence} | set(extra))
            sources = [quote_source(corpus, ev) for ev in evidence]
            item = {
                "qid": row["case_id"],
                "split": None,
                "set": set_name,
                "question": row["question"],
                "answerable": bool(ids),
                "expected_behavior": row["expected_behavior"],
                "target_answer": row["reference_answer"],
                "must_include": row.get("must_include", []),
                "must_not_include": row.get("must_not_include", []),
                "evidence": [ev["quote"] for ev in evidence],
                "evidence_pages": [{"file": ev["file"], "page": ev["page"], "source": src}
                                   for ev, src in zip(evidence, sources)],
                "evidence_source": "+".join(sorted(set(sources))) or None,
                "targets": [{"file": f, "page": p} for f, p in targets],
                "source_ids": ids,
                "source_kind": source_kind(ids),
                "difficulty": row["difficulty"],
                "category": row["category"],
                "context_type": (review or {}).get("context_type") or ("text" if ids else None),
                "evidence_reviewed": bool(review),
                "note": (review or {}).get("note", ""),
            }
            if row.get("source_file"):
                item["source_file"] = nfc(row["source_file"])
            if row.get("source_locator"):
                item["source_locator"] = row["source_locator"]
            items.append(item)
    assign_split(items)
    return items


def check(corpus: Corpus, items: list[dict], cfg: dict) -> list[str]:
    """Quotes match their page; every target page is indexed and inside the item's index scope."""
    problems = []
    for item in items:
        scope = cfg["corpus"]["set_scope"][item["set"]]
        for t in item["targets"]:
            page = corpus.page_rows.get((t["file"], t["page"]))
            if page is None or not indexable(page, cfg) or not in_scope(page, cfg, scope):
                problems.append(f"{item['qid']}: target {t['file']} p.{t['page']} is not indexed in scope {scope}")
        if item["answerable"] and not item["evidence"]:
            problems.append(f"{item['qid']}: answerable without evidence")
        for quote, where in zip(item["evidence"], item["evidence_pages"]):
            if not quote_matches(corpus, {**where, "quote": quote}):
                problems.append(f"{item['qid']}: quote does not match {where['file']} p.{where['page']}: {quote[:40]!r}")
    return problems


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--check", action="store_true", help="check only, write nothing")
    p.add_argument("--out", default=str(GOLDEN / "provided.jsonl"))
    args = p.parse_args()
    cfg = load_config(BASELINE)
    corpus = Corpus(load_pages(ROOT / cfg["corpus"]["pages"]))
    items = convert(corpus, load_reviewed())
    problems = check(corpus, items, cfg)

    counts = Counter((i["set"], i["split"]) for i in items)
    print(f"{len(items)} items; split {dict(Counter(i['split'] for i in items))}")
    for s in ANSWER_FILES.values():
        print(f"  {s:14} dev {counts[(s, 'dev')]:3}  test {counts[(s, 'test')]:3}")
    answerable = [i for i in items if i["answerable"]]
    print(f"answerable {len(answerable)}, evidence reviewed {sum(i['evidence_reviewed'] for i in answerable)}, "
          f"quotes {sum(len(i['evidence']) for i in items)}, problems {len(problems)}")
    print(f"evidence source: {dict(Counter(i['evidence_source'] for i in answerable))}")
    for problem in problems:
        print("  " + problem)
    if args.check:
        return
    if problems:
        raise SystemExit("not written: fix the quote problems first")
    with open(args.out, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
