<!--
GUIDE: How to use evalkit in this project. Add project-specific notes (file locations, wrapper
scripts that call evalkit) under "This project". Do not grow evalkit into a framework: it stays small
and dependency-free so it can be read in one sitting. Project-specific code (retrievers, prompts,
the judge) lives outside evalkit/.
Keep guide comment in place after filling in.
-->

# evalkit

Small, dependency-free tools (Python 3.10+, standard library only) that make most RAG analysis possible without LLM calls. The project's own code does the retrieval, answering, and judging; evalkit logs it, measures it, and compares it.

## Which step uses what

| Workflow step | Tool |
|---|---|
| 2. Baseline | `runlog.RunLog` for every run; `metrics.ranked_metrics` / `metrics.context_metrics` on dev |
| 3. Noise | `paired` on two runs of the same config, and on two gradings of the same answers |
| 4. Proxy metric | `metrics.proxy_check`, later `metrics.direction_agreement` |
| 5. Triage | `RunLog.latest` + `metrics.context_metrics` (gold page in context or not) |
| 6. Experiments | `metrics` for the LLM-free comparison, `headroom` before any answer run, `paired` after |
| 7. Added structure | `metrics.context_metrics` on the first search and on the accumulated context separately |
| 8. Final test | `paired` on test |

## Data contracts

Golden item (`golden/README.md`): `qid`, `targets` [{`file`, `page`}], `evidence` [verbatim quotes], plus `split`, `answerable`, and slicing fields.

Unit (retrieved chunk or page): `{"chunk_id", "source", "page", "content"}`. `source` must use the same file names as the golden `targets` (both are NFC-normalized when compared).

System run result passed to `RunLog.save`: any of `system, config, question, answer, status, searches, context, citations, steps, n_searches, n_llm_calls, input_tokens, output_tokens, latency_s, error`. `context` is the exact list of units given to the answer step.

Grades: JSONL, one row per graded run, with at least `qid` and a score field (default `correctness`, 0/1/2 → use `--max-score 2`). Appending a re-grade is fine; the latest row per `qid` wins.

Metric files for `headroom`: JSONL with `qid` and metric fields. One file may hold several configs; select them with `--before-where` / `--after-where key=value`.

## Wiring it into the project

```python
from evalkit.runlog import RunLog
from evalkit.metrics import context_metrics, ranked_metrics

log = RunLog("out/runs.db")
for item in dev_items:
    if item["qid"] in log.done_qids("dev_baseline"):
        continue                                   # resume an interrupted batch
    result = system.run(item["question"])          # project code: search -> answer
    log.save(result, experiment="dev_baseline", qid=item["qid"])

# LLM-free: score what each run actually passed to the answer step
golden = {g["qid"]: g for g in all_items}
rows = [{"qid": r["qid"], **context_metrics(golden[r["qid"]], r["context"])}
        for r in log.latest("dev_baseline")]
```

## CLI

```bash
python -m evalkit.runlog list out/runs.db
python -m evalkit.runlog export out/runs.db dev_baseline out/runs_dev_baseline.json

# noise: same config twice, or the same answers graded twice
python -m evalkit.paired out/grades_dev_baseline.jsonl out/grades_dev_baseline_rerun.jsonl --max-score 2

# A/B against the existing baseline run
python -m evalkit.paired out/grades_dev_baseline.jsonl out/grades_dev_new.jsonl --max-score 2 --noise 5

# before an answer run
python -m evalkit.headroom --scores out/grades_dev_baseline.jsonl --max-score 2 \
    --before out/context_dev.jsonl --before-where config=chunk5 \
    --after out/context_dev.jsonl --after-where config=page --metric evid_full --noise 5
```

## This project

- `out/runs.db`: local only (git-ignored); each teammate keeps their own.
- `results/<experiment>/`: committed. Every experiment: `summary.json`, `grades.jsonl`, `metrics.jsonl`. Baseline, adopted configs, final test, and cards 007/008 also: `runs.jsonl`, exported with `python -m evalkit.runlog export out/runs.db <experiment> results/<experiment>/runs.jsonl`. Rules: `results/README.md`.
- Experiment names: `<split>_<card>_<variant>`, e.g. `dev_000_baseline`.
