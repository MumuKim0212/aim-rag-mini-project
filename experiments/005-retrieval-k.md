<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 005: Number of retrieved chunks k = 3 / 5 / 8

Status: planned
Date: 2026-10-21

## 1. Hypothesis

- Change (one variable): `retrieval.k` on the adopted chain (structure + 900/112 for the rest + hybrid α 0.5; `configs/004-hybrid.yaml`). Variants `configs/005-k3.yaml` and `configs/005-k8.yaml` against k=5. MMR (PLAN.md §3.2) is **not** run: it needs a new retriever and the time-cut order in PLAN.md §9 puts "k only, no MMR" second (decided by the builder on 2026-10-21, the day before the deadline; the owner can veto).
- Failure it targets: evidence missing from the context; the misses that remain in `dev_004_hybrid` are listed in section 5.
- Expected effect: k=8 puts more evidence in the context at about 1.6× the characters; k=3 saves about 40% of the context and may lose evidence. The answer step may also be distracted by more chunks, which only an answer run shows.

## 2. Measurement

- Baseline for this card: `dev_004_hybrid_retrieval` (retrieval only, k=5) and `dev_004_hybrid` (answers and grades, for the headroom check and the paired answer comparison).
- Proxy: context `evid` of the run (share of evidence segments in the chunks actually passed on, which is `evid@k` of that run's k). Also `page_hit`, `gold`, context characters. Split: dev, the 74 questions with gold pages. Answer-level noise: 14 of 90.
- Not looked at: test split, self-written golden set.

## 3. Go/no-go criteria (written before results)

- **k=8 (more context):** LLM-free gate: mean `evid` ≥ chain + 0.03 and (higher − lower) ≥ 5 questions, and mean context ≤ 1.5× chain (≤ 4,551 characters). The cap is expected to be tight or binding for k=8; if the cap fails, k=8 is rejected whatever its `evid`. If it passes: headroom (`evalkit.headroom --scores results/dev_004_hybrid/grades.jsonl --metric evid --noise 14`) must give upside − risk > 14, otherwise no answer run (no waiver assumed).
- **k=3 (less context, a cost-saving candidate):** it passes the LLM-free gate if mean `evid` ≥ chain − 0.03 and mean context ≤ 0.7× chain (≤ 2,124 characters). If it passes, one answer run is made (about 0.23 USD, an exception because the aim is cost, not gain) and k=3 is adopted if the paired score difference against `dev_004_hybrid` is ≥ −0.02 and tokens per question ≤ 0.8× the chain's. Otherwise k stays 5.
- If neither variant is adopted, k stays 5.

## 4. LLM budget

- Retrieval-only runs: query embeddings only (a few cents at most). Answer run only for a passing k=3 (or a passing k=8 with headroom): answers 90 + judge 90 (about 0.23 USD) each.
- Calls so far in the project: 1,366 (submission/PROCESS.md ledger, after `dev_004_hybrid`).

## 5. LLM-free results

| Config | evid (dev) | Net vs chain (+/−) | Context chars |
|---|---|---|---|
| k=3 | | | |
| k=5 (chain) | 0.853 | – | 3,034 |
| k=8 | | | |

- Details: _..._
- Gates passed? _..._

## 6. Answer run (only if the gates passed)

_..._

## 7. Decision and notes

- Decision: _..._
- Why, with question IDs: _..._
- What the criteria missed, if anything: _..._
