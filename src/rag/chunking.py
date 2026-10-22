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
    chunks = CHUNKERS[method](pages, cfg)
    if cfg["chunking"].get("add_header"):
        chunks = add_header(chunks, cfg)
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


def _size(piece: list[tuple[int, str]]) -> int:
    return sum(len(line) + 1 for _, line in piece)


def _cap(piece: list[tuple[int, str]], max_chars: int) -> list[list[tuple[int, str]]]:
    """Cut a piece still over max_chars (no paragraph mark to cut at) at line ends; a single line over
    max_chars is split with the recursive splitter first. No overlap, so the pieces still add up to the
    article (the header added by add_header carries the article name instead). Pages stay per line."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=max_chars, chunk_overlap=0, separators=SEPARATORS,
                                              keep_separator="end")
    lines = [(page, part) for page, line in piece
             for part in (splitter.split_text(line) if len(line) > max_chars else [line])]
    out, size = [[]], 0
    for page, line in lines:
        if out[-1] and size + len(line) + 1 > max_chars:
            out.append([])
            size = 0
        out[-1].append((page, line))
        size += len(line) + 1
    return out


def _units(file: str, groups: list[list[tuple[int, str]]], max_chars: int | None = None,
           hard_cap: bool = False) -> list[dict]:
    """One chunk per group of (page, line); a group longer than max_chars is cut before paragraph marks. With
    hard_cap (chunking.hard_cap, mixed chunker only), a piece still longer than max_chars is cut at line ends
    (_cap), so no chunk exceeds max_chars; off, the chunks are exactly those of the final chain."""
    chunks, per_page = [], {}
    for group in groups:
        pieces = [group]
        if max_chars and _size(group) > max_chars:
            pieces, size = [[]], 0
            for page, line in group:
                starts = line[:1] in PARAGRAPH_MARKS
                if starts and pieces[-1] and size + len(line) > max_chars:
                    pieces.append([])
                    size = 0
                pieces[-1].append((page, line))
                size += len(line) + 1
            if hard_cap:
                pieces = [part for piece in pieces
                          for part in (_cap(piece, max_chars) if _size(piece) > max_chars else [piece])]
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
    chunking.max_chars cut before a paragraph mark (then at line ends if still over, with chunking.hard_cap); other documents: the
    baseline recursive splitter (card 002). A unit may run over a page break: `page` is where it starts,
    `pages` lists all."""
    max_chars = cfg["chunking"].get("max_chars", DEFAULT_MAX_CHARS)
    by_file: dict[str, list[dict]] = {}
    for page in pages:
        by_file.setdefault(page["file"], []).append(page)
    chunks, others = [], []
    for file, group in by_file.items():
        if file == GLOSSARY:
            chunks += _units(file, _glossary_groups(_lines(group), _glossary_terms(cfg)))
        elif group[0]["path"].startswith("standard_terms/"):
            chunks += _units(file, _article_groups(_lines(group)), max_chars, cfg["chunking"].get("hard_cap", False))
        else:
            others += group
    return chunks + recursive(others, cfg)


HEADING = re.compile(r"제\s?\d+\s?조(?:의\s?\d+)?\s?[(（][^)）\n]*[)）]?")


def add_header(chunks: list[dict], cfg: dict) -> list[dict]:
    """Prefix each chunk with "[document title | p.N(-M) | article]" (card 003). The article is the heading
    the chunk starts with, else the last heading a chunk of the same document started with, so the pieces of
    a cut article keep its name. As in _article_groups, the article number must increase, so a piece that
    starts with "제1조(…)에 따라" after a cut is not taken as a heading. Chunks must come in document order."""
    from .ingest import title_of
    last: dict[str, tuple[tuple[int, int], str]] = {}
    out = []
    for c in chunks:
        body = c["content"].lstrip()
        m = ARTICLE.match(body)
        if m and (int(m[1]), int(m[2] or 0)) > last.get(c["source"], ((0, 0), ""))[0]:
            last[c["source"]] = ((int(m[1]), int(m[2] or 0)), HEADING.match(body).group().strip())
        article = last.get(c["source"], (None, None))[1]
        pages = c.get("pages") or [c["page"]]
        where = f"p.{pages[0]}" + (f"-{pages[-1]}" if pages[-1] != pages[0] else "")
        header = f"[{title_of(c['source'], cfg)} | {where}" + (f" | {article}" if article else "") + "]"
        out.append({**c, "content": f"{header}\n{c['content']}"})
    return out
