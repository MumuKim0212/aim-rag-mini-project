<!--
GUIDE: What gets committed under results/. One folder per experiment name (results/<experiment>/).
out/runs.db stays local; results/ is how runs are shared and submitted. Files here are written by
scripts/evaluate.py and scripts/report.py — do not hand-edit them; keep this README in sync with
src/rag/harness.py when the summary format changes.
Keep guide comment in place after editing.
-->

# results

One folder per experiment, `results/<experiment>/`, named `<split>_<config name>[_retrieval]` (e.g. `dev_000_baseline`, `dev_004_hybrid_retrieval`). Written by `python scripts/evaluate.py --experiment <name>`; the local `out/runs.db` is never committed.

## Files per experiment

| File | Every experiment | Baseline, adopted configs, final test, cards 007/008 (`--with-runs`) |
|---|---|---|
| `summary.json` | yes | yes |
| `metrics.jsonl` | yes | yes |
| `grades.jsonl` | if graded | yes |
| `runs.jsonl` | – | yes |

- `metrics.jsonl` — one row per question, no LLM: `qid`, `set`, `status`; for questions with gold pages the context metrics (`page_hit`, `gold`, `evid`, `evid_full`, `units`, `chars`) and ranked metrics (`mrr`, `page_hit@k`, `gold@k`, `evid@k`), plus `first_*` for agents; code checks `status_ok`, `behavior_group`, `citation_in_context`, `citation_on_target`; per-question `usd`, tokens, calls, `latency_s`; `correctness` copied from grades.
- `grades.jsonl` — one row per graded run: `qid`, `run_id`, `correctness` (0/1/2), `reason`, judge flags, `calls`, `judge_model`, `judge_prompt`.
- `runs.jsonl` — every logged run of the experiment (`RunLog.load`, errors and reruns included), one per line.

## summary.json

| Key | Contents |
|---|---|
| `experiment`, `card`, `split`, `system`, `retrieval_only` | identity |
| `n_questions`, `n_errors`, `n_graded` | counts (`n_errors` = questions whose only runs failed) |
| `compare_to` | experiment the report diffs against (config meta key; default `<split>_000_baseline`) |
| `changed` | settings that differ from `configs/baseline.yaml`: `{"retrieval.method": {"from": "vector", "to": "hybrid"}}` |
| `description`, `config_file`, `config_hash`, `config` | the full merged settings that produced the runs |
| `environment` | Python, git commit / branch / dirty flag, package versions |
| `scores` | `correctness_mean` (score / 2, 0–1), `fully_correct` (share of 2s), `status_ok`, `citation_in_context`, `citation_on_target` |
| `by_set` | per golden set: `n`, `correctness_mean`, `fully_correct`, `status_ok`, `page_hit@5` |
| `retrieval` | means over questions with gold pages: `page_hit@5`, `mrr`, `evid@5`, `gold@5`, context `page_hit`, `evid`, `chars` |
| `cost` | `usd`, `usd_per_question`, `usd_by_model`, `judge_usd`, `index_build_usd`, input / output / thinking tokens, `tokens_per_question` |
| `calls` | `llm`, `llm_per_question`, `searches_per_question`, `judge` |
| `latency_s` | `p50`, `p90` |

Metrics an experiment did not measure are `null`, never dropped, so summaries stay comparable.

## Comparison views

- `results/SUMMARY.md` — all dev experiments in one table with differences against `compare_to`; committed, readable on GitHub. Regenerate with `python scripts/report.py` after each evaluation.
- `out/report.html` — the same table, sortable, colored by better / worse; local only, open in a browser.
- `python scripts/compare.py <a> <b>` — paired per-question comparison with a 95% CI, plus cost and latency ratios.

## Rules

- Write the experiment card's sections 1–4 before the first file appears here.
- `test_*` folders appear only at workflow step 8 (`--final`); the report leaves them out unless `--include-test --final`.
- `evaluate.py` refuses to overwrite an existing folder. A folder used in a decision is never overwritten; rerun under a new name. `--overwrite` is only for folders nobody has used yet.
