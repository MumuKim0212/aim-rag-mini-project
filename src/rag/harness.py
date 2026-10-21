"""Batch run, grading, evaluation, and the comparison report. scripts/ are thin CLIs over these functions,
so every teammate runs, scores, and summarizes experiments the same way.

Flow per experiment (names: config.experiment_name):
    run_experiment      golden questions -> system -> out/runs.db            (resumable)
    grade_experiment    runs -> judge -> out/grades/<experiment>.jsonl       (resumable)
    evaluate_experiment runs + grades -> results/<experiment>/{summary.json, metrics.jsonl, grades.jsonl[, runs.jsonl]}
    build_report        results/*/summary.json -> results/SUMMARY.md, out/report.html
"""

import html
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from evalkit import load_jsonl
from evalkit.metrics import context_metrics, ranked_metrics
from evalkit.runlog import RunLog

from . import ROOT, cost, judge
from .config import settings
from .golden import GOLDEN_DIR, behavior_of, load_golden, scope_of
from .repro import environment
from .retrieval import index_dir
from .systems import build_system

DB = ROOT / "out" / "runs.db"
GRADES_DIR = ROOT / "out" / "grades"
RESULTS_DIR = ROOT / "results"
REPORT_HTML = ROOT / "out" / "report.html"
BASELINE_NAME = "000_baseline"


class SplitLocked(RuntimeError):
    pass


def guard_test(name: str, final: bool) -> None:
    """Test numbers are produced once, at workflow step 8 (CLAUDE.md). Callers pass --final explicitly."""
    if name.startswith("test") and not final:
        raise SplitLocked(f"{name}: the test split is locked until workflow step 8; pass --final then")


def _write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def _mean(values):
    values = [v for v in values if v is not None]
    return round(statistics.fmean(values), 4) if values else None


def _quantile(values, q):
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    return round(values[min(len(values) - 1, int(q * len(values)))], 3)


# ---------------------------------------------------------------- run

def run_experiment(cfg: dict, split: str, *, experiment: str, sets=None, limit: int | None = None,
                   retrieval_only: bool = False, final: bool = False, db: Path = DB,
                   golden_dir: Path = GOLDEN_DIR, system=None) -> dict:
    guard_test(split, final)
    items = load_golden(split=split, sets=sets, golden_dir=golden_dir)
    if not items:
        raise ValueError(f"no golden items for split={split!r} sets={sets!r} in {golden_dir}")
    log = RunLog(db)
    done = log.done_qids(experiment)
    todo = [i for i in items if i["qid"] not in done][:limit]
    system = system or build_system(cfg)
    run_config = {**cfg, "environment": environment(), "retrieval_only": retrieval_only}

    def one(item):
        scope = scope_of(item, cfg)
        start = time.perf_counter()
        try:
            if retrieval_only:
                steps = {"calls": []}
                units = system.retrieve(item["question"], scope, steps)
                result = {"status": "retrieval_only", "context": units, "n_searches": 1, "n_llm_calls": 0,
                          "steps": steps,
                          "searches": [{"query": item["question"], "chunk_ids": [u["chunk_id"] for u in units]}]}
            else:
                result = system.run(item["question"], scope)
        except NotImplementedError:
            raise
        except Exception as e:  # one failing question must not stop the batch; rerun resumes it
            result = {"status": "error", "error": f"{type(e).__name__}: {e}"}
        result.setdefault("latency_s", round(time.perf_counter() - start, 3))
        calls = cost.calls_of(result.get("steps"))
        result.setdefault("input_tokens", sum(c["input_tokens"] for c in calls))
        result.setdefault("output_tokens", sum(c["output_tokens"] for c in calls))
        result.setdefault("n_llm_calls", sum(1 for c in calls if c.get("kind") != "embedding"))
        result.update(system=cfg["system"], config=run_config, question=item["question"])
        log.save(result, experiment=experiment, qid=item["qid"])
        return result["status"]

    statuses = {}
    with ThreadPoolExecutor(max_workers=cfg["run"]["concurrency"]) as pool:
        futures = [pool.submit(one, item) for item in todo]
        try:
            for future in as_completed(futures):
                status = future.result()
                statuses[status] = statuses.get(status, 0) + 1
        except BaseException:
            for f in futures:
                f.cancel()
            raise
    return {"experiment": experiment, "skipped_done": len(done), "ran": len(todo), "statuses": statuses}


