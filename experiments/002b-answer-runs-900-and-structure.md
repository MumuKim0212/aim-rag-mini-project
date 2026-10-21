<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 002b: Answer runs — 900/112 alone and structure + 900/112

Status: decided (B adopted by the owner on 2026-10-21, not by the adopt rule)
Date: 2026-10-21

## 1. Hypothesis

- Change: two candidates against the baseline `dev_000_baseline` (Recursive 800/100):
  - A `configs/001b-chunk900.yaml`: Recursive 900/112 (best chunk size at the retrieval level, cards 001–001c).
  - B `configs/002b-structure-900.yaml`: structure units for the glossary and the 15 standard terms (card 002) and Recursive 900/112 for all other documents. B differs from A only in how the glossary and terms are cut, so B − A is the effect of structure units on top of 900.
- Gate waiver: the headroom gates of cards 001b (11 ≤ 14) and 002 (8 ≤ 14) failed. The project owner waived them on 2026-10-21 ("ㅇㅇ 진행해", after being told the cost, about 0.5 USD, and that the answer effect is unmeasured). This card is the record of that waiver. No other gate is waived.
- Failure it targets: evidence missing from the context (25 of the 32 dev failures with a gold page, PROCESS.md §6).
- Expected effect: from the retrieval runs, A improves `evid@5` for 18 questions and worsens 4; structure units improve the four glossary misses. Whether answers get better is what this card measures; the retrieval numbers say nothing about it.
- Prerequisite done before the runs: the answer step shows a unit that runs over a page break with all its pages (`p.3-4`) and `citation_on_target` counts every page of a cited unit (`src/rag/rag.py`, `src/rag/judge.py`, test `test_answer_step_shows_every_page_of_a_unit`). Outputs for single-page chunks are unchanged, so the baseline run stays comparable.

## 2. Measurement

- Baseline run (reused, not rerun): `dev_000_baseline`; its rerun `dev_000_baseline_r2` shows the noise (14 of 90 answers changed, net −8 with a CI that excluded 0).
- Metric: judge score 0/1/2 per question (`prompts/judge_v1.md`, `gemini-3.6-flash`), paired per question (`scripts/compare.py`), plus `status_ok`, `citation_on_target`, retrieval metrics, tokens, USD, latency.
- Split: dev, all 90 questions. Answer model `gemini-3.5-flash-lite`, prompt `answer_v1`, k=5, `gemini-embedding-2`: all as the baseline. One run per candidate.
- Garbled outputs (`scripts/garble_scan.py`) are counted and reported for every run; they are not removed from the scores.
- Not looked at: test split, self-written golden set.

## 3. Go/no-go criteria (written before results)

- A candidate is adoptable if, paired against `dev_000_baseline`: net wins (better − worse) ≥ 9, more than 14 questions changed, the 95% CI of the score difference excludes 0, tokens per question ≤ 1.3× baseline (≤ 3,790), p90 latency ≤ 3.0 s (the baseline is 2.07 s).
- Choice: if only one candidate is adoptable, it is adopted. If both are, the one with the higher mean score; if within 0.01 the one with fewer tokens per question. If neither is adoptable, the baseline 800/100 stays and the result is reported as "no adoptable change at the answer level" — the retrieval gains did not turn into measurable answer gains on dev.
- B vs A is compared with the same paired method and reported, but it only decides between two adoptable candidates by the rule above.
- A result is not reported as an improvement when the score difference is inside the noise (fewer than 15 changed questions or net wins < 9), even if the CI excludes 0.

## 4. LLM budget

- Answers 90 + judge 90 for each of A and B: 360 calls, about 0.46 USD. Index for B and its retrieval-only run: embeddings only (about 0.14 USD).
- Calls so far in the project: 826 → 1,186 after this card (submission/PROCESS.md ledger).

## 5. Results

Runs `dev_001b_chunk900` (A) and `dev_002b_structure900` (B), dev 90, 0 errors, 2026-10-21. Baseline `dev_000_baseline`.

