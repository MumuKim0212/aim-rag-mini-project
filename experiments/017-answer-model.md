<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 017: Answer model and thinking level on the final chain, rerank held fixed

Status: decided on dev (A and B better than T4 by the criteria, C not distinguishable; the owner picked B, 3.8-flash; no test run; sections 1–4 written 2026-10-22 before any run of A, B, C)
Date: 2026-10-22

## 1. Hypothesis

- Change: the answer step of the final system T4 (`configs/013b-rerank-lite.yaml`: structure + 950/119, Hybrid pool 15 → LLM rerank 5, `answer_v4`, `gemini-3.5-flash-lite`, thinking low). One variable per arm:
  - A `configs/017a-flash36.yaml`: answer model `gemini-3.6-flash`, thinking low.
  - B `configs/017b-flash38.yaml`: answer model `gemini-3.8-flash`, thinking low.
  - C `configs/017c-lite-think-high.yaml`: answer model `gemini-3.5-flash-lite` unchanged, `answer.thinking_level: high`.
- The rerank is fixed in all arms to `gemini-3.5-flash-lite` with thinking low (`retrieval.rerank_model`; new optional `retrieval.rerank_thinking_level`, `src/rag/rerank.py`, tests in `tests/test_rerank_thinking.py`; without the key the rerank follows `answer.thinking_level` as before). Reason: in T2 the rerank model was the answer model, so a plain model swap changes two steps at once. Consequence: arm A is **not** T2 (T2 reranked with 3.6-flash). The effect of the rerank model is a separate comparison, not part of this card.
- Failure it targets (dev, `dev_013b_rerank_lite_fix` = T4, 17 of 90 below full score, 19 points): the answer has the evidence but leaves out an item the reference requires. Against `dev_013_rerank_flash36_fix` (T2, 12 below full score): lost by lite only (7): ADD-HP10 ADD-PF01 NEG013 POS050 POS054 POS076 POS078; lost by both (10): ADD-HP02 ADD-IN04 ADD-PF08 ADD-SE06 ADD-SE08 NEG014 POS057 POS059 POS066 POS079; lost by 3.6-flash only (2): ADD-HP09 NEG039. Several of the shared ten miss an item that is not in the retrieved text (POS066, POS079) or is a single word (POS057), so no answer model is expected to recover them.
- Expected effect: A about +0.03 (T2 − T4 was +0.034 on dev and on test, with a different rerank); B unknown, at most A (older chain without rerank: 0.850 vs 0.822, within noise); C unknown, 0 to +0.03 (at thinking low `gemini-3.5-flash-lite` used 0 thinking tokens). Ceiling with the shared ten unchanged: about 0.93–0.94 on dev. Cost: A and B about 2×, C more output tokens (thinking is billed as output).
- Limits: one run per arm; "high" is the only thinking value tried; the arm questions and the lists above were read from dev results, so a dev gain is optimistic; dev scores came down by about 0.05 on test for T2 and T4 (EVALUATION.md §7).

## 2. Measurement

- Baseline run (reused, not rerun): `dev_013b_rerank_lite_fix` (T4 on dev, 0.894). Split: dev 90, one run per arm: `dev_017a_flash36`, `dev_017b_flash38`, `dev_017c_lite_think_high`. Same index, same judge.
- Metrics: judge score paired per question against T4 (`scripts/compare.py`); `status_ok`; fully correct reference answers that fall below 2; how many of the 7 lite-only and the 10 shared questions each arm brings to 2; share of questions whose final context differs from T4's (the rerank is an LLM call, so some differ even with the same settings; reported so score differences can be read against it); evid@5; USD per question (answer + rerank), tokens including thinking tokens, p50 / p90 latency; garbled outputs (`scripts/garble_scan.py`).
- Arms are compared with each other descriptively; only the pairing against T4 is tested.
- Not looked at: the test split, the self-written golden sets. No new test run: the provided test split has been used twice (EVALUATION.md §7).

## 3. Go/no-go criteria (written before results)

- An arm counts as better than T4 on dev if, paired against `dev_013b_rerank_lite_fix`: net wins ≥ 5, no more than 5 of the fully correct reference answers drop below 2, and the 95% CI of the score difference excludes 0 (the rule of card 013).
- A difference smaller than the run-to-run variation is described as not distinguishable: a rerun of the same setting changed 14 of 90 answers (PROCESS §4), and the final context differed in 45 of 90 questions between two runs of the same settings (card 016).
- Cost is reported, not gated. Choosing the final answer model is the owner's decision by price (T4 was chosen for price, 2026-10-22); this card only measures. No test number will exist for any arm, so an arm cannot be reported as a test result.
- Results are a dev measurement, one run per arm; nothing here changes T4, the test results, or any frozen file.

## 4. LLM budget

- Per arm: rerank 90 (lite) + answers 90 + judge 90 = 270 calls; three arms 810 calls. Estimated USD: A and B about 0.7–0.9 each answer side plus about 0.13 judge; C unknown, thinking is billed as output; plan for 0.4–1.0. Total about 2–3.5 USD.
- Smoke check before the batches: 2 dev questions per arm, not graded (also checks that `thinking_level: high` is accepted by `gemini-3.5-flash-lite`).
- Calls so far in the project: see the `submission/PROCESS.md` ledger.

## 5. Results

Runs `dev_017a_flash36`, `dev_017b_flash38`, `dev_017c_lite_think_high` (2026-10-22, dev 90, 0 errors, one run each; the 2-question smoke runs kept their names and the batch resumed). Reference: `dev_013b_rerank_lite_fix` (T4 on dev). In all three the rerank is `gemini-3.5-flash-lite` with thinking low (checked in the smoke calls: 0 thinking tokens on the rerank).