# ---------------------------------------------------------------- grade

def grade_experiment(experiment: str, *, suffix: str = "", final: bool = False, db: Path = DB,
                     golden_dir: Path = GOLDEN_DIR, grades_dir: Path = GRADES_DIR, grade_fn=None) -> dict:
    """Grade the latest run per question. `suffix` writes a separate file (e.g. "__regrade1" for noise (b))."""
    guard_test(experiment, final)
    grade_fn = grade_fn or judge.grade
    items = {i["qid"]: i for i in load_golden(golden_dir=golden_dir)}
    runs = [r for r in RunLog(db).latest(experiment) if r["status"] != "retrieval_only"]
    path = Path(grades_dir) / f"{experiment}{suffix}.jsonl"
    graded = {r["qid"] for r in load_jsonl(path)} if path.exists() else set()
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("a", encoding="utf-8") as f:
        for run in runs:
            if run["qid"] in graded:
                continue
            judge_cfg = run["config"]["judge"]
            row = {"qid": run["qid"], "run_id": run["run_id"], **grade_fn(items[run["qid"]], run, run["config"]),
                   "judge_model": judge_cfg["model"], "judge_prompt": judge_cfg["prompt"],
                   "created_at": datetime.now().isoformat(timespec="seconds")}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            n += 1
    return {"grades": str(path), "graded_now": n, "already_graded": len(graded)}


# ---------------------------------------------------------------- evaluate

def question_metrics(item: dict, run: dict, prices: dict) -> dict:
    row = {"qid": item["qid"], "set": item["set"], "status": run["status"]}
    context = run.get("context") or []
    if item.get("targets"):
        row.update(context_metrics(item, context))
        row.update(ranked_metrics(item, context))
        first = (run.get("steps") or {}).get("first_context") if isinstance(run.get("steps"), dict) else None
        if first is not None:
            row.update({f"first_{k}": v for k, v in context_metrics(item, first).items()})
    if run["status"] != "retrieval_only":
        row["status_ok"] = judge.status_ok(item, run)
        row["behavior_group"] = behavior_of(item)[0]
        row.update({f"citation_{k}": v for k, v in judge.citation_check(item, run).items()})
    run_cost = cost.totals(cost.calls_of(run.get("steps")), prices)
    row.update(usd=round(run_cost["usd"], 6), input_tokens=run.get("input_tokens"),
               output_tokens=run.get("output_tokens"), thinking_tokens=run_cost["thinking_tokens"],
               n_llm_calls=run.get("n_llm_calls"), n_searches=run.get("n_searches"), latency_s=run.get("latency_s"))
    return row


def _index_build_usd(cfg: dict, scopes: set, prices: dict):
    total, found = 0.0, False
    for scope in scopes:
        build = index_dir(cfg, scope) / "build.json"
        if build.exists():
            found = True
            total += cost.totals(json.loads(build.read_text(encoding="utf-8")).get("calls", []), prices)["usd"]
    return round(total, 6) if found else None


