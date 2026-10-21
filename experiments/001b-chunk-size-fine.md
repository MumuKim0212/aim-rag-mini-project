<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 001b: Chunk size 500 / 700 / 900 (follow-up of 001)

Status: planned
Date: 2026-10-21

## 1. Hypothesis

- Change (one variable): Recursive chunk size 500/62, 700/88, 900/112 (overlap = size/8, rounded) against the baseline 800/100. Everything else is the baseline. Requested by the project owner on 2026-10-21: "pick the chunk size with the highest accuracy".
- Already known before this card (card 001, `evid@5` on dev, 74 questions with gold pages): 400 → 0.675, 800 → 0.697, 1200 → 0.748 (context 1,670 / 3,064 / 4,166 characters). So `evid@5` rises with size and the context grows with it; 500–900 fills in the curve between the points already measured. Card 001's decision (400 rejected, 1200 not adopted because of the headroom gate) stays as written.
- Failure it targets: same as card 001 (evidence missing from the context).
- Expected effect: a size between 800 and 1200 may keep most of 1200's gain at a shorter context; 500 and 700 are expected to be at or below the baseline (from 400 → 800).

## 2. Measurement

- Baseline run (reused): `dev_000_baseline`. Candidate set for the choice: 400, 500, 700, 800 (baseline), 900, 1200 — the 400 and 1200 runs come from card 001 and are not rerun.
- Proxy metric: `evid@5` (card 001, PROCESS.md §5); also `page_hit@5`, `mrr`, `gold@5`, context characters.
- Split: dev, the 74 questions with gold pages. Noise: answer-level 14 of 90 (rerun) and 3 of 90 (regrade); retrieval is deterministic for a fixed index.
- Six candidates are compared on the same 74 questions, so the best of them is picked partly by chance. Therefore the winner must clear the same bars as in card 001 over the baseline, and ties are broken toward the smaller context.
- Not looked at: test split, self-written golden set.

## 3. Go/no-go criteria (written before results)

- Selection rule (LLM-free, retrieval level): among the six candidates, take those with mean `evid@5` ≥ baseline + 0.03 (≥ 0.727), (questions with higher `evid@5` − questions with lower) ≥ 5, and mean context characters ≤ 1.5× baseline (≤ 4,596). From these, the highest mean `evid@5` wins; candidates within 0.01 of the highest are treated as tied and the one with the shortest context wins. If no candidate qualifies, the baseline 800/100 stays.
- Headroom gate for the winner: `evalkit.headroom --metric evid@5 --noise 14`, upside − risk > 14. If it fails, there is **no answer run**, and the winner is reported as "best at the retrieval level, answer effect unknown"; the adopted chunk size stays 800/100 unless the project owner waives the gate in writing (date and name in section 7).
- Cost cap and adopt rule for an answer run (only if the gate passes or is waived): same as card 001 — tokens per question ≤ 1.3× baseline, p90 latency ≤ 3.0 s; paired net wins ≥ 9, more than 14 questions changed, 95% CI excludes 0, garbled-output count reported.
- "Highest accuracy" here means highest `evid@5` at the retrieval level. Answer accuracy (judge score) is measured only by an allowed answer run.

## 4. LLM budget

- Planned calls: retrieval-only runs and indexes use embeddings only (about 0.14 USD per config for scopes A and B, about 0.42 USD for the three). If an answer run is allowed for the winner: answers 90 + judge 90 (about 0.23 USD).
- Calls so far in the project: 826 (submission/PROCESS.md ledger, 2026-10-21)

## 5. LLM-free results

| Config | Proxy metric (dev) | Net vs baseline (+/−) | Context chars |
|---|---|---|---|
| 400/50 (card 001) | 0.675 | 9 up / 19 down, net −10 | 1,670 |
| 500/62 | | | |
| 700/88 | | | |
| baseline 800/100 | 0.697 | – | 3,064 |
| 900/112 | | | |
| 1200/150 (card 001) | 0.748 | 18 up / 8 down, net +10 | 4,166 |

- Winner by the selection rule: _..._
- Headroom: _..._

## 6. Answer run (only if allowed)

_..._

## 7. Decision and notes

- Decision: _..._
- Why, with question IDs: _..._
- What the criteria missed, if anything: _..._
