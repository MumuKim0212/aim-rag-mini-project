<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 014: Agent v2 (memo to the answer step + answer check with one revision)

Status: decided (v2 not adopted: no change vs T2 on dev, check node flagged none of the targeted answers; sections 1–4 written 2026-10-22 before any v2 run)
Date: 2026-10-22

## 1. Hypothesis

- Change: the agent graph on the final chain. Base = T3 (`configs/008b-agent-950.yaml`: structure + 950/119, hybrid pool 15 → LLM rerank 5, `gemini-3.6-flash`, classify / grade / rewrite ≤ 2 / cite_check). v2 (`configs/014-agent-v2.yaml`) adds, all behind config flags so T3 runs unchanged:
  1. **memo** (`agent.memo`): the generate node receives the classify node's question type and reason, and "evidence still missing after search N" when the last grade said insufficient. Prompt `answer_v5` = `answer_v4` + rule 12 + an `[에이전트 메모]` block. In card 008 the type was computed and then dropped (NEG013: classified `needs_info`, answered).
  2. **check** (`agent.check`, `prompts/agent_check_v1.md`, model `gemini-3.8-flash`, a different model from the answer model at the same price): after cite_check, reads the draft and lists missing question parts, missing conditions / caveats, numbers not in the results, wrong response type. If it lists any, generate rewrites once with those problems and the draft in the memo (`agent.max_revise: 1`); the revision is not checked again.
  3. **termination reason** in `steps`: completed / revised / insufficient_evidence.
- Not built: a separate abstain node with a fixed message (course notebook 23). In `dev_008_agent` 4 questions ended with grade still "insufficient"; ADD-HF06 was answered from partial evidence and scored 2, NEG034 was a correct refusal, so a fixed abstain message would have lost at least 2. The "insufficient" state goes to the answer step through the memo instead.
- Failure it targets (dev, `dev_013_rerank_flash36_fix` = T2 on dev, 12 of 90 below full score): 10 found the gold page but left out a part or a caveat (ADD-HP02 ADD-HP09 ADD-IN04 ADD-PF08 ADD-SE06 ADD-SE08 POS057 POS059 POS066 POS079) → check + revision; 2 response-type errors (NEG014 clarify expected, NEG039 abstain expected) → memo. The check prompt uses general rules only, no reference answer or rubric wording. It was written after reading these 10 dev failures, so a dev gain is optimistic.
- Expected effect: + a few questions on dev, mostly score 1 → 2; cost about +1.3 calls per question.

## 2. Measurement

