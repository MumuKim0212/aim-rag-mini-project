<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 007: Answer model — gemini-3.1-flash-lite and gemini-3.8-flash vs gemini-3.5-flash-lite (H5)

Status: decided (gemini-3.8-flash meets the written adoption conditions; its latency check fails and is flagged to the owner)
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

Runs `dev_007_lite31`, `dev_007_flash38` (2026-10-21, dev 90, 0 errors). Reused: `dev_004_hybrid`.

| | 3.5-flash-lite (chain) | 3.1-flash-lite | 3.8-flash |
|---|---|---|---|
| Answer score (0–1) | 0.772 | 0.833 | **0.850** |
| Paired vs chain (better / worse / same) | – | 14 / 4 / 72, diff +0.061, CI [+0.011, +0.111], net +10, 18 changed | 14 / 1 / 75, diff +0.078, CI [+0.033, +0.122], net +13, 15 changed |
| Status match / citation on a gold page | 87.8% / 90.5% | 93.3% / 94.6% | 95.6% / 95.9% |
| Score by difficulty (basic / intermediate / advanced / adversarial) | 0.816 / 0.885 / 0.569 / 1.0 | 0.947 / 0.885 / 0.672 / 1.0 | 0.895 / 0.910 / 0.724 / 1.0 |
| Score by set (base_pos / base_neg / life_guide / additional) | 0.867 / 0.825 / 0.650 / 0.683 | 0.883 / 0.825 / 0.800 / 0.800 | 0.917 / 0.875 / 0.700 / 0.817 |
| USD / question (answer) | 0.00115 | 0.00164 (**1.43×**) | 0.00265 (2.31×) |
| Tokens / question | 2,813 | 3,323 | 2,855 |
| Thinking tokens (90 answers) | 0 | 43,215 | 0 |
| p50 / p90 latency | 1.69 s / 3.51 s (2.19 s without the first 12) | 2.68 s / 5.53 s | 3.88 s / 5.40 s (5.21 s without the first 12) |
| Garbled outputs (kana in the answer) | 0 | 0 | 0 |

- 3.1-flash-lite better: ADD-HF06 ADD-HF10 ADD-HP06 ADD-HP10 ADD-IN01 ADD-RP06 ADD-SE06 NEG023 NEG039 POS017 POS058 POS061 POS064 POS078; worse: ADD-PF06 NEG011 NEG022 POS045.
- 3.8-flash better: ADD-HF06 ADD-HP06 ADD-HP10 ADD-IN01 ADD-IN08 ADD-RP06 ADD-SE08 NEG023 NEG025 NEG039 POS052 POS054 POS058 POS064; worse: NEG022.
- `scripts/garble_scan.py` flags 41 of 90 `dev_007_lite31` runs because it compares output tokens with answer characters and 3.1-flash-lite spends thinking tokens at `thinking_level: low`. Checking the answers directly for kana (the failure seen in POS054) finds none in any of the three runs. The scan is not valid for models that think. 3.8-flash and 3.5-flash-lite show no thinking tokens.
- Cost: answers 0.148 USD (3.1-lite) and 0.238 USD (3.8-flash); judge about 0.12 USD each.
- By the rules of section 3: **3.8-flash**: net +13 ≥ 9, 15 changed > 14, CI excludes 0, USD 2.31× ≤ 4× → meets the adoption conditions. **3.1-flash-lite**: not cheaper — with its thinking tokens it costs 1.43× the chain, against the required ≤ 0.9× → not adopted as the cheap option, although its score gain (+0.061, CI excludes 0) is also real. **Latency check**: 3.8-flash has p90 5.2 s without warm-up (cap 3.0 s) and p50 3.9 s; the check is not met.

## 6. Decision and notes

- Decision: **gemini-3.8-flash is adopted as the answer model** under the written conditions (score, CI, cost). The latency check is **not** met (p90 5.2 s vs 3.0 s); section 3 words it as "checked", not as a blocking condition, so the rule alone does not reject it. This is flagged for the project owner, who may revert to `gemini-3.5-flash-lite` (0.772, p90 2.2 s) or choose differently.
- Why, with question IDs: the gain over the chain is on advanced questions (0.569 → 0.724), over-abstention and negative handling (ADD-HF06 ADD-HP06 ADD-HP10 ADD-IN01 NEG023 NEG025 NEG039 improved; only NEG022 worse), and 3.8-flash does not use thinking tokens at `low`, so it is a model effect. H5 (small gap on basic, larger on advanced and negative) is partly supported: basic 0.816 → 0.895, advanced 0.569 → 0.724; `base_negative` 0.825 → 0.875.
- Cost and time: +0.0015 USD per question (answer), +1.7–1.9 s median latency. Over 90 questions that is +0.14 USD.
- What the criteria missed: the latency bullet was ambiguous (check or gate), the `scripts/garble_scan.py` heuristic fails for thinking models, and "cheaper" 3.1-flash-lite turned out dearer than 3.5-flash-lite because of thinking tokens. Nothing was changed after the results. The score of 3.8-flash vs 3.1-flash-lite (0.850 vs 0.833) was not compared directly and is not claimed.

## 8. Addendum — owner decision (2026-10-21, after the results above)

- The project owner ordered `gemini-3.6-flash` as the answer model ("3.6 flash로 그냥 컨펌하고 해"), a model that was not a candidate of this card and that is also the judge model (`configs/baseline.yaml` `judge.model`). This overrides the section 6 decision for the answer model; the results above are unchanged.
- Consequence recorded here: the judge grades answers written by the same model, which can favour them (self-preference). The judge stays `gemini-3.6-flash` and `judge_v1` as everywhere else, because changing it would invalidate every graded run. To be stated as a limitation in EVALUATION.md.
- Measured for the record and as the answer baseline of card 008: `configs/007-flash36.yaml`, experiment `dev_007_flash36` (same chain, `thinking_level: low`). No adopt criteria apply; the result is reported against `dev_004_hybrid` and `dev_007_flash38`.
