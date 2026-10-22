<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 016: Answer prompt v6 — state the scope of the answer

Status: decided (v6 rejected: guard failed, no gain distinguishable from noise; sections 1–4 written 2026-10-22 before any v6 run)
Date: 2026-10-22

## 1. Hypothesis

- Change (one variable): the answer prompt, `answer_v4` → `answer_v6` (`configs/016-lite-v6.yaml`, base = `configs/013b-rerank-lite.yaml`, i.e. the final system T4: structure + 950/119, hybrid pool 15 → LLM rerank 5, `gemini-3.5-flash-lite`). v6 adds rule 12 only: (a) when the question does not name a product / insurance / scheme type but the results cover one type, say the answer is about that type, say other types may differ, and do not open with "예/아니오"; (b) when the results are group aggregates or an example table and the question asks to apply them to one household / person / contract, say in one sentence that the aggregate does not carry over to individual cases. The rule adds no fact, so it does not conflict with rule 1. Rules 1–11 are identical to v4 (checked by `tests/test_answer_prompt_v6.py`).
- Failure it targets (dev, T4 `dev_013b_rerank_lite_fix` and T2 `dev_013_rerank_flash36_fix`): the answer has all the evidence (`evid` = 1) but omits a limit of scope. Read case by case: ADD-IN04 (question: "병원비 보장 보험을 두 군데 들면 두 배?", answer opens "아니오" about 실손 only, does not say other types differ) and ADD-SE08 (question asks whether one household can be said to owe twice the average; the answer says "말할 수 있습니다" without saying the figure is a group aggregate). Both lose a point in both chains.
- Deliberately **not** targeted: POS066 and POS079 lose a caveat that is not in the retrieved text (POS079's question already excludes eligibility), so adding it would be writing to the reference rather than to the user; NEG014 (clarify expected for "해외 거래 결제는 며칠 걸려?") fails in every chain but the answer is faithful to the document and a stronger clarify rule would risk turning answerable questions into clarify; ADD-SE06 / ADD-PF08 / ADD-HP09 / ADD-PF01 miss evidence, which is a retrieval matter. Graph changes (grade split, query decomposition, a check node) are not part of this card: card 014 tried a check node and it flagged none of the targeted answers; the evidence-missing loss is 3 points in both chains.
- Expected effect: at most +2 questions of 1 point on dev (+0.011), in the lite chain; likely 0–2. Risk: scope sentences added where not needed (extra length), or status drift (clarify / abstained) on answerable questions. This is a targeted probe; the gain is inside the noise (14 of 90 changed in a rerun, net −8, PROCESS §4), so the result will be described as such unless it is larger than expected.

## 2. Measurement

- Baseline run (reused, not rerun): `dev_013b_rerank_lite_fix` (T4 on dev, 0.894, 19 points lost). Same index, same rerank, same judge. Split: dev 90, one run.
- Metrics: judge score paired per question (`scripts/compare.py`); `status_ok`; `citation_on_target`; answer length (characters) vs reference; for ADD-IN04 and ADD-SE08, whether the answer contains the scope sentence and its score; the fully correct reference answers (73 of 90) that drop below 2; USD per question, p90 latency.
- Garbled outputs counted with `scripts/garble_scan.py` (lite, PROCESS §6).
- Not looked at: test split, self-written golden sets.

## 3. Go/no-go criteria (written before results)

- Guard (harm): at most 2 of the fully correct reference answers drop below 2, and `status_ok` does not fall by more than 1 question. If it fails, v6 is rejected whatever the gain.
- Mechanism (descriptive): both ADD-IN04 and ADD-SE08 contain the scope sentence; their scores are reported, not gated.
- Better than T4 on dev if, paired against `dev_013b_rerank_lite_fix`: net wins ≥ 9, more than 14 questions changed, 95% CI of the difference excludes 0 (the rule of cards 008 and 014). The expected gain (+2 questions) cannot reach this, so the most likely reading is "not distinguishable"; that is stated here, not after the run.
- The final system is **not** changed by this card (T4 was fixed by the owner on 2026-10-22; the test split is not run again). v6 is reported as a tried change; adoption would be a new decision by the owner and would need a new final test, which the rules do not allow, so v6 is not adopted by default.
- Cost is reported, not gated (an answer-side token change only).

## 4. LLM budget

- `dev_016_lite_v6`: 90 rerank + 90 answers + 90 judge = 270 calls, about 0.3 USD (lite answer side 0.0035 USD per question incl. rerank; judge about 0.13 USD).
- Smoke check before the batch: ADD-IN04 and ADD-SE08 with v6 (not graded).
- Calls so far in the project: see the `submission/PROCESS.md` ledger.

## 5. Results

Run `dev_016_lite_v6` (2026-10-22, dev 90, 0 errors; a 3-question smoke run under the same name came first and was kept by the resume). Reference: `dev_013b_rerank_lite_fix` (T4 on dev).

| | T4 `dev_013b_rerank_lite_fix` | v6 `dev_016_lite_v6` |
|---|---|---|
| Answer score (0–1) / points | 0.894 / 161 | 0.889 / 160 |
| Fully correct / status match / citation on a gold page | 81.1% / 96.7% / 95.9% | 81.1% / 94.4% / 95.9% |
| Paired vs T4 (better / worse / same) | – | 3 / 4 / 83, diff −0.006, CI [−0.033, +0.022], net −1 |
| LLM calls / question | 2.0 | 2.0 |
| Tokens / question | 9,796 | 10,055 (1.03×) |
| USD / question (answer + rerank) | 0.003504 | 0.003586 (1.02×) |
| p90 latency | 4.0 s | 11.1 s (cause not checked) |
| Garbled outputs (`garble_scan.py`) | – | 0 of 90 |

- v6 better: ADD-SE08 (1 → 2), POS054 (1 → 2), POS078 (1 → 2). T4 better: ADD-HP09 (2 → 1), ADD-PF06 (2 → 1), NEG025 (2 → 1, refused → answered), POS057 (1 → 0, answered → abstained).
- Guard (section 3): 3 of 73 fully correct reference answers fell below 2 (NEG025, ADD-HP09, ADD-PF06; limit 2) and `status_ok` fell by 2 questions (87 → 85; limit 1). **Both fail.**
- Mechanism (descriptive): ADD-SE08 now says the aggregate does not carry over to one household ("개별 가구 단위에 그대로 적용하기에는 한계가 있을 수 있습니다"), 1 → 2. ADD-IN04 has no sentence about other insurance types and stays 1 → 1: rule 12 (a) did not fire. A regex count of scope-like phrases finds 2 v6 answers (ADD-SE08, ADD-PF08) against 0 in T4; mean answer length is 448 vs 449 characters, so the rule changed few answers.
- Better-than-T4 rule (net wins ≥ 9, more than 14 changed, CI excludes 0): net −1, 7 changed, CI includes 0 → not met.
- Run-to-run variation seen in this pair: the retrieval settings are identical, yet the final context set differs in 45 of 90 questions (the rerank is an LLM call and `gemini-3.5-flash-lite` ignores `temperature: 0`). Of the 7 questions whose score changed, 4 had a different context (ADD-PF06, NEG025, ADD-SE08, POS078) and 3 the same context (POS054, POS057, ADD-HP09).
- LLM calls used: rerank 90 + answers 90 + judge 90 = 270 (USD 0.323 answer side incl. embeddings 0.001, judge 0.133).

## 6. Decision and notes

- Decision: **reject.** The guard failed on both conditions written before the run, and the gain is not distinguishable from noise (−0.006, CI includes 0). The final system stays T4; v6 is reported as a tried, not-adopted change.
- Why, with question IDs: rule 12 changed few answers. It produced the intended scope sentence on ADD-SE08, but the context of ADD-SE08 also differed from T4's, so the gain cannot be assigned to the rule alone. It did nothing on ADD-IN04. Of the four questions that got worse, two had a different context (ADD-PF06, NEG025) and one (ADD-HP09) answered from the same context with one part missing; POS057 switched from answered to abstained on the same context. With the rule so rarely active these look like run-to-run variation, but this run cannot separate that from an effect of the rule.
- What the criteria missed: the guard of 2 drops was too tight for this noise. A rerun alone flips 14 of 90 questions (PROCESS §4), and here 45 of 90 context sets change with unchanged settings, so a guard of 2 can fail by chance. The criteria were not changed after the results; the decision above follows them as written. The expected gain (at most +2 questions) was far below what one dev run can show.
- Consequence for any later comparison on the final chain: a single dev run of an answer-step change cannot be separated from the rerank variation. A comparison that replays the stored contexts of T4 through the answer step only, and repeats each arm, would remove that part; it was not built because the final system is fixed and the possible gain is small (+0.01 to +0.02).
- Not changed by this card: T4, the test split, the self-written sets. `answer_v6` stays frozen.
