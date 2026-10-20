# configs

- `baseline.yaml` — every setting of the baseline (submission/PLAN.md §3.1). Frozen once the baseline has run.
- `pricing.yaml` — model prices; the only place prices live.
- `<card>-<variant>.yaml` — one file per experiment variant, listing only what it changes.

## Writing a variant

```yaml
# configs/004-hybrid.yaml
base: baseline.yaml
name: 004_hybrid
card: experiments/004-retrieval.md
description: hybrid search, alpha 0.5
retrieval:
  method: hybrid
```

- Meta keys (`name`, `card`, `description`, `compare_to`) are not settings. `compare_to` is the experiment the report diffs against; default `<split>_000_baseline`. Set it when the comparison baseline moved (e.g. `compare_to: dev_001_chunk400`).
- `base` may point to another variant (e.g. after a change was adopted, `base: 001-chunk400.yaml`). The chain is merged top-down.
- `src/rag/config.py` records which keys differ from `baseline.yaml` (`changed`) and a hash of the merged settings (`config_hash`); both go into every run and `summary.json`.
- One variant changes one thing (PLAN §3.2). If `changed` lists more than the card says, fix the file before running.
- Experiment name = `<split>_<name>`, e.g. `dev_004_hybrid`. Names must be unique; a rerun gets a new name (`004_hybrid_r2`).