| | T4 | A 3.6-flash | B 3.8-flash | C lite, thinking high |
|---|---|---|---|---|
| Answer score / points | 0.894 / 161 | 0.939 / 169 | **0.950 / 171** | 0.906 / 163 |
| Paired vs T4 (better / worse / same, net) | – | 9 / 2 / 79, +7 | 11 / 2 / 77, +9 | 4 / 2 / 84, +2 |
| Diff, 95% CI | – | +0.044 [+0.006, +0.083] | +0.056 [+0.017, +0.100] | +0.011 [−0.017, +0.039] |
| Fully correct T4 answers that fell below 2 (limit 5) | – | 2 (NEG039 ADD-HP09) | 1 (ADD-HP09) | 2 (ADD-HP09 ADD-RP05) |
| Fully correct / status match / citation on a gold page | 81.1% / 96.7% / 95.9% | 88.9% / 96.7% / 97.3% | 91.1% / 96.7% / 98.7% | 83.3% / 95.6% / 98.7% |
| USD / question (answer + rerank) | 0.003504 | 0.00589 (1.68×) | 0.00591 (1.69×) | 0.00858 (2.45×) |
| Tokens / question (thinking tokens in total) | 9,796 (0) | 9,948 (3,911) | 9,952 (0) | 11,806 (178,813) |
| p90 latency | 4.0 s | 9.0 s | 11.1 s | 14.4 s |
| Final context differs from T4's | – | 46 / 90 | 43 / 90 | 43 / 90 |

- Criteria (section 3): A and B meet all three (net wins ≥ 5, ≤ 5 drops, CI excludes 0). C does not (net +2, CI includes 0).
- B vs A (descriptive): +0.011, CI [−0.017, +0.039], 4 better / 2 worse / 84 same. Not distinguishable. B better: ADD-SE06 NEG014 NEG039 POS076; A better: POS050 POS066.
- Better than T4 — A: ADD-HP10 ADD-PF01 ADD-SE08 NEG013 POS054 POS057 POS059 POS066 POS078; B: ADD-HP10 ADD-PF01 ADD-SE06 ADD-SE08 NEG013 NEG014 POS054 POS057 POS059 POS076 POS078; C: ADD-PF01 POS050 POS059 POS078. Worse than T4 — A: ADD-HP09 NEG039; B: ADD-HP09 POS050; C: ADD-HP09 ADD-RP05.
- The 7 questions lost by lite only (section 1): A brings 5 to 2 points (ADD-HP10 ADD-PF01 NEG013 POS054 POS078), B 6 (all but POS050), C 3 (ADD-PF01 POS050 POS078). The shared ten: A 4 (ADD-SE08 POS057 POS059 POS066), B 4 (ADD-SE06 ADD-SE08 POS057 POS059), C 1 (POS059); NEG014 rises from 0 to 1 in B only and stays below 2.
- Garbled outputs: no kana in any answer of the three arms (direct check). `garble_scan.py` flags 2 of 90 for A (NEG025, NEG035) and 90 of 90 for C; both are the output-token / answer-length ratio, which counts thinking tokens and long refusals, not garbling.
- LLM calls: per arm rerank 90 + answers 90 + judge 90 (smoke included); 810 in total. USD answer + rerank: A 0.530, B 0.532, C 0.772; judge about 0.14 per arm.

## 6. Decision and notes

- Decision on dev: **A and B are better than T4; C is not.** The owner picked **B (`gemini-3.8-flash`)** on 2026-10-22. By the criteria A and B are not distinguishable (+0.011, CI includes 0), so B over A is the owner's choice, not a result of this card; both cost the same here. This card does not change T4 or any test result: no test number exists for any arm, and the provided test split is not run again (it has been used twice, EVALUATION.md §7). Using B as the final system would be reported as a dev measurement.
- Why, with question IDs: a bigger answer model brings back most of the answers that only lite lost (A 5 of 7, B 6 of 7) and a part of the ten that both models lost (4 of 10 for A and for B). Raising lite's thinking brought back 3 of 7 and 1 of 10 at 2.45× the cost, so on this chain model size mattered more than the reasoning budget. The rerank was held at lite, which made A and B cost 1.7× T4 instead of the 2.5× of T2 (T2 reranked with its own model).
- Correction to the earlier estimate (card 016 discussion): the ten shared losses were expected to stay and the dev ceiling to be about 0.93–0.94. A bigger model recovered 4 of the ten and B reached 0.950. Still below full score: A 10 questions (ADD-HP02 ADD-HP09 ADD-IN04 ADD-PF08 ADD-SE06 NEG014 NEG039 POS050 POS076 POS079), B 8 (ADD-HP02 ADD-HP09 ADD-IN04 ADD-PF08 NEG014 POS050 POS066 POS079). Six of A's and six of B's are among the shared ten that no arm fully fixes; ADD-HP09 was fully correct only in T4 and lost in T2, A, B and C (cause not checked). Several of the shared ones need an item that is not in the retrieved text (earlier reading of POS066, POS079).
- What the criteria missed / limits: one run per arm on dev, the set the settings were tuned on (dev→test fell by about 0.05 for T2 and T4); 43–46 of 90 final contexts differ from T4's even with the rerank held at the same model, so part of the paired difference may be rerank variation, although A and B recover the same questions and C does not. The two flash arms are not separated. Cost p90 latency of 9–11 s versus 4 s was not gated. Open: the effect of the rerank model on A and B (T2, with a 3.6-flash rerank, scored 0.928 on dev against 0.939 for A with a lite rerank; different runs, so no conclusion); a repeat run or a replay of stored contexts to separate rerank variation.
