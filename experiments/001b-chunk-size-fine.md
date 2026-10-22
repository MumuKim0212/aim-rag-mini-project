<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 001b: Chunk size 500 / 700 / 900 (follow-up of 001)

Status: superseded (900/112 was later answer-run in card 002b and on the final chain in cards 001d / 001e; the chain ended at 950/119). Original: llm-free done (winner 900/112 at the retrieval level; headroom gate failed, so no answer run unless waived)
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
| 500/62 | 0.659 | 11 up / 21 down, net −10 | 2,065 |
| 700/88 | 0.714 | 12 up / 9 down, net +3 | 2,737 |
| baseline 800/100 | 0.697 | – | 3,064 |
| 900/112 | **0.771** | 18 up / 4 down, net +14 | 3,428 |
| 1200/150 (card 001) | 0.748 | 18 up / 8 down, net +10 | 4,166 |

Runs `dev_001b_chunk500_retrieval`, `dev_001b_chunk700_retrieval`, `dev_001b_chunk900_retrieval` (2026-10-21). Other numbers (500 / 700 / 800 / 900): `page_hit@5` 0.905 / 0.932 / 0.878 / 0.932, `mrr` 0.789 / 0.812 / 0.800 / 0.828, `gold@5` 2.20 / 2.08 / 1.92 / 1.97. Questions with `evid@5` = 1: 30 / 36 / 34 / 42; with 0: 12 / 9 / 11 / 8. Chunks (scope A / B): 480 / 1,832; 351 / 1,360; 309 / 1,212; 284 / 1,100. Index build cost (A + B): 0.144 / 0.141 / – / 0.139 USD.

- Qualifying under the rule (≥ 0.727, net ≥ 5, context ≤ 4,596): 900 and 1200 only. 900 is highest (0.771 vs 0.748, a gap of 0.023 > the 0.01 tie band) and has the shorter context (3,428 vs 4,166). **Winner: 900/112.** 700 is above the baseline but under both bars (0.714, net +3); 500 is below the baseline like 400.
- 900 improved: POS001 POS021 POS047 POS058 POS057 POS061 POS078 ADD-HP09 ADD-HF10 ADD-SE04 ADD-SE03 ADD-IN01 ADD-SE08 ADD-PF01 ADD-IN08 ADD-IN10 ADD-PF08 ADD-PF06. Worsened: NEG019 POS074 POS079 ADD-HF06. Dev quotes cut by chunking (scope A / B): 3 / 5 (baseline 1 / 6).
- Headroom (`evid@5`, noise 14), 900: upside 14 (ADD-HF10 ADD-HP09 ADD-IN10 ADD-PF01 ADD-PF08 ADD-SE04 ADD-SE08 POS001 POS021 POS047 POS057 POS058 POS061 POS078), already correct among improved 4, risk 3 (NEG019 POS074 POS079). Upside − risk = 11 ≤ 14.

## 6. Answer run (only if allowed)

The headroom gate failed (11 ≤ 14). The project owner waived it on 2026-10-21; the answer run of 900/112 is `dev_001b_chunk900`, recorded with its criteria in card 002b (score 0.717 vs 0.722, net +1, not adoptable). LLM calls used: 90 answers + 90 judge.

## 7. Decision and notes

- Decision: **900/112 is the best chunk size at the retrieval level; the adopted size stays 800/100 until the headroom gate is waived in writing or an answer run is otherwise allowed.** Answer accuracy of 900 is not measured.
- Why, with question IDs: the `evid@5` curve over 400 / 500 / 700 / 800 / 900 / 1200 is 0.675 / 0.659 / 0.714 / 0.697 / 0.771 / 0.748, not monotonic; 900 beats 1200 with a 19% shorter context, and has the most questions with all evidence in context (42, baseline 34) and the fewest with none (8, baseline 11). Its gain is across glossary, terms and the additional documents (POS001 POS021 POS047 POS057 POS058 POS078 ADD-HF10 ADD-HP09 ADD-PF08 ADD-SE04 ADD-SE08 among the 14 upside questions).
- What the criteria missed, if anything: nothing was changed after the results. The dip at 500 and the rise at 900 show that `evid@5` moves by a few questions between neighbouring sizes; with six candidates on 74 questions, the winner's margin over 1200 (0.023) and over the baseline (0.074) is not proof that 900 is best in general. The headroom bar is the same as in cards 001 and 002 (see their section 7).