- Baselines (reused): `dev_013_rerank_flash36_fix` (T2 on dev, 0.928). The T3 agent on this chain was never run on dev, so it is run once now as `dev_008b_agent950` in the same batch as v2 (same day, same judge) to separate "agent v1 → v2" from "RAG → agent".
- Split: dev 90, one run each. Noise: 14 of 90 changed in a rerun (net −8, PROCESS §4).
- Metrics: judge score paired per question (`scripts/compare.py`), `status_ok`, `citation_on_target`, by set and behavior group; check results (share with problems, share revised, score of revised questions before → after is not observable, so report revised questions' final score vs T2); termination reasons; LLM calls, tokens, USD, p50/p90 latency.
- Self-written set: v2 is also run once on `golden/self2.jsonl` (41) as `test_014_agent_v2_self2`, after the dev runs, whatever the dev result. T1–T4 already ran on self2 (PROCESS §9); this builder has not read those self2 results and does not read them before the v2 self2 run is done. Provided test 90 is **not** run with v2 (it has been used twice).

## 3. Go/no-go criteria (written before results)

- v2 counts as better than T2 on dev if, paired against `dev_013_rerank_flash36_fix`: net wins ≥ 9, more than 14 questions changed, 95% CI of the difference excludes 0 (same rule as card 008).
- v2 vs `dev_008b_agent950`: reported, not gated (same rule would need net ≥ 9).
- Final system is **not** changed by this card: T4 was chosen by the owner for price and the test split is not run again. v2 replaces T3 as "the agent" in the write-up only if it is better than T2 by the rule above; otherwise it is reported as a tried and not-adopted change.
- Cost is reported, not gated.

## 4. LLM budget

- `dev_008b_agent950`: about 4.4 calls / question (classify, rerank, grade 1–3, rewrite 0–2, generate 1–2) ≈ 400 + judge 90. About 1.2 + 0.14 USD.
- `dev_014_agent_v2`: about 5.7 calls / question (+ check 1, + revision 0–1) ≈ 520 + judge 90. About 1.6 + 0.14 USD.
- `test_014_agent_v2_self2`: 41 × 5.7 ≈ 235 + judge 41. About 0.75 + 0.07 USD.
- Smoke check before the batches: 2 dev questions with v2 (not graded).
- Calls so far in the project: 6,490 (PROCESS ledger, 2026-10-22).

## 5. Results

Runs 2026-10-22, 0 errors. `dev_008b_agent950` and `dev_014_agent_v2` ran at the same time (same judge, same day).

| | T2 RAG `dev_013_rerank_flash36_fix` | Agent v1 `dev_008b_agent950` | Agent v2 `dev_014_agent_v2` |
|---|---|---|---|
| Answer score (dev 90) | 0.928 | 0.939 | 0.928 |
| Fully correct / status match / citation on a gold page | 86.7% / 96.7% / 98.6% | 88.9% / 97.8% / 97.3% | 86.7% / 95.6% / 98.6% |
| Paired vs T2 (better / worse / same) | – | 3 / 1 / 86, +0.011, CI [−0.011, +0.033] | 2 / 2 / 86, +0.000, CI [−0.022, +0.022] |
| LLM calls / question | 2.0 | 4.06 | 4.96 |
| Tokens / question | 9,951 | 12,693 | 15,640 |
| USD / question (answer side) | 0.0086 | 0.0109 | 0.0131 |
| p90 latency | 7.0 s | 9.9 s | 11.9 s |

- v1 better than T2: NEG039 POS059 POS066; T2 better: NEG013. v2 better than T2: ADD-HP02 ADD-SE08; T2 better: ADD-PF01 POS076. v2 vs v1: 3 better (ADD-HP02 ADD-SE08 NEG013) / 5 worse (ADD-PF01 NEG039 POS059 POS066 POS076), −0.011, CI [−0.044, +0.017].
- **Check node**: flagged 3 of 90 drafts (POS045 ADD-RP05 ADD-PF09), all three already scored 2 in T2 and still 2 after revision. It flagged **none** of the 10 targeted answers (ADD-HP02 ADD-HP09 ADD-IN04 ADD-PF08 ADD-SE06 ADD-SE08 POS057 POS059 POS066 POS079); ADD-HP02 and ADD-SE08 went 1 → 2 without a revision, so those two are answer variation (or the v5 memo), not the check.
- **Memo**: NEG014 (clarify expected) still answered (0 → 0); NEG013 answered correctly as clarify in v2 (it failed in v1 on this chain); NEG039 1 → 1. Termination reasons: completed 86, revised 3, insufficient_evidence 1.
- Self-written set `test_014_agent_v2_self2` (41, run once after the dev runs): 0.939 vs T2 `test_013_rerank_flash36_self2` 0.902 (3 / 1 / 37, CI [−0.024, +0.110]) and vs T3 `test_008b_agent950_self2` 0.927 (1 / 0 / 40, SELFB041). The check node revised 0 of 41; termination completed 35, insufficient_evidence 6. USD / question 0.0161 (T2 0.0090, T3 0.0139), p90 18.7 s.
- LLM calls: smoke 10; dev v1 365 + judge 90; dev v2 446 + judge 90; self2 v2 243 + judge 41. USD: 0.98 + 1.18 + 0.66 answer side, judge 0.34.

## 6. Decision and notes

- Decision by the criteria: **v2 is not better than T2** (net +0 vs 9 required, 4 changed vs more than 14, CI includes 0). v2 is reported as a tried, not-adopted change. T3 stays the agent of the write-up; the final system stays T4.
- Why, with question IDs: the change that targets the main dev failure (check + revision) did not fire on the targeted answers. The 10 answers each miss one detail the judge's reference requires (e.g. POS057 the word "별첨", ADD-PF01 "제도별 경로와 조건 다름"); a reviewer without the reference reads them as complete. `gemini-3.8-flash` at `thinking_level: low` used no thinking tokens (831 thinking tokens over all v2 calls); a guess, not checked: a review without thinking is shallow. The memo fixed NEG013 but not NEG014.
- Side result: agent v1 on the final chain was run on dev for the first time. It is ahead of T2 on all three sets that have it, each within noise: dev 0.939 vs 0.928 (+2), provided test 0.911 vs 0.883 (+4), self2 0.927 vs 0.902. Same direction three times; no single set separates them.
- Not tried (would need a new card): a reviewer with higher thinking or a stronger model; a checklist built from the question alone before answering. Both target the same 10 dev answers that were read to write this card, so a dev gain would be optimistic.
- What the criteria missed: nothing changed after the results.
