<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 002b: Answer runs — 900/112 alone and structure + 900/112

Status: planned
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

_filled after the runs_

## 6. Decision and notes

_filled after the runs_
