<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 007: Answer model — gemini-3.1-flash-lite and gemini-3.8-flash vs gemini-3.5-flash-lite (H5)

Status: planned
Date: 2026-10-21

## 1. Hypothesis

- Change (one variable): `answer.model` on the adopted chain (structure + 900/112 + hybrid, k=5, `prompts/answer_v1.md`, `thinking_level: low`). Variants `configs/007-lite31.yaml` (`gemini-3.1-flash-lite`, cheaper) and `configs/007-flash38.yaml` (`gemini-3.8-flash`, flash tier). The chain's own answer run `dev_004_hybrid` (`gemini-3.5-flash-lite`) is reused, not rerun.
- Failure it targets: answer-side failures that survive good retrieval (PROCESS.md §6: incomplete answers with all evidence in context, over-abstention, negative-question responses).
- Expected effect (H5, PLAN.md §1): the cheapest model is close to the flash tier on basic questions and the gap shows on advanced and negative questions. Prices (`configs/pricing.yaml`, USD per 1M tokens in/out): 3.1-lite 0.25 / 1.50, 3.5-lite 0.30 / 2.50, 3.8-flash 0.75 / 3.75.
- 007 changes the answer step, so there is no LLM-free proxy and no headroom gate: the answer run is the comparison (PLAN.md §3.2, 2026-10-20 decision).

## 2. Measurement

- Baseline run (reused): `dev_004_hybrid` (answers + grades). Judge fixed: `gemini-3.6-flash`, `judge_v1`.
- Metrics: judge score 0/1/2 paired per question (`scripts/compare.py`), by set and by difficulty (`golden/provided.jsonl` `difficulty`), `status_ok`, `citation_on_target`, tokens (thinking tokens reported separately), USD per question, p50/p90 latency, garbled outputs (`scripts/garble_scan.py`).
- The same `low` thinking level gives different thinking amounts per model (PLAN.md §4.3: 3.1-lite 159 tokens, 3.8-flash 0 in a short test), so a score difference is the effect of model and thinking together and is not split.
- Split: dev, 90 questions, one run per variant. Noise: 14 of 90 changed in a rerun (net −8). Not looked at: test split, self-written golden set.

## 3. Go/no-go criteria (written before results)

- **gemini-3.8-flash (stronger, dearer)** is adopted only if, paired against `dev_004_hybrid`: net wins ≥ 9, more than 14 questions changed, the 95% CI of the score difference excludes 0, and USD per question (answers) ≤ 4× the chain's.
- **gemini-3.1-flash-lite (cheaper)** is adopted if: the score difference is ≥ −0.02, USD per question (answers) ≤ 0.9× the chain's, and its garbled-output count is no larger than the chain's (1).
- If both qualify, the dearer model is chosen (it was required to show a real gain). If only one qualifies, that one. If neither, `gemini-3.5-flash-lite` stays.
- p90 latency ≤ 3.0 s is checked for the chosen model, with the warm-up of the BM25 index (first 12 questions) reported separately as in card 004.
- A difference inside the noise (fewer than 15 changed questions or net wins < 9) is not reported as a gain.

## 4. LLM budget

- Answers 90 + judge 90 per variant = 360 calls. Estimated cost from the chain run's tokens and the prices: 3.1-lite about 0.10 + 0.12 USD, 3.8-flash about 0.25 + 0.12 USD, about 0.6 USD in total.
- Calls so far in the project: 1,366 → 1,726 after this card.

## 5. Results

_..._

## 6. Decision and notes

- Decision: _..._
- Why, with question IDs: _..._
- What the criteria missed, if anything: _..._
