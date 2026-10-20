<!--
GUIDE: Entry point for every agent session in this repo (loaded on every task, so keep it short).
Holds only: where things are, what to read first per task, and rules whose violation cannot be undone.
Procedure, values, and formats live in the documents listed below — add them there, not here.
Keep guide comment in place after editing.
-->

# Financial-document RAG agent — team repo

A Korean RAG agent over 23 financial PDFs, plus its evaluation loop. Assignment: `docs/assignment.md`. Deadline 2026-10-22.

## Start of every task

1. Read the status table at the top of `submission/PROCESS.md`: current step, who is doing what.
2. Claim your task there before starting: add or update a row with your GitHub username and commit/push only that change to `main` so teammates see it (only when the user asks you to commit). Do not take a task someone else holds. Do the work on a `<github-user>/<task>` branch merged by PR (README "협업").
3. Read the documents for your task type:

| Task | Read first |
|---|---|
| Any experiment or batch run | `docs/WORKFLOW.md` (the current step + "Working rules"), `experiments/_TEMPLATE.md` |
| Golden set, data conversion | `golden/README.md` |
| Exporting or reading results | `results/README.md` |
| Settings, model IDs | `configs/baseline.yaml`, `configs/README.md` (values live only in configs) |
| Prices | `configs/pricing.yaml` |
| Plan, hypotheses, schedule | `submission/PLAN.md` |
| Pipeline code | `src/rag/__init__.py` (what is implemented vs stub), the module docstring, `src/rag/systems.py` (result contract) |
| Prompts | `prompts/` (header comment of each file) |
| evalkit tools | `evalkit/README.md` |

When the task is done, update your status row and record the outcome in the matching section of `submission/PROCESS.md`.

## Where things are

| Path | Contents |
|---|---|
| `submission/` | Deliverables (index: `submission/README.md`): PLAN, AGENT_GRAPH, PROCESS, EVALUATION — Korean |
| `docs/` | `assignment.md` (original spec), `WORKFLOW.md` (8-step procedure, project facts, working rules) |
| `01_data/`, `02_questions/`, `03_answers/` | Provided PDFs, questions, reference answers — read-only |
| `golden/` | Golden sets (converted provided set, self-written set) and review log |
| `experiments/` | One card per experiment |
| `configs/`, `prompts/` | Baseline + variant configs, prices; prompt files (one file per version) |
| `corpus/` | `pages.jsonl`, the committed page extraction everyone chunks from |
| `src/rag/`, `scripts/`, `tests/` | Pipeline code (shared harness implemented, pipeline stages stubbed); fixed entry points; `python -m pytest` |
| `evalkit/` | Run log, metrics, paired comparison, headroom check |
| `results/` | Committed results per experiment + `SUMMARY.md`; `out/` (indexes, `runs.db`, `report.html`) and `scratch/` stay local |

## Rules that cannot be undone if broken

- **Test split once.** Do not compute or look at any test-split number (LLM-free included) before the final setting is fixed (workflow step 8). Do not read the self-written golden set's results before then either.
- **Never index** `02_questions/`, `03_answers/`, or `golden/`.
- **No batch LLM run without a card** whose sections 1–4 were written before results and whose gates passed (`docs/WORKFLOW.md` step 6). Exceptions: baseline (step 2) and noise runs (step 3).
- **Disable tracing before batch runs**: scripts call `rag.env.setup()`, which forces `LANGSMITH_TRACING=false`; any new entry point must call it first.
- **Frozen files stay frozen**: a prompt or golden set used in a run is never edited — create a new version. A `results/<experiment>/` folder used in a decision is never overwritten — rerun under a new name.

Deliverable documents (`submission/`) are written in Korean; agent-facing docs in English.
