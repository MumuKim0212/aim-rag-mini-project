"""Pages -> chunks. The method is chosen by name from the config (chunking.method), so a new strategy is
a new registered function plus a config variant, not a new script.

Chunk unit (also the evalkit unit):
    {"chunk_id": "<doc>-p<page>-<n>", "source": "<file>", "page": <first page>, "content": "...",
     "pages": [<pages covered>]}

`page` is the page the chunk starts on; a chunk crossing pages lists all of them in `pages`.
The baseline splits each page on its own, so its chunks never cross pages.
"""

import hashlib
import itertools
import re
from pathlib import Path
from typing import Callable

import pymupdf
from langchain_text_splitters import RecursiveCharacterTextSplitter

from . import ROOT

CHUNKERS: dict[str, Callable[[list[dict], dict], list[dict]]] = {}
SEPARATORS = ["\n\n", "\n", ". ", " ", ""]
ARTICLE = re.compile(r"^제\s*\d+조(?:의\d+)?\s*\(")   # "제12조(매매거래 등의 통지)" at the start of a line
GLOSSARY_FILE = "financial_glossary_readable.pdf"
TERMS_DIR = "standard_terms/"
TERM_SIZE = (10.5, 12.0)                                # glossary term lines are set at 11 pt, definitions at 10 pt


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
    splitter = _splitter(cfg)
    chunks = []
    for page in pages:
        for n, text in enumerate(t.strip() for t in splitter.split_text(page["text"])):
            if text:
                chunks.append({"chunk_id": f"{doc_id(page['file'])}-p{page['page']:03d}-{n:02d}",
                               "source": page["file"], "page": page["page"], "content": text,
                               "pages": [page["page"]]})
    return chunks


def _splitter(cfg: dict) -> RecursiveCharacterTextSplitter:
    c = cfg["chunking"]
    return RecursiveCharacterTextSplitter(chunk_size=c["chunk_size"], chunk_overlap=c["chunk_overlap"],
                                          separators=SEPARATORS, keep_separator="end")


def _is_page_number(line: str, page: int) -> bool:
    return line.strip() == str(page)


def _glossary_lines(pdf_path: Path, page: int) -> list[tuple[str, bool]]:
    """(text, is_term_line) for each text line of a glossary page, page number and title dropped."""
    with pymupdf.open(pdf_path) as doc:
        blocks = doc[page - 1].get_text("dict")["blocks"]
    lines = []
    for block in blocks:
        for line in block.get("lines", []):
            spans = [s for s in line["spans"] if s["text"].strip()]
            if not spans:
                continue
            text = "".join(s["text"] for s in line["spans"]).rstrip("\n")
            size = max(s["size"] for s in spans)
            if _is_page_number(text, page) or size > TERM_SIZE[1]:   # page number, page title "금융용어 모음"
                continue
            lines.append((text, TERM_SIZE[0] <= size <= TERM_SIZE[1]))
    return lines


def _groups_glossary(pages: list[dict], cfg: dict) -> list[dict]:
    """One group per term: the term line(s) followed by definition lines, possibly continuing on the next page."""
    groups, current = [], None
    for page in pages:
        previous_was_term = False
        for text, is_term in _glossary_lines(ROOT / cfg["corpus"]["pdf_dir"] / page["path"], page["page"]):
            if is_term and not previous_was_term:      # a term that wraps onto a second line stays one term
                current = {"segments": []}
                groups.append(current)
            previous_was_term = is_term
            if current is None:                        # definition text before any term: keep it, do not drop it
                current = {"segments": []}
                groups.append(current)
            _add_line(current, page["page"], text)
    return groups


def _groups_terms(pages: list[dict]) -> list[dict]:
    """One group per article (제N조(...)); text before the first article (title, preamble) is its own group."""
    groups, current = [], None
    for page in pages:
        for n, text in enumerate(page["text"].split("\n")):
            if n == 0 and _is_page_number(text, page["page"]):
                continue
            if ARTICLE.match(text) or current is None:
                current = {"segments": []}
                groups.append(current)
            _add_line(current, page["page"], text)
    return groups


def _add_line(group: dict, page: int, text: str) -> None:
    if not group["segments"] or group["segments"][-1]["page"] != page:
        group["segments"].append({"page": page, "lines": []})
    group["segments"][-1]["lines"].append(text)


def _chunk_groups(file: str, groups: list[dict], cfg: dict, counters: dict) -> list[dict]:
    """A group that fits chunking.chunk_size is one chunk; a longer one is split per page with the
    baseline splitter, so every chunk keeps the page its text is on."""
    splitter, limit, chunks = _splitter(cfg), cfg["chunking"]["chunk_size"], []

    def emit(text: str, page: int, pages: list[int]) -> None:
        n = counters.get(page, 0)
        counters[page] = n + 1
        chunks.append({"chunk_id": f"{doc_id(file)}-p{page:03d}-{n:02d}", "source": file, "page": page,
                       "content": text, "pages": pages})

    for group in groups:
        texts = ["\n".join(seg["lines"]).strip() for seg in group["segments"]]
        total = "\n".join(t for t in texts if t)
        pages = [seg["page"] for seg in group["segments"]]
        if not total:
            continue
        if len(total) <= limit:
            emit(total, pages[0], pages)
            continue
        for seg, text in zip(group["segments"], texts):
            for part in (t.strip() for t in splitter.split_text(text)):
                if part:
                    emit(part, seg["page"], [seg["page"]])
    return chunks


@register("structure")
def structure(pages: list[dict], cfg: dict) -> list[dict]:
    """Glossary: one term + definition; standard terms: one article (제N조); every other document: the
    baseline Recursive split per page (card 002). Units longer than chunking.chunk_size are split with the
    baseline splitter (chunk_size / chunk_overlap), so those two settings keep their baseline meaning."""
    chunks = []
    for file, group in itertools.groupby(pages, key=lambda pg: pg["file"]):
        file_pages = list(group)
        if file == GLOSSARY_FILE:
            groups = _groups_glossary(file_pages, cfg)
        elif file_pages[0].get("path", "").startswith(TERMS_DIR):
            groups = _groups_terms(file_pages)
        else:
            chunks += recursive(file_pages, cfg)
            continue
        chunks += _chunk_groups(file, groups, cfg, {})
    return chunks
