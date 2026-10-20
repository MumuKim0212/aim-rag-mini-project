"""Pages -> chunks. The method is chosen by name from the config (chunking.method), so a new strategy is
a new registered function plus a config variant, not a new script.

Chunk unit (also the evalkit unit):
    {"chunk_id": "<file-hash>-p<page>-<n>", "source": "<file>", "page": <first page>, "content": "...",
     "pages": [<pages covered>]}

`page` is the page the chunk starts on; a chunk crossing pages lists all of them in `pages`.
"""

from typing import Callable

CHUNKERS: dict[str, Callable[[list[dict], dict], list[dict]]] = {}


def register(name: str):
    def wrap(fn):
        CHUNKERS[name] = fn
        return fn
    return wrap


def chunk_pages(pages: list[dict], cfg: dict) -> list[dict]:
    method = cfg["chunking"]["method"]
    if method not in CHUNKERS:
        raise KeyError(f"unknown chunking.method {method!r}; registered: {sorted(CHUNKERS)}")
    return CHUNKERS[method](pages, cfg)


@register("recursive")
def recursive(pages: list[dict], cfg: dict) -> list[dict]:
    """RecursiveCharacterTextSplitter with chunking.chunk_size / chunk_overlap (baseline)."""
    raise NotImplementedError("baseline chunking — PLAN §3.1")


@register("structure")
def structure(pages: list[dict], cfg: dict) -> list[dict]:
    """Glossary: one term + definition; terms: one article (제N조); others: heading + paragraphs (card 002)."""
    raise NotImplementedError("card 002")
