<!--
GUIDE: The operating manual for this RAG experiment. Agents read it before starting each step.
Fill in "Project facts" first; do not edit the steps per project unless the user asks — record
project-specific deviations in submission/PROCESS.md instead.
Keep guide comment in place after filling in.
-->

# RAG experiment workflow

## Project facts

Fill in before step 1. Budget and cost cap are decided now, before any results exist.

| Item | Value |
|---|---|
| Task | Korean RAG agent over financial PDFs: answer with file + page citations, or confirm / correct / abstain / refuse when the documents cannot support an answer. Assignment spec: `docs/assignment.md` |
| Corpus | `01_data/`, 23 PDFs, 490 pages, all with a text layer (no OCR). Scope A "base" = glossary (25 p; p.20– is a URL source list, not content) + 15 standard terms (117 p, `제N조` structure). Scope B "full" = A + life guide (43 p, charts/tables) + 6 additional (348 p; housing_pension has 243 images). Base-set negatives assume scope A only |
| Models | Gemini stable models only (no preview, no limited-access 2.5). Answer candidates: `gemini-3.1-flash-lite`, `gemini-3.5-flash-lite`, `gemini-3.8-flash` (baseline). Judge: `gemini-3.6-flash`, fixed. Embedding: `gemini-embedding-2` (baseline), `gemini-embedding-001` (card 006). IDs and prices: `submission/PLAN.md` §4 |
| LLM call budget | No fixed number; minimize. Every call goes into the submission/PROCESS.md ledger. Estimate in `submission/PLAN.md` §6 |
| Cost cap for adopting a change | None fixed. Report cost (USD from tokens × price, per model), tokens, p50/p90 latency, LLM calls and searches next to quality for every compared config |
| Split | Provided 180 questions stratified by set × difficulty (× category for negatives) → dev 90 / test 90. Self-written golden set kept separate, evaluated only at step 8 |
| Deadline | 2026-10-22 (Thu). Schedule and cut order: `submission/PLAN.md` §9 |
| Outward side effects to disable | LangSmith tracing if a `.env` enables it — force `LANGSMITH_TRACING=false` in-process for batch runs |

Project deviations from the steps below (also in submission/PROCESS.md §0):
- The assignment requires chunking, retrieval, and RAG-vs-agent comparisons regardless of triage. Chunking and retrieval comparisons (cards 001–006) are reported from LLM-free metrics; their answer runs happen only if the headroom gate passes. Cards 007 (answer model) and 008 (agent) change the answer step, so no LLM-free proxy exists; they always get an answer run, each with a card.
- The baseline RAG uses the same answer prompt as the agent's generate node (`prompts/answer_v1.md`), so card 008 measures structure, not instructions.
- Runs are shared through `results/<experiment>/` (see `results/README.md`); `out/runs.db` stays local.

## Working rules

Apply to every step. The irreversible ones are repeated in `CLAUDE.md`.

- **Gate answer runs.** Before an answer run, do the LLM-free comparison and the headroom check (`evalkit/headroom.py`). If upside minus risk is not larger than the measured noise, do not run it; record that in the card. Cards 007/008 are the exceptions listed under Project facts.
- **Reuse, don't rerun.** Compare against the existing baseline run instead of running it again.
- **Log every run** with `evalkit/runlog.py`: retrieved ids, the context passed to the answer step, citations, status, tokens, latency.
- **Record cost per call.** Every LLM and embedding call goes through `rag.llm.record_call`, which appends `{node, kind, model, input_tokens, output_tokens, thinking_tokens, seconds}` to `steps["calls"]`; `rag.cost` prices them with `configs/pricing.yaml`.
- **Use the shared harness.** Run, grade, evaluate, and compare only through `scripts/` (commands below). Pipeline changes go into `src/rag/` behind the registered names (`chunking.method`, `retrieval.method`, `system`), selected by config.
- **Index scope.** Base sets (POS001–060, NEG001–040) run on scope A only (glossary + standard terms); life-guide and additional sets on scope B. Record the scope in `config`.
- **Export results** to `results/<experiment>/` as `results/README.md` specifies, at the end of each experiment.
- **New experiment = new config + card**, not a new script. `scripts/` holds fixed entry points (build index, run, grade, evaluate, compare); one-off analysis goes to `scratch/` (git-ignored). Promote a scratch analysis to `scripts/` only if the write-up depends on it.
- **Claims need data.** Write a cause only after checking per-question data, and cite question IDs. Mark guesses as guesses.
- **Decisions get a date.** A changed decision goes into `submission/PROCESS.md` §0 with the date and reason; do not silently edit `submission/PLAN.md` criteria after results are seen.

