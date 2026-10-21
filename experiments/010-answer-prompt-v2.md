<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 010: Answer prompt v2 (aim: as many fully correct answers as possible)

Status: decided by the criteria (v1 stays); v2 adoption is an open owner decision; v3 not tried
Date: 2026-10-21

## 1. Hypothesis

- Change (one variable): answer prompt `prompts/answer_v1.md` → `prompts/answer_v2.md` in the final RAG chain (`configs/010-answer-v2.yaml`: structure + 950/119, hybrid k=5, `gemini-3.6-flash`). v1 stays frozen for T1. The agent's generate node uses the same prompt file, so if v2 is adopted the agent config of T3 follows (`configs/008b-agent-950.yaml` would point to v2).
- Requested by the project owner on 2026-10-21: "fix the prompt and aim for 1.0". A score of 1.0 is a target, not an expectation: the judge changes 3 of 90 grades on a regrade and a rerun changes 14 of 90 answers.
- Failure it targets (the 23 imperfect answers of `dev_001e_chunk950chain`: 5 zero, 18 one, read in full): (1) answers that leave out a part of the question or the conditions, caveats and limits that the evidence states (1-point answers: POS037 POS045 POS047 POS050 POS059 POS076 POS078 ADD-HP02 ADD-HP09 ADD-SE08 ADD-IN04 ADD-IN08 ADD-PF08); (2) over-abstention with partial evidence in context (POS051 POS074 ADD-SE06); (3) refusals without the risk statement (NEG022 NEG023 NEG025); (4) answering instead of asking when the question does not say which account or market (NEG013 NEG014); (5) saying "not in the documents" when it is, or reading a proposal as enforced (POS079 ADD-HF06).
- Honest limit: v2 was written after reading these answers, so the dev result is optimistic for these questions. The unbiased check is the final test (T1 uses v1, T2 uses the adopted prompt).
- Expected effect: fewer 1-point answers and fewer wrong abstentions; risk: longer answers that add content the judge's `must_not_include` forbids, and over-clarifying.

## 2. Measurement

- Baseline run (reused): `dev_001e_chunk950chain` (answers and grades), same retrieval and answer model. Judge fixed (`judge_v1`, `gemini-3.6-flash`). Split: dev, 90 questions, one run. Noise: 14 of 90 changed in a rerun, net −8.
- Metrics: score paired per question; split into the 67 questions that were fully correct before (regressions = how many drop) and the 23 that were not (gains); `status_ok`; by set; answer length (output tokens per question); USD and p90 latency; garbled outputs (kana).
- Not looked at: test split, self-written golden set.

## 3. Go/no-go criteria (written before results)

- v2 is adopted if, paired against `dev_001e_chunk950chain`: net wins ≥ 9, more than 14 questions changed, 95% CI of the score difference excludes 0, no more than 5 of the 67 previously fully correct questions drop below 2, output tokens per question ≤ 1.5× baseline, p90 latency ≤ 5 s. Otherwise v1 stays.
- At most two prompt versions are tried (v2, then v3 only if v2 shows a clear, general failure pattern in the regressions). The target 1.0 does not extend this limit; the loop stops after v3 and the best adopted prompt is frozen before the test.
- A gain inside the noise is described as "not distinguishable".

## 4. LLM budget

- Answers 90 + judge 90 per version (about 0.36 USD). Up to 2 versions.
- Calls so far in the project: 2,640 → 2,820 after v2.

## 5. Results

Run `dev_010_answerv2` (2026-10-21, dev 90, 0 errors, 90 answers + 90 judge, answer 0.296 USD). Baseline `dev_001e_chunk950chain` (prompt v1).

| | v1 (baseline) | v2 |
|---|---|---|
| Answer score (0–1) | 0.844 | **0.861** |
| Fully correct | 67 (74.4%) | 69 (76.7%) |
| Paired vs v1 | – | 8 better / 6 worse / 76 same, diff +0.017, CI [−0.033, +0.072], net +2, 14 changed |
| Status match / citation on a gold page | 94.4% / 94.6% | 96.7% / 96.0% |
| By set (base_pos / base_neg / life_guide / additional) | 0.883 / 0.825 / 0.750 / 0.850 | 0.933 / 0.875 / 0.650 / 0.850 |
| Answer length (characters, mean) | 302 | 404 (1.34×) |
| Tokens / question; USD / question (answer) | 2,882; 0.00265 | 3,376 (1.17×); 0.00329 (1.24×) |
| p50 / p90 latency | 2.60 s / 3.52 s | 3.11 s / 4.34 s |
| Garbled outputs (kana) | 0 | 0 |

- Of the 23 imperfect answers of the baseline (the questions v2 was written from): **8 became fully correct** (POS037 POS045 POS051 NEG013 NEG022 NEG023 NEG025 ADD-IN08) and none got worse; 15 stay imperfect.
- Of the 67 fully correct ones, **6 dropped**: POS057 POS066 POS070 ADD-PF01 (each to 1: the judge names a required point the answer left out), NEG011 (1: clarify without mentioning product and company), NEG037 (0: repeats the dictionary's planned date and does not say to verify the current date).
- Still imperfect after v2 (21): POS047 POS050 POS057 POS059 NEG014 NEG011 NEG037 POS066 POS074 POS076 POS070 POS078 ADD-HP02 POS079 ADD-HP09 ADD-HF06 ADD-SE06 ADD-SE08 ADD-IN04 ADD-PF01 ADD-PF08.
- By the criteria: net +2 (needs 9) → fails; 6 regressions (limit 5) → fails; 14 changed (needs more than 14) → fails. Tokens 1.17× and p90 4.3 s are within the caps.
- Biased evidence: the 8 fixes are on questions v2 was written from (for example all three refusals NEG022 NEG023 NEG025 now carry the risk statement, NEG013 now asks). The 6 drops are on questions it was not written from, and four of them are the same kind of 1-point omission that the rerun noise produces; the 76 unchanged answers and 14 changed ones are the same size as in a plain rerun.

## 6. Decision and notes

- Decision by the criteria: **v1 stays**; v2 is not adopted. v3 is not tried: the pre-registered condition for it (a clear, general failure pattern in the regressions) is not met — the six drops are one-point omissions of different required points and two negative-question details, with no common rule to add.
- Why: +0.017 is inside the noise and the regression limit is exceeded. The target 1.0 is far away: 21 of 90 answers are still imperfect, of which about half are questions whose evidence is not completely in the five retrieved chunks (retrieval, not the prompt) and the rest are strict required-point omissions of the judge.
- Open owner decision: adopt v2 anyway by point estimate (0.861 vs 0.844, status match 96.7% vs 94.4%, the three refusals fixed), at +24% answer cost and +0.8 s p90, as was done for structure + 900, hybrid and 950. The dev gain is optimistic (see above); the test run is the unbiased check. If adopted: `configs/001e-chunk950-chain.yaml` (T2) and `configs/008b-agent-950.yaml` (T3) point to `answer_v2.md`, T1 keeps v1, and PROCESS.md §9 is updated before the test.
