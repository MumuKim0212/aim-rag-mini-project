"""Small, dependency-free helpers for evaluating a RAG system without LLM calls.

Modules
- runlog   : SQLite log of every system run (retrieved ids, context, answer, tokens, latency)
- metrics  : retrieval / context metrics against a golden set, and checks for choosing a proxy metric
- paired   : per-question paired comparison with a bootstrap CI (also used to measure noise)
- headroom : before an answer run, count the questions a change could actually fix or break

Run the CLIs from the folder that contains evalkit/, e.g. `python -m evalkit.paired a.jsonl b.jsonl`.
Requires Python 3.10+, standard library only.
"""

import json
from pathlib import Path


def load_jsonl(path, where: dict | None = None) -> list[dict]:
    """Rows of a JSONL file. `where` keeps rows whose fields equal the given values (compared as strings),
    so one results file holding several configs can be filtered, e.g. {"method": "vector"}."""
    with Path(path).open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    if where:
        rows = [r for r in rows if all(str(r.get(k)) == v for k, v in where.items())]
    return rows


def to_map(rows: list[dict], field: str, key: str = "qid") -> dict:
    """{row[key]: row[field]} for rows where the field is present and not None. Later rows win,
    so a file with appended re-grades or reruns yields the latest value per question."""
    return {r[key]: r[field] for r in rows if r.get(field) is not None}


def parse_where(*filter_lists: list[str]) -> dict:
    """CLI helper: ["method=vector"], ["context=chunk5"] -> {"method": "vector", "context": "chunk5"}.
    Later lists override earlier ones, so a shared --where can be refined per file."""
    where = {}
    for filters in filter_lists:
        where.update(f.split("=", 1) for f in filters or [])
    return where