## Commands per step

| Step | Commands |
|---|---|
| 1 | page extraction → `corpus/pages.jsonl`; conversion → `golden/provided.jsonl`; `python -m pytest` |
| 2 | `python scripts/build_index.py --config configs/baseline.yaml` · `python scripts/run.py --config configs/baseline.yaml --split dev` · `python scripts/grade.py --experiment dev_000_baseline` · `python scripts/evaluate.py --experiment dev_000_baseline --with-runs` · `python scripts/report.py` |
| 3 | (a) `run.py ... --name dev_000_baseline_r2`, grade, evaluate; (b) `grade.py --experiment dev_000_baseline --suffix __regrade1`; compare with `python -m evalkit.paired` |
| 4–5 | `results/dev_000_baseline/metrics.jsonl` + `grades.jsonl`; `evalkit.metrics.proxy_check` |
| 6 | variant config → `run.py --retrieval-only` → `evaluate.py` → `python scripts/compare.py dev_000_baseline <variant>_retrieval --metric <proxy>` → `python -m evalkit.headroom ...` → answer run only if gates pass |
| 8 | the same commands with `--split test --final` |

## The eight steps

Each step lists what to do and the exit criteria. Do not start a step before the previous one's exit criteria hold. Record each step in the matching section of `submission/PROCESS.md`.

### 1. Corpus check, golden set, evaluation tools

- Spot-check extraction against the original before indexing: tables, charts, scanned or garbled pages, information that exists only in images (a product color, a chart value). Fixing extraction later means re-indexing everything.
- Build the golden set by `golden/README.md`. Split dev/test now, before building anything.
- Size dev for the decisions it must carry. Almost every decision is made on dev, so dev should not be much smaller than test. In the previous project, 85 answerable dev questions could not show an effect that 195 test questions showed clearly.
- Write the answer judge (different model from the answer model, given the reference answer and evidence quotes, score 0/1/2 with a written reason).

Exit criteria
- [ ] Extraction issues found are listed in submission/PROCESS.md, with what was done about each
- [ ] Every answerable question has verbatim evidence quotes that auto-match the target page text
- [ ] dev/test split fixed and stored with the golden set; test not looked at
- [ ] Judge prompt fixed (changing it later invalidates earlier grades)

### 2. Simplest baseline, end to end

One chunk size, vector search, k=5, a short answer prompt that can abstain ("found=false"), citations mapped from result numbers to file and page in code. No agent, no reranker.

- Log every run with `evalkit/runlog.py`.
- Run dev, judge it, and compute LLM-free retrieval metrics on dev (`evalkit/metrics.py`).

Exit criteria
- [ ] Baseline dev run and grades saved; experiment name recorded in submission/PROCESS.md
- [ ] Retrieval metrics for the baseline on dev saved per question

### 3. Measure noise

Two runs, both on dev with the baseline config:
- (a) Run the identical config again and judge it → total noise (generation + judging).
- (b) Judge the baseline's existing answers again → judge noise alone.

Compare each pair with `evalkit/paired.py`. The number of questions whose score changed is the smallest difference worth acting on.

Changing anything between the two runs (a prompt, k, a model version) does not measure noise. In the previous project the "noise" figure came from two runs with different prompts, so it mixed the prompt effect into the noise.

