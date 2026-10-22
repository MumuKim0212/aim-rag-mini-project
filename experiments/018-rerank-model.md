<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 018: Rerank model with the answer model B fixed, run on the provided test split

Status: decided (R-36 is nominally best on test but its gain over R-lite is below the interpretability floor written in section 3; nothing adopted; sections 1–4 written 2026-10-22 before any run of this card)
Date: 2026-10-22

## 1. Hypothesis

- Change (one variable): the model that does the LLM rerank (Hybrid pool 15 → 5, `rerank_v1`). The answer step is B of card 017 in both runs: `gemini-3.8-flash`, thinking low, `answer_v4`, structure + 950/119, Hybrid, k=5. The rerank thinking is low in both.
  - R-lite `configs/017b-flash38.yaml` (rerank `gemini-3.5-flash-lite`, the setting of the final system T4): run on test as `test_017b_flash38`. Its dev run `dev_017b_flash38` exists; no new dev run is made.
  - R-36 `configs/018-b-rerank-flash36.yaml` (rerank `gemini-3.6-flash`): `test_018_b_rerank_flash36`. No dev run of this setting exists.
- Why test: the owner asked for the provided test questions on 2026-10-22, reading "Test split once" as "once per condition". Each of the two conditions is run once; no repeat, no retuning on the result. The provided test split has already been used for T1–T3 and for T4 (EVALUATION.md §7), so this is the third look at it. If a setting is chosen from these runs, its test number is no longer an unbiased estimate and must be reported that way.
- Failure it targets: the evidence is not fully in the 5 passed chunks. On dev, B lost two questions with `evid` < 1 (ADD-HP09 0.70, ADD-PF08 0.67), i.e. 3 of 9 lost points; retrieval-side loss is small on both chains.
- Expected effect: 0 to +0.017 at most. In card 013 each model reranking for itself gave `evid@5` 0.938 (3.6-flash) and 0.945 (lite), so the larger model is not expected to rerank better. Cost: a 3.6-flash rerank is billed at 0.75 / 3.75 USD per 1M tokens against 0.30 / 2.50 for lite.
- Limits: the rerank is an LLM call and `gemini-3.5-flash-lite` ignores `temperature: 0`; two runs of the same setting gave different final contexts for 43–46 of 90 dev questions (cards 016, 017). A difference between R-lite and R-36 therefore mixes the rerank model with run-to-run variation, and one run per condition cannot separate them. No rerun of R-lite is made, so there is no noise estimate for this pair.

## 2. Measurement

- Split: provided test, the sets `base_positive`, `base_negative`, `life_guide`, `additional` (90 questions). The discarded first self-written set and `self2` are not run. Runs use `--split test --final`.
- Reference runs: R-lite is compared with T4 `test_013b_rerank_lite` (the same 90 questions, matched by question ID); R-36 is compared with R-lite.
- Metrics: judge score paired per question (`scripts/compare.py`); `status_ok`; `citation_on_target`; evid@5 and `page_hit` from the final 5 chunks; share of questions whose final context differs between the two runs; USD per question (answer + rerank), tokens, p50 / p90 latency; garbled outputs (kana check).
- Not looked at before the runs: any test number of R-lite or R-36. T4's test numbers are known (EVALUATION.md).

## 3. Go/no-go criteria (written before results)

- R-36 counts as better than R-lite on test if, paired against `test_017b_flash38`: net wins ≥ 5, no more than 5 of R-lite's fully correct answers drop below 2, and the 95% CI of the score difference excludes 0 (the rule of cards 013 and 017). Otherwise it is described as not distinguishable; with one run per condition and the context variation above, a difference below about 0.03 is not interpreted.
- R-lite vs T4 (the effect of the answer model 3.6-flash/3.8-flash on test, B against the lite answer model) is reported with the same rule, as a descriptive result.
- Cost and latency are reported, not gated. Changing the final system is the owner's decision and not part of this card; the already published T1–T4 numbers are not edited.
- If a run fails or is interrupted it resumes under the same name; it is not rerun under a new name to get a different number.

## 4. LLM budget

- R-lite: rerank 90 + answers 90 + judge 90 = 270 calls, about 0.7 USD (dev B: 0.53 + judge 0.14).
- R-36: the same 270 calls, about 1.0 USD (the rerank by 3.6-flash adds about 0.4 USD).
- Smoke check before the test runs: 2 dev questions with the R-36 config, not graded and not part of any decision.
- Calls so far in the project: see the `submission/PROCESS.md` ledger.

## 5. Results

Runs `test_017b_flash38` (R-lite) and `test_018_b_rerank_flash36` (R-36), provided test, the 90 questions of `base_positive`, `base_negative`, `life_guide`, `additional`, one run each, 2026-10-22. In R-lite one question (ADD-PF10) ended in an error (the model returned an empty response that did not match the schema, after the retries); it was resumed once under the same name, as section 3 allows, and succeeded, so both runs have 90 graded questions. Smoke check of the R-36 config on 2 dev questions (not graded): the rerank ran on `gemini-3.6-flash`, the answer on `gemini-3.8-flash`.

All numbers below are over the same 90 questions. T1 and T4 are the earlier test runs (`test_000_baseline`, `test_013b_rerank_lite`) restricted to these questions.

