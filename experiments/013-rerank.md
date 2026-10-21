<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 013: LLM rerank, hybrid pool 15 → 5

Status: running
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
