"""Pages -> chunks. The method is chosen by name from the config (chunking.method), so a new strategy is
a new registered function plus a config variant, not a new script.

Chunk unit (also the evalkit unit):
    {"chunk_id": "<doc>-p<page>-<n>", "source": "<file>", "page": <first page>, "content": "...",
     "pages": [<pages covered>]}

`page` is the page the chunk starts on; a chunk crossing pages lists all of them in `pages`.
The baseline splits each page on its own, so its chunks never cross pages.
"""

import hashlib
from typing import Callable

from langchain_text_splitters import RecursiveCharacterTextSplitter

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


@register("structure")
def structure(pages: list[dict], cfg: dict) -> list[dict]:
    """Glossary: one term + definition; terms: one article (제N조); others: heading + paragraphs (card 002)."""
    raise NotImplementedError("card 002")