def evaluate_experiment(experiment: str, *, with_runs: bool = False, final: bool = False, overwrite: bool = False,
                        db: Path = DB, golden_dir: Path = GOLDEN_DIR, grades_dir: Path = GRADES_DIR,
                        results_dir: Path = RESULTS_DIR, prices: dict | None = None) -> dict:
    guard_test(experiment, final)
    out_dir = Path(results_dir) / experiment
    if (out_dir / "summary.json").exists() and not overwrite:
        raise FileExistsError(f"{out_dir} exists; a folder used in a decision is never overwritten "
                              "(rerun under a new name), otherwise pass --overwrite")
    prices = prices or cost.load_prices()
    log = RunLog(db)
    runs = log.latest(experiment)
    if not runs:
        raise ValueError(f"no runs for {experiment} in {db}")
    errors = len({r["qid"] for r in log.load(experiment) if r["status"] == "error"} - {r["qid"] for r in runs})
    items = {i["qid"]: i for i in load_golden(golden_dir=golden_dir)}
    cfg = runs[0]["config"]

    metrics = [question_metrics(items[r["qid"]], r, prices) for r in runs]
    grades_path = Path(grades_dir) / f"{experiment}.jsonl"
    grades = {g["qid"]: g for g in load_jsonl(grades_path)} if grades_path.exists() else {}
    for m in metrics:
        if m["qid"] in grades:
            m["correctness"] = grades[m["qid"]].get("correctness")

    judge_calls = [c for g in grades.values() for c in g.get("calls", [])]
    run_calls = [c for r in runs for c in cost.calls_of(r.get("steps"))]
    run_cost, judge_cost = cost.totals(run_calls, prices), cost.totals(judge_calls, prices)
    graded = [m for m in metrics if m.get("correctness") is not None]
    with_targets = [m for m in metrics if "page_hit" in m]
    n = len(runs)

    def score_block(rows):
        return {"n": len(rows),
                "correctness_mean": _mean([m["correctness"] / 2 for m in rows if m.get("correctness") is not None]),
                "fully_correct": _mean([int(m["correctness"] == 2) for m in rows if m.get("correctness") is not None]),
                "status_ok": _mean([m.get("status_ok") for m in rows]),
                "page_hit@5": _mean([m.get("page_hit@5") for m in rows])}

    summary = {
        "experiment": experiment,
        "card": cfg.get("card"),
        "split": experiment.split("_", 1)[0],
        "system": cfg["system"],
        "retrieval_only": cfg.get("retrieval_only", False),
        "n_questions": n,
        "n_errors": errors,
        "n_graded": len(graded),
        "compare_to": cfg.get("compare_to") or f"{experiment.split('_', 1)[0]}_{BASELINE_NAME}",
        "changed": cfg.get("changed", {}),
        "description": cfg.get("description"),
        "config_file": cfg.get("config_file"),
        "config_hash": cfg.get("config_hash"),
        "config": settings(cfg),
        "environment": cfg.get("environment"),
        "scores": {
            "correctness_mean": score_block(metrics)["correctness_mean"],
            "fully_correct": score_block(metrics)["fully_correct"],
            "status_ok": _mean([m.get("status_ok") for m in metrics]),
            "citation_in_context": _mean([m.get("citation_in_context") for m in metrics]),
            "citation_on_target": _mean([m.get("citation_on_target") for m in metrics]),
        },
        "by_set": {s: score_block([m for m in metrics if m["set"] == s]) for s in sorted({m["set"] for m in metrics})},
        "retrieval": {k: _mean([m.get(k) for m in with_targets])
                      for k in ("page_hit@5", "mrr", "evid@5", "gold@5", "page_hit", "evid", "chars")},
        "cost": {
            "usd": round(run_cost["usd"], 6),
            "usd_per_question": round(run_cost["usd"] / n, 6),
            "usd_by_model": {k: round(v, 6) for k, v in run_cost["usd_by_model"].items()},
            "judge_usd": round(judge_cost["usd"], 6),
            "index_build_usd": _index_build_usd(cfg, {scope_of(items[r["qid"]], cfg) for r in runs}, prices),
            "input_tokens": run_cost["input_tokens"],
            "output_tokens": run_cost["output_tokens"],
            "thinking_tokens": run_cost["thinking_tokens"],
            "tokens_per_question": round((run_cost["input_tokens"] + run_cost["output_tokens"]) / n, 1),
        },
        "calls": {"llm": run_cost["llm_calls"], "llm_per_question": round(run_cost["llm_calls"] / n, 2),
                  "searches_per_question": _mean([r.get("n_searches") for r in runs]),
                  "judge": judge_cost["llm_calls"]},
        "latency_s": {"p50": _quantile([r.get("latency_s") for r in runs], 0.5),
                      "p90": _quantile([r.get("latency_s") for r in runs], 0.9)},
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str),
                                          encoding="utf-8")
    _write_jsonl(out_dir / "metrics.jsonl", metrics)
    if grades:
        _write_jsonl(out_dir / "grades.jsonl", grades.values())
    if with_runs:
        _write_jsonl(out_dir / "runs.jsonl", log.load(experiment))
    return summary


