"""Log every system run to SQLite so later analysis does not need a rerun.

One row per run of one question. Store what was retrieved and what was actually passed to the answer
step, not only the answer: questions like "was the gold page in the context?" or "did re-search help?"
are then answered from the log, without calling an LLM.

    from evalkit.runlog import RunLog
    log = RunLog("out/runs.db")
    log.save(result, experiment="dev_baseline", qid="Q001")
    done = log.done_qids("dev_baseline")      # resume an interrupted batch
    runs = log.latest("dev_baseline")         # last non-error run per question

    python -m evalkit.runlog export out/runs.db dev_baseline out/runs_dev_baseline.json
    python -m evalkit.runlog export out/runs.db dev_baseline results/dev_baseline/runs.jsonl  # one run per line

`result` is a dict with any of the COLUMNS below. Keep `context` as the exact list of units
(chunks or pages) given to the answer step, each {chunk_id, source, page, content}, so
evalkit.metrics.context_metrics can score it later.
"""

import json
import sqlite3
import sys
import threading
import uuid
from datetime import datetime
from pathlib import Path

JSON_FIELDS = ("config", "searches", "context", "citations", "steps")
COLUMNS = (
    "system", "config", "question", "answer", "status", "searches", "context", "citations", "steps",
    "n_searches", "n_llm_calls", "input_tokens", "output_tokens", "latency_s", "error",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id        TEXT PRIMARY KEY,
    experiment    TEXT,     -- experiment name, e.g. dev_baseline
    qid           TEXT,     -- golden-set question id
    system        TEXT,     -- rag / agent / ...
    config        TEXT,     -- JSON: chunking, retrieval method, k, models, prompt versions
    question      TEXT,
    answer        TEXT,     -- final answer including the source list
    status        TEXT,     -- answered / abstained / error
    searches      TEXT,     -- JSON [{query, chunk_ids, seconds}] in search order
    context       TEXT,     -- JSON [{chunk_id, source, page, content}] passed to the answer step
    citations     TEXT,     -- JSON [{chunk_id, source, page}] cited by the answer
    steps         TEXT,     -- JSON: intermediate decisions, e.g. an agent's sufficiency judgments
    n_searches    INTEGER,
    n_llm_calls   INTEGER,
    input_tokens  INTEGER,
    output_tokens INTEGER,
    latency_s     REAL,
    error         TEXT,
    created_at    TEXT
)"""


class RunLog:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()  # batch runs usually write from a thread pool

    def _query(self, sql: str, params=()) -> list[sqlite3.Row]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            with conn:  # commits on success
                conn.execute(SCHEMA)
                return conn.execute(sql, params).fetchall()
        finally:
            conn.close()

    def save(self, result: dict, experiment: str, qid: str | None = None) -> str:
        row = {
            "run_id": uuid.uuid4().hex[:12],
            "experiment": experiment,
            "qid": qid,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            **{c: result.get(c) for c in COLUMNS},
        }
        for field in JSON_FIELDS:
            row[field] = json.dumps(row[field], ensure_ascii=False)
        with self._lock:
            self._query(
                f"INSERT INTO runs ({', '.join(row)}) VALUES ({', '.join('?' * len(row))})",
                list(row.values()),
            )
        return row["run_id"]

    def load(self, experiment: str) -> list[dict]:
        rows = [dict(r) for r in self._query(
            "SELECT * FROM runs WHERE experiment = ? ORDER BY created_at, rowid", (experiment,))]
        for row in rows:
            for field in JSON_FIELDS:
                row[field] = json.loads(row[field]) if row[field] else None
        return rows

    def latest(self, experiment: str, include_errors: bool = False) -> list[dict]:
        """Last run per question (a rerun after a failure replaces the failed one)."""
        by_qid = {}
        for row in self.load(experiment):
            if include_errors or row["status"] != "error":
                by_qid[row["qid"]] = row
        return list(by_qid.values())

    def done_qids(self, experiment: str) -> set[str]:
        return {r["qid"] for r in self.latest(experiment)}

    def experiments(self) -> list[tuple[str, int]]:
        return [(r["experiment"], r["n"]) for r in self._query(
            "SELECT experiment, COUNT(*) AS n FROM runs GROUP BY experiment ORDER BY MIN(created_at)")]


def main():
    if len(sys.argv) >= 4 and sys.argv[1] == "export":
        db, experiment = sys.argv[2], sys.argv[3]
        out = sys.argv[4] if len(sys.argv) > 4 else f"runs_{experiment}.json"
        runs = RunLog(db).load(experiment)
        if out.endswith(".jsonl"):  # one run per line: diff-friendly for results/<experiment>/runs.jsonl
            text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in runs)
        else:
            text = json.dumps(runs, ensure_ascii=False, indent=2)
        Path(out).write_text(text, encoding="utf-8")
        print(f"exported {len(runs)} runs -> {out}")
    elif len(sys.argv) == 3 and sys.argv[1] == "list":
        for name, n in RunLog(sys.argv[2]).experiments():
            print(f"{name}\t{n}")
    else:
        print("usage: python -m evalkit.runlog export <db> <experiment> [out.json | out.jsonl]\n"
              "       python -m evalkit.runlog list <db>")
        sys.exit(1)


if __name__ == "__main__":
    main()