| Setting | T1 original (`baseline.yaml`) | T4 original final | R-lite | **R-36 (best here)** |
|---|---|---|---|---|
| Chunking | recursive 800/100 | structure + 950/119 | same as T4 | same as T4 |
| Retrieval | vector, k=5 | Hybrid, pool 15 → LLM rerank 5 | same | same |
| Rerank model | – | `gemini-3.5-flash-lite` | `gemini-3.5-flash-lite` | `gemini-3.6-flash` |
| Answer model / thinking | `gemini-3.5-flash-lite` / low | `gemini-3.5-flash-lite` / low | `gemini-3.8-flash` / low | `gemini-3.8-flash` / low |
| Answer prompt | `answer_v1` | `answer_v4` | `answer_v4` | `answer_v4` |
| Answer score / points of 180 | 0.706 / 127 | 0.844 / 152 | 0.928 / 167 | **0.956 / 172** |
| Fully correct | 56.7% | 75.6% | 87.8% | 93.3% |
| Status match | 83.3% | 92.2% | 98.9% | 98.9% |
| `evid@5` / `page_hit` (gold-page questions) | 0.767 / 0.946 | 0.881 / 0.973 | 0.879 / 0.973 | 0.898 / 0.973 |
| USD / question (answer + rerank) | 0.0012 | 0.0036 | 0.0061 (1.66× T4) | 0.0089 (2.43× T4) |
| p90 latency | about 1.9 s | about 3.5 s | about 10.5 s | about 10.5 s |

Paired differences (95% CI; better / worse / same):

| Pair | Difference | Counts |
|---|---|---|
| R-36 vs T1 (original) | +0.250 [+0.167, +0.333] | 36 / 3 / 51 (T1 better: ADD-HF09 POS011 POS067) |
| R-36 vs T4 (original final) | +0.111 [+0.061, +0.161] | 19 / 1 / 70 (T4 better: POS067) |
| R-lite vs T4 | +0.083 [+0.033, +0.139] | 16 / 3 / 71 (T4 better: NEG017 NEG024 POS067) |
| **R-36 vs R-lite (this card)** | **+0.028 [+0.006, +0.056]** | 5 / 0 / 85 (R-36 better: ADD-HF04 ADD-HF08 NEG017 NEG024 POS068) |
| R-lite vs T2 `test_013_rerank_flash36` | +0.044 [+0.000, +0.094] | 9 / 3 / 78 |
| R-36 vs T2 | +0.072 [+0.033, +0.117] | 11 / 0 / 79 |

- By set (score / 2), T4 → R-lite → R-36: `base_positive` 0.933 → 0.967 → 0.967; `base_negative` 0.850 → 0.925 → 0.975; `life_guide` 0.750 → 0.900 → 0.950; `additional` 0.783 → 0.900 → 0.933.
- The final context differs between R-lite and R-36 in 67 of 90 questions. In the 5 questions R-36 gains, `evid` is the same in both runs (ADD-HF04, ADD-HF08, POS068: 1.0 and 1.0; NEG017: 0.0 and 0.0; NEG024 has no gold evidence), so the gain is not from more evidence in the context.
- Still below full score in R-36 (6): ADD-HF09, ADD-PF02, ADD-RP10, NEG005, POS011, POS067; in R-lite (11): those six plus ADD-HF04, ADD-HF08, NEG017, NEG024, POS068. POS011 is the grading error noted in EVALUATION.md §5.
- No kana in any answer of the two runs.
- LLM calls: R-lite rerank 90 + answers 90 + judge 90, R-36 the same, plus 4 smoke calls on dev; the failed attempt of ADD-PF10 logged no call. USD answer + rerank: R-lite 0.546, R-36 0.797; judge 0.145 each.

## 6. Decision and notes

- Decision: **nothing adopted; T1–T4 numbers in EVALUATION.md are unchanged.** R-36 has the highest test score of the settings run so far (0.956), but the card does not turn that into a recommendation.
- Rerank model (this card's question): R-36 meets the formal rule of section 3 (net +5, 0 drops, CI excludes 0), but its gain over R-lite is 0.028, below the 0.03 floor that section 3 gives for what is interpreted, and the 5 gained questions have unchanged `evid`, which points to answer variation on a different context rather than to better reranking. With one run per condition and 67 of 90 contexts different, the effect of the rerank model is **not established**. The rerank by `gemini-3.6-flash` costs 1.46× R-lite.
- Answer model: B (`gemini-3.8-flash`) with the lite rerank beats T4 on test by +0.083 [+0.033, +0.139], above the floor, with the largest gains in `life_guide` and `additional`; cost 1.66× and p90 latency about 3× T4. This repeats the dev result of card 017 (+0.056).
- Original vs best: R-36 against the original final system T4 is +0.111 and against the first RAG T1 +0.250, both with CIs that exclude 0. About three quarters of the T4-to-R-36 gap (+0.083 of +0.111) comes with the answer model; the rerank model accounts for at most the remaining +0.028.
- Limits: this is the third use of the provided test split (T1–T3, T4, this card). Choosing R-36 from these runs makes its 0.956 an optimistic estimate; B (R-lite) was chosen on dev and by the owner, so its 0.928 is less affected. Dev→test fell by about 0.05 for T2 and T4 earlier. The self-written sets were not run. No repeat of either condition, so no noise estimate for this pair.
- What the criteria missed: section 3 contains a formal gate and an interpretability floor that disagree for this result (+0.028). The decision above applies the floor; neither was changed after the results. The card also did not require a rerun of R-lite, which would have given a noise estimate for the pair.