# ---------------------------------------------------------------- report

COLUMNS = [  # (header, path in summary, format, higher_is_better)
    ("정답 점수", "scores.correctness_mean", "{:.3f}", True),
    ("완전 정답", "scores.fully_correct", "{:.1%}", True),
    ("대응 일치", "scores.status_ok", "{:.1%}", True),
    ("인용 정확", "scores.citation_on_target", "{:.1%}", True),
    ("page_hit@5", "retrieval.page_hit@5", "{:.3f}", True),
    ("evid@5", "retrieval.evid@5", "{:.3f}", True),
    ("gold@5", "retrieval.gold@5", "{:.2f}", True),
    ("문맥 evid", "retrieval.evid", "{:.3f}", True),   # what the answer step received; equals evid@5 only when k=5
    ("문맥 글자", "retrieval.chars", "{:.0f}", False),
    ("USD/문항", "cost.usd_per_question", "{:.5f}", False),
    ("토큰/문항", "cost.tokens_per_question", "{:.0f}", False),
    ("LLM 호출/문항", "calls.llm_per_question", "{:.2f}", False),
    ("p50 s", "latency_s.p50", "{:.2f}", False),
    ("p90 s", "latency_s.p90", "{:.2f}", False),
]


def _get(summary: dict, path: str):
    value = summary
    for key in path.split("."):
        value = value.get(key) if isinstance(value, dict) else None
    return value


def _fmt(value, fmt):
    return "–" if value is None else fmt.format(value)


def load_summaries(results_dir: Path = RESULTS_DIR, include_test: bool = False) -> list[dict]:
    summaries = []
    for path in sorted(Path(results_dir).glob("*/summary.json")):
        s = json.loads(path.read_text(encoding="utf-8"))
        if include_test or s.get("split") != "test":
            summaries.append(s)
    return summaries


def _changed_text(s: dict) -> str:
    if not s.get("changed"):
        return "기준 설정"
    return ", ".join(f"{k}: {v['from']} → {v['to']}" for k, v in s["changed"].items())