| | Baseline 800/100 | A: 900/112 | B: structure + 900 |
|---|---|---|---|
| Answer score (0–1) | 0.722 | 0.717 | **0.756** |
| Fully correct | 51 (56.7%) | 51 (56.7%) | 52 (57.8%) |
| Paired vs baseline (better / worse / same) | – | 10 / 9 / 71, diff −0.006, CI [−0.072, +0.061] | 13 / 11 / 66, diff +0.033, CI [−0.033, +0.106] |
| Net wins / changed questions | – | +1 / 19 | +2 / 24 |
| Status match (`status_ok`) | 82.2% | 83.3% | 92.2% |
| Citation on a gold page | 81.1% | 86.5% | 91.9% |
| `evid@5` (74 gold questions) | 0.697 | 0.771 | 0.838 (24 up / 4 down) |
| Context chars | 3,064 | 3,428 | 2,700 |
| Tokens / question | 2,916 | 3,155 (1.08×) | 2,622 (0.90×) |
| USD / question (answer) | 0.00116 | 0.00123 | 0.00107 |
| p90 latency | 2.07 s | 1.89 s | 1.88 s |
| Garbled outputs (`garble_scan`) | 2 runs in earlier scans (POS054) | 1 (POS013, abstained) | 0 |

- By set (score): base_positive 0.683 / 0.717 / 0.817; base_negative 0.800 / 0.725 / 0.800; life_guide 0.750 / 0.700 / 0.700; additional 0.700 / 0.717 / 0.683.
- A better than baseline: ADD-HF06 ADD-HF07 ADD-IN10 ADD-SE04 NEG037 NEG039 POS001 POS021 POS052 POS061; worse: ADD-HP10 ADD-RP07 ADD-SE06 NEG009 NEG013 NEG019 POS044 POS064 POS070.
- B better than baseline: ADD-HF06 ADD-IN10 ADD-SE04 NEG025 NEG037 NEG039 POS001 POS006 POS013 POS021 POS052 POS058 POS061; worse: ADD-HP10 ADD-RP01 ADD-RP07 ADD-SE03 ADD-SE06 NEG009 NEG013 POS022 POS057 POS064 POS074.
- B vs A: 9 better / 6 worse / 75 same, diff +0.039, CI [−0.011, +0.100], net +3.
- The baseline rerun changed 14 questions with net −8; both candidates changed about as many questions as that and their nets (+1, +2) are far smaller.

## 6. Decision and notes

- Rule outcome: **neither candidate is adoptable** (net wins +1 and +2 against the required 9; CIs include 0; changed questions 19 and 24 are above 14 but the net is inside the noise). By the rule the baseline 800/100 stays: the retrieval gains did not turn into a measurable answer gain on dev.
- What the data does show: B has the highest point estimate of the three (0.756 vs 0.722 and 0.717), the best status match (92.2% vs 82.2%) and citation accuracy (91.9% vs 81.1%), the shortest context, 10% fewer tokens and no garbled output; it does not look worse than the baseline on any measure. A does not improve the score and costs 8% more tokens. These are secondary measures not named in the criteria, and the score difference is inside the noise, so they support "B is not worse and is cheaper", not "B is more accurate".
- Where B's gain sits: `base_positive` 0.683 → 0.817 (glossary and terms questions POS001 POS006 POS013 POS021 POS052 POS058 improved, POS022 POS057 POS074 got worse). `additional` and `life_guide` did not improve although they use the 900 splitter, consistent with A.
- Using B as the improved RAG (T2) is a choice by point estimate and cost, not by the adopt rule; it needs the project owner's decision and must be stated as such in EVALUATION.md. The test run (T1 vs T2) is the one confirmation.
- **Owner decision (2026-10-21): candidate B is adopted as the improved RAG chain.** Later cards use `configs/002b-structure-900.yaml` as their base and compare against `dev_002b_structure900`. The adopt rule was not met; this is a choice by point estimate and cost.\n- What the criteria missed: nothing was changed after the results. With 90 dev questions and a rerun noise of 14 changed questions, an answer-level gain of +0.03 (about 3 questions) cannot be separated from noise; the retrieval-level evidence is the stronger part of the case for B.
