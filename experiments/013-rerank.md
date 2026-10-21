<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 013: LLM rerank, hybrid pool 15 → 5

Status: decided by the criteria (cost cap failed → references stay; both runs pass every other criterion and CI excludes 0; adoption is the owner's call)
Date: 2026-10-21

## 1. Hypothesis

- Requested by the project owner on 2026-10-21 ("rerank 진행해"), aiming at a dev score of 0.9.
- Change (one variable per run): after Hybrid retrieval take a pool of 15 (`retrieval.rerank_pool: 15`) and let the answer model pick the 5 chunks that answer the question (`prompts/rerank_v1.md`, `src/rag/rerank.py`, one extra LLM call; falls back to the pool order if the call fails). Answer step unchanged (k=5 chunks, prompt v4).
  - R1 `configs/013-rerank-flash36.yaml`: 3.6 flash + v4, reference `dev_012_flash36_v4` (0.883).
  - R2 `configs/013b-rerank-lite.yaml`: lite + v4, reference `dev_011c_lite_v4` (0.856).
- Failure it targets: answers whose evidence is not completely in the top 5 (dev, 3.6 flash + v4: POS047 POS050 POS059 POS061 POS074 ADD-HP09 ADD-HF06 ADD-SE06 ADD-IN08 ADD-PF08; lite adds POS079 ADD-HP10 ADD-HF10 ADD-IN01). LLM-free headroom (scratch analysis, 74 gold questions): evid vs k 5 → 0.861, 8 → 0.896, 15 → 0.951; 12 of 22 incomplete questions are complete by rank 15.
- Expected effect: evid@5 rises toward 0.90, +0.02 to +0.03 on the answer score; risk: the reranker drops a chunk the plain top 5 had (regressions) and adds one call of latency and money.
- Limits: pool 15 and the rerank prompt are single values chosen from the headroom analysis, not tuned; no second version of the prompt unless a general failure shows (then at most one, rerank_v2). The rerank model is the answer model, so the lite run reranks with lite.

## 2. Measurement

- Runs `dev_013_rerank_flash36`, `dev_013b_rerank_lite`, dev 90, one run each. Retrieval metrics (evid@5, page_hit, gold@5) come from the final 5 chunks. Rerank failures counted from `steps.rerank.failed`.
- Metrics as in cards 011/012, plus USD per question including the rerank call. Not looked at: test split, self-written golden set.

## 3. Go/no-go criteria (written before results)

- Adopt a rerank run if, paired against its reference: net wins ≥ 5, no more than 5 of the fully correct reference answers drop below 2, evid@5 ≥ reference + 0.02, USD per question ≤ 1.6× the reference's and p90 latency ≤ 8 s, rerank failures ≤ 5 of 90. Otherwise the reference setting stays.
- Target 0.9 is a goal, not a criterion. A gain inside the noise (CI includes 0) is described as "not distinguishable".

## 4. LLM budget

- Per run: rerank 90 + answers 90 + judge 90 (about 0.5 USD for 3.6 flash, 0.3 USD for lite).
- Calls so far in the project: 3,541 (submission/PROCESS.md ledger, 2026-10-21)

## 5. Results

First attempt (`dev_013_rerank_flash36`, `dev_013b_rerank_lite`, 360 calls, never graded) was invalid: the rerank system prompt still contained the literal `{k}` (fix: `fill` on the system text). It is not used in any decision; the runs below were made again under `*_fix` names with the same configs.

| | 3.6 flash + v4 | + rerank (R1) | lite + v4 | + rerank (R2) |
|---|---|---|---|---|
| Answer score | 0.883 | **0.928** | 0.856 | **0.894** |
| Points / fully correct | 159 / 72 | 167 / 78 | 154 / 67 | 161 / 73 |
| evid@5 / page_hit@5 / gold@5 | 0.861 / 0.973 / 2.15 | 0.938 / 0.986 / 2.50 | 0.861 / 0.973 / 2.15 | 0.945 / 0.986 / 2.41 |
| Citation on gold page | 97.3% | 98.7% | 93.2% | 96.0% |
| USD / question (answer + rerank) | 0.00404 | 0.00860 (2.13×) | 0.00164 | 0.00350 (2.14×) |
| p50 / p90 latency | – / 5.3 s | 5.5 s / 7.0 s | – / 3.7 s | 3.2 s / 4.0 s |

- R1 vs reference (`dev_012_flash36_v4`): better 9 (ADD-HF06 ADD-IN08 ADD-RP06 ADD-SE06 POS047 POS050 POS061 POS070 POS074), worse 2 (NEG039 POS079), 79 same; diff +0.044, CI [+0.006, +0.089], net +7. Both worse ones were fully correct before.
- R2 vs reference (`dev_011c_lite_v4`): better 9 (ADD-HF06 ADD-HF10 ADD-HP09 ADD-IN01 ADD-IN08 POS022 POS047 POS057 POS074), worse 2 (ADD-PF01 POS054), 79 same; diff +0.039, CI [+0.006, +0.072], net +7.
- R1 vs R2: +0.033 for 3.6 flash, CI [−0.072, +0.000]. Rerank failures 0 of 90 in both runs.

## 6. Answer run
See section 5 (2 × (90 rerank + 90 answer + 90 judge); 4,441 calls in the project ledger after the invalid first attempt).

## 7. Decision and notes

- Criteria: net ≥ 5 (+7, +7) yes; fully correct answers that drop ≤ 5 (2, 2) yes; evid@5 +0.02 (+0.077, +0.084) yes; p90 ≤ 8 s (7.0, 4.0) yes; rerank failures ≤ 5 (0, 0) yes; **USD per question ≤ 1.6× the reference: 2.13× and 2.14× → fails**. By the pre-registered rule the references stay. The absolute cost is small (0.0086 and 0.0035 USD per question, 0.77 and 0.32 USD per 90 answers).
- This is the first change in the project whose paired CI excludes 0 and that was not written from the dev failures (the rerank prompt and pool 15 were fixed once, before any run); in R1 it improves 7 of the 10 retrieval-limited questions it was aimed at (POS047 POS050 POS061 POS074 ADD-HF06 ADD-IN08 ADD-SE06; POS059 ADD-HP09 ADD-PF08 not), plus ADD-RP06 and POS070. It is the most trustworthy gain on dev, though the base prompt v4 is still dev-tuned.
- 0.9 reached: R1 0.928; R2 0.894 (just below). Rerank + lite costs about the same as 3.6 flash alone (0.0035 vs 0.0040 USD per question) and scores higher (0.894 vs 0.883).
- Candidates for T2 (owner): 3.6 flash + v4 + rerank (0.928), lite + v4 + rerank (0.894), 3.6 flash + v4 (0.883), 3.6 flash + v2 (0.861, current). Not switched; the agent (T3) does not use rerank (its search calls the retriever directly), so adopting rerank for T2 means T3 would differ in retrieval unless the agent's retrieve node is changed.