def build_report(results_dir: Path = RESULTS_DIR, md_path: Path | None = None, html_path: Path = REPORT_HTML,
                 include_test: bool = False, final: bool = False) -> dict:
    if include_test:
        guard_test("test", final)
    summaries = load_summaries(results_dir, include_test)
    by_name = {s["experiment"]: s for s in summaries}
    md_path = md_path or Path(results_dir) / "SUMMARY.md"

    def delta(s, path, fmt):
        base = by_name.get(s.get("compare_to"))
        a, b = _get(base, path) if base and base is not s else None, _get(s, path)
        if a is None or b is None:
            return None
        return b - a

    # Markdown (rendered on GitHub)
    head = "| 실험 | 카드 | 변경 | n | " + " | ".join(c[0] for c in COLUMNS) + " | 비용 USD | 기준 |"
    lines = ["# 실험 결과 요약", "", f"생성: {datetime.now().isoformat(timespec='seconds')} · "
             "`python scripts/report.py`로 다시 만든다. 괄호는 기준(compare_to) 대비 차이.", "",
             head, "|" + "---|" * (len(COLUMNS) + 6)]
    for s in summaries:
        cells = []
        for header, path, fmt, _ in COLUMNS:
            d = delta(s, path, fmt)
            cell = _fmt(_get(s, path), fmt)
            cells.append(cell + (f" ({'+' if d >= 0 else ''}{fmt.format(d)})" if d not in (None, 0) else ""))
        lines.append(f"| {s['experiment']} | {s.get('card') or '–'} | {_changed_text(s)} | {s['n_questions']} | "
                     + " | ".join(cells) + f" | {_fmt(_get(s, 'cost.usd'), '{:.4f}')} | {s.get('compare_to') or '–'} |")
    Path(md_path).write_text("\n".join(lines) + "\n", encoding="utf-8")

    # HTML (local, sortable)
    rows = []
    for s in summaries:
        tds = []
        for header, path, fmt, better in COLUMNS:
            value, d = _get(s, path), delta(s, path, fmt)
            cls = "" if d in (None, 0) else ("up" if (d > 0) == better else "down")
            sub = f"<small>{'+' if d > 0 else ''}{fmt.format(d)}</small>" if d not in (None, 0) else ""
            tds.append(f'<td class="num {cls}" data-v="{"" if value is None else value}">{_fmt(value, fmt)}{sub}</td>')
        rows.append(f"<tr><td>{html.escape(s['experiment'])}</td><td>{html.escape(str(s.get('card') or '–'))}</td>"
                    f"<td>{html.escape(_changed_text(s))}</td><td class='num' data-v='{s['n_questions']}'>"
                    f"{s['n_questions']}</td>{''.join(tds)}</tr>")
    headers = "".join(f"<th>{html.escape(h)}</th>" for h in ["실험", "카드", "변경", "n"] + [c[0] for c in COLUMNS])
    Path(html_path).parent.mkdir(parents=True, exist_ok=True)
    Path(html_path).write_text(HTML_TEMPLATE.format(headers=headers, rows="\n".join(rows),
                                                    created=datetime.now().isoformat(timespec="seconds")),
                               encoding="utf-8")
    return {"experiments": len(summaries), "markdown": str(md_path), "html": str(html_path)}


HTML_TEMPLATE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>RAG 실험 비교</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 24px; color: #222; }}
table {{ border-collapse: collapse; font-size: 13px; }}
th, td {{ border-bottom: 1px solid #ddd; padding: 6px 10px; text-align: left; vertical-align: top; }}
th {{ cursor: pointer; background: #f6f6f6; position: sticky; top: 0; }}
td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
td small {{ display: block; color: #666; }}
td.up small {{ color: #1a7f37; }} td.down small {{ color: #c62828; }}
</style></head><body>
<h1>RAG 실험 비교</h1>
<p>생성 {created}. 작은 숫자는 기준(compare_to) 대비 차이(초록 = 나아짐, 빨강 = 나빠짐). 머리글을 누르면 정렬된다.
잡음보다 작은 차이는 결과로 해석하지 않는다(submission/PROCESS.md 4절).</p>
<table id="t"><thead><tr>{headers}</tr></thead><tbody>
{rows}
</tbody></table>
<script>
document.querySelectorAll("#t th").forEach((th, i) => th.onclick = () => {{
  const body = document.querySelector("#t tbody"), rows = [...body.rows];
  const dir = th.dataset.dir = th.dataset.dir === "asc" ? "desc" : "asc";
  const key = r => {{ const c = r.cells[i]; return c.dataset.v !== undefined && c.dataset.v !== "" ? parseFloat(c.dataset.v) : c.textContent; }};
  rows.sort((a, b) => {{ const x = key(a), y = key(b); const r = x > y ? 1 : x < y ? -1 : 0; return dir === "asc" ? r : -r; }});
  rows.forEach(r => body.appendChild(r));
}});
</script></body></html>
"""
