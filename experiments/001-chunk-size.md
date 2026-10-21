<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 001: Chunk size 400 / 800 / 1200

Status: planned
Date: 2026-10-21

## 1. Hypothesis

- Change (one variable): Recursive chunk size, overlap kept at 1/8 of the size. Variants `configs/001-chunk400.yaml` (400/50) and `configs/001-chunk1200.yaml` (1200/150) against the baseline 800/100. Everything else is the baseline (retrieval, k=5, embedding, prompt, answer model).
- Failure it targets: "evidence missing from the context", 25 of the 32 dev failures with a gold page (triage, PROCESS.md §6): retrieval misses POS001, POS006, POS013, POS021, POS052, ADD-HF10, ADD-SE04; partial evidence ADD-HF06, ADD-HF07, ADD-HP09, ADD-IN10, ADD-PF01, ADD-RP05, ADD-RP06, ADD-SE06, ADD-SE08, POS047, POS050, POS061, POS078; over-abstention ADD-PF08, ADD-PF09, POS045, POS057, POS058.
- Expected effect: 400 isolates one glossary definition or clause better (fewer terms mixed in a chunk), so the four glossary misses may improve, but it cuts multi-line evidence apart. 1200 keeps more evidence together and brings more text per search. No prediction on the sign for 400; for 1200 any gain in `evid@5` is partly just more characters in the context, which is why the context length is a gate below.

## 2. Measurement

- Baseline run (reused, not rerun): `dev_000_baseline` (`results/dev_000_baseline/`)
- Proxy metric (step 4): `evid@5` — share of evidence segments found in the top 5 chunks (r = 0.51 / 0.61 / 0.50 with the answer score on the three gradings, PROCESS.md §5). Also reported: `page_hit@5`, `mrr`, `gold@5`, context characters, and the number of chunks per index.
- Split: dev, the 74 questions with gold pages (the 16 without gold pages have no retrieval metric). Indexes: scope A for `base_*`, scope B for the other sets, as in the baseline.
- Noise (step 3): (a) 14 of 90 answers changed on a rerun of the same config, (b) 3 of 90 changed on a regrade. Retrieval is deterministic for a fixed index (baseline and its rerun have identical retrieval metrics), so the LLM-free gate has no noise of its own; the answer-level noise 14 applies to the headroom and adopt gates.
- Not looked at: test split, self-written golden set.

## 3. Go/no-go criteria (written before results)

Applied to each variant separately against the baseline.

- LLM-free gate: mean `evid@5` ≥ baseline + 0.03 (0.697 → 0.727) **and** questions with higher `evid@5` minus questions with lower ≥ 5.
- Context cap: mean context characters ≤ 1.5× baseline (3,064 → 4,596). A variant over the cap is rejected even if the gate above passes (the gain would be paid for in answer-step tokens); it is still reported.
- Headroom gate: `python -m evalkit.headroom ... --metric evid@5 --noise 14`: upside − risk > 14 (the workflow rule). If not, no answer run; record the reason in section 7.
- Cost cap (answer run): tokens per question ≤ 1.3× baseline (2,916 → 3,790), p90 latency ≤ 3.0 s (baseline 2.07 s).
- Adopt if (answer run): paired against `dev_000_baseline` net wins (B better − A better) ≥ 9, more than 14 questions changed, and the 95% CI of the score difference excludes 0. The bar is above the worst noise seen (rerun: 3 better / 11 worse, i.e. |net| = 8, CI also excluded 0). Report the garbled-output count (`scripts/garble_scan.py`) next to the result.
- If both variants pass everything, adopt the one with more net wins; on a tie the smaller context.

## 4. LLM budget

- Planned calls if the gates pass: answers 90 + judge 90 per passing variant (about 0.23 USD each); 0 if the gates fail. Indexes and retrieval-only runs use embeddings only (about 0.14 USD per config for scopes A and B).
- Calls so far in the project: 826 (submission/PROCESS.md ledger, 2026-10-21)

## 5. LLM-free results

| Config | Proxy metric (dev) | Net vs baseline (+/−) | Context chars / est. tokens |
|---|---|---|---|
| baseline (800/100) | 0.697 | – | 3,064 |
| 400/50 | | | |
| 1200/150 | | | |

- Headroom: upside _N_ (_qids_), already correct among improved _N_, risk _N_ (_qids_)
- Gates passed? _yes / no — if no, skip section 6 and decide in section 7_

## 6. Answer run (only if the gates passed)

- Experiment name: _..._
- Paired vs baseline: _B better N / A better N / same N, diff ±0.000, 95% CI [_, _]_
- Tokens / latency vs baseline: _..._
- LLM calls used: _answers __ + judge ___

## 7. Decision and notes

- Decision: _adopt / reject / inconclusive_
- Why, with question IDs: _..._
- What the criteria missed, if anything: _..._