Exit criteria
- [ ] Noise recorded in submission/PROCESS.md as "(a) X of N changed, (b) Y of N changed"

### 4. Check which retrieval metric tracks answers (LLM-free)

Use the baseline's grades and per-question retrieval metrics (`metrics.proxy_check`). Pick the metric that moves with answer score as the proxy for later LLM-free comparisons. Once two configs have answer runs, also check `metrics.direction_agreement`.

Do not assume page_hit or MRR is the right proxy. With small chunks in the previous project, hybrid search had the best page_hit and MRR but lost on answers; the number of gold-page chunks in the top 5 (gold@5) tracked answers.

Exit criteria
- [ ] Proxy metric chosen, with the numbers that justify it, in submission/PROCESS.md

### 5. Triage dev failures

Classify every dev answer that is not fully correct, using the run log (no rerun needed):

| Bucket | How to tell |
|---|---|
| Retrieval miss | No gold page in the context passed to the answer step |
| Evidence present, answer incomplete | Gold page in context, answer misses or misstates part |
| Over-abstention | Gold page in context, system abstained |
| Data problem | Extraction lost the answer (image-only, broken table), or duplicate content elsewhere |
| Evaluation error | Reference answer wrong, or the judge mis-scored (read the judge's reason) |
| Ambiguous question | Depends on unstated context ("원고가…", "이 사건", "해당 표") |

Exit criteria
- [ ] Counts per bucket, with question IDs, in submission/PROCESS.md
- [ ] The largest bucket named as the bottleneck for step 6

### 6. Improve the bottleneck — one experiment card per change

Copy `experiments/_TEMPLATE.md` to `experiments/NNN-slug.md`. Then, in order:

1. Fill sections 1–4 of the card (hypothesis, measurement, go/no-go criteria, LLM budget) before computing anything you will judge it by.
2. LLM-free comparison on dev with the proxy metric. Measure context length too.
3. Headroom check (`evalkit/headroom.py`) against the baseline's grades:
   - upside: proxy improved and baseline not fully correct
   - risk: proxy worsened and baseline scored above 0
   - If upside − risk ≤ noise, stop: the answer run cannot show a gain. Record the decision.
4. Only if the gates pass: run dev answers, judge, and compare against the existing baseline run with `evalkit/paired.py`.
5. Decide (adopt / reject / inconclusive) against the criteria written in step 1, including the cost cap.

Upside is a ceiling, not a forecast: more context can also distract the answer step.

Exit criteria (per card)
- [ ] Card sections 5–7 filled; decision recorded in submission/PROCESS.md's experiment table and LLM ledger

### 7. Add structure only when triage demands it

Agents, rerankers, and query rewriting cost time and tokens on every question. Add one only when step 5 points at a failure it addresses, and treat it as a step-6 experiment with a card and a cost cap.

Decide its instrumentation before building it, so wins can be attributed:
- Agent with re-search: log the first search and the accumulated context separately, score both with `metrics.context_metrics`, and record whether the answer cites chunks that only re-search found. In the previous project this showed that only 5 of the agent's 9 wins came from re-search.
- Since the first search of an agent equals the baseline search for the same question, compare them directly.

Exit criteria
- [ ] Same as step 6, plus the attribution numbers in the card

### 8. Final test run and write-up

Fix the configuration. Run test once for the baseline and the final system, compare with `evalkit/paired.py`, and write `submission/EVALUATION.md`.

Exit criteria
- [ ] Test run once per system; no change made after seeing test results
- [ ] submission/EVALUATION.md complete; every causal claim cites question IDs; limitations include noise, dev size, and judge reliability (spot-check 10 graded answers by hand)

## Rules of thumb

- A retrieval gain becomes an answer gain only on questions the current setup gets wrong. Count those first.
- A difference smaller than the measured noise is not a result. The same direction in two independent runs is stronger evidence than one run.
- With small chunks, how much of the gold page reaches the answer step matters more than whether the gold page appears at all.
- Report cost next to accuracy: a +0.026 score for 2.3× latency is a trade-off, not a win.
