"""Pages -> chunks. The method is chosen by name from the config (chunking.method), so a new strategy is
a new registered function plus a config variant, not a new script.

Chunk unit (also the evalkit unit):
    {"chunk_id": "<doc>-p<page>-<n>", "source": "<file>", "page": <first page>, "content": "...",
     "pages": [<pages covered>]}

`page` is the page the chunk starts on; a chunk crossing pages lists all of them in `pages`.
The baseline splits each page on its own, so its chunks never cross pages.
"""

import hashlib
import re
from typing import Callable

from evalkit.metrics import squash
from langchain_text_splitters import RecursiveCharacterTextSplitter

from . import ROOT
from .ingest import load_pages

CHUNKERS: dict[str, Callable[[list[dict], dict], list[dict]]] = {}
SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


def register(name: str):
    def wrap(fn):
        CHUNKERS[name] = fn
        return fn
    return wrap


def doc_id(file: str) -> str:
    return hashlib.sha1(file.encode("utf-8")).hexdigest()[:8]


def chunk_pages(pages: list[dict], cfg: dict) -> list[dict]:
    method = cfg["chunking"]["method"]
    if method not in CHUNKERS:
        raise KeyError(f"unknown chunking.method {method!r}; registered: {sorted(CHUNKERS)}")
    if cfg["chunking"].get("add_header"):
        raise NotImplementedError("chunking.add_header — card 003")
    chunks = CHUNKERS[method](pages, cfg)
    ids = [c["chunk_id"] for c in chunks]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate chunk_id")
    return chunks


@register("recursive")
def recursive(pages: list[dict], cfg: dict) -> list[dict]:
    """RecursiveCharacterTextSplitter per page with chunking.chunk_size / chunk_overlap (characters)."""
    c = cfg["chunking"]
    splitter = RecursiveCharacterTextSplitter(chunk_size=c["chunk_size"], chunk_overlap=c["chunk_overlap"],
                                              separators=SEPARATORS, keep_separator="end")
    chunks = []
    for page in pages:
        for n, text in enumerate(t.strip() for t in splitter.split_text(page["text"])):
            if text:
                chunks.append({"chunk_id": f"{doc_id(page['file'])}-p{page['page']:03d}-{n:02d}",
                               "source": page["file"], "page": page["page"], "content": text,
                               "pages": [page["page"]]})
    return chunks


GLOSSARY = "financial_glossary_readable.pdf"
GLOSSARY_TERM_MARK = " / 용어 설명 / "     # source-list line: "<term> / 용어 설명 / <url>"
ARTICLE = re.compile(r"제\s?(\d+)\s?조(?:의\s?(\d+))?\s?[(（]")  # headings come as "제11조 (…)" too
PARAGRAPH_MARKS = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
DEFAULT_MAX_CHARS = 1600


def _lines(pages: list[dict]) -> list[tuple[int, str]]:
    """(page, line) over consecutive pages, without the leading page-number line."""
    out = []
    for page in sorted(pages, key=lambda p: p["page"]):
        lines = page["text"].split("\n")
        if lines and lines[0].strip().isdigit():
            lines = lines[1:]
        out += [(page["page"], line) for line in lines]
    return out


def _glossary_terms(cfg: dict) -> list[str]:
    """Terms in body order, read from the glossary's source-list pages (excluded from the index but in the
    corpus). Using them makes the term boundaries exact instead of guessed from line lengths."""
    first, last = cfg["corpus"]["exclude_pages"][GLOSSARY]
    pages = [p for p in load_pages(ROOT / cfg["corpus"]["pages"])
             if p["file"] == GLOSSARY and first <= p["page"] <= last]
    return [line.split(GLOSSARY_TERM_MARK)[0].strip() for p in sorted(pages, key=lambda p: p["page"])
            for line in p["text"].split("\n") if GLOSSARY_TERM_MARK in line]


def _units(file: str, groups: list[list[tuple[int, str]]], max_chars: int | None = None) -> list[dict]:
    """One chunk per group of (page, line); a group longer than max_chars is cut before paragraph marks."""
    chunks, per_page = [], {}
    for group in groups:
        pieces = [group]
        if max_chars and sum(len(line) + 1 for _, line in group) > max_chars:
            pieces, size = [[]], 0
            for page, line in group:
                starts = line[:1] in PARAGRAPH_MARKS
                if starts and pieces[-1] and size + len(line) > max_chars:
                    pieces.append([])
                    size = 0
                pieces[-1].append((page, line))
                size += len(line) + 1
        for piece in pieces:
            text = "\n".join(line for _, line in piece).strip()
            if not text:
                continue
            page = piece[0][0]
            n = per_page.get(page, 0)
            per_page[page] = n + 1
            chunks.append({"chunk_id": f"{doc_id(file)}-p{page:03d}-{n:02d}", "source": file, "page": page,
                           "content": text, "pages": sorted({p for p, _ in piece})})
    return chunks


def _glossary_groups(lines: list[tuple[int, str]], terms: list[str]) -> list[list[tuple[int, str]]]:
    groups, pos = [], 0
    for page, line in lines:
        if pos < len(terms) and squash(line) == squash(terms[pos]):
            groups.append([])
            pos += 1
        if groups:
            groups[-1].append((page, line))
    if pos != len(terms):
        raise ValueError(f"glossary: matched {pos} of {len(terms)} terms in order; stuck at {terms[pos]!r}")
    return groups


def _article_groups(lines: list[tuple[int, str]]) -> list[list[tuple[int, str]]]:
    """Preamble (title, date, version) first, then one group per article. Article numbers must increase,
    so a line like "제12조(...)에 따라" inside a sentence is not taken as a heading."""
    groups, last = [[]], (0, 0)
    for page, line in lines:
        m = ARTICLE.match(line.strip())
        if m and (int(m[1]), int(m[2] or 0)) > last:
            last = (int(m[1]), int(m[2] or 0))
            groups.append([])
        groups[-1].append((page, line))
    return groups


@register("structure")
def structure(pages: list[dict], cfg: dict) -> list[dict]:
    """Glossary: one term + definition; standard terms: one article (제N조), a preamble chunk first, articles over
    chunking.max_chars cut before a paragraph mark; other documents: the baseline recursive splitter (card 002).
    A unit may run over a page break: `page` is where it starts, `pages` lists all."""
    max_chars = cfg["chunking"].get("max_chars", DEFAULT_MAX_CHARS)
    by_file: dict[str, list[dict]] = {}
    for page in pages:
        by_file.setdefault(page["file"], []).append(page)
    chunks, others = [], []
    for file, group in by_file.items():
        if file == GLOSSARY:
            chunks += _units(file, _glossary_groups(_lines(group), _glossary_terms(cfg)))
        elif group[0]["path"].startswith("standard_terms/"):
            chunks += _units(file, _article_groups(_lines(group)), max_chars)
        else:
            others += group
    return chunks + recursive(others, cfg)
