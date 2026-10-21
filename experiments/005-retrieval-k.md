<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 005: Number of retrieved chunks k = 3 / 5 / 8

Status: decided (k stays 5 by the criteria; k=8 missed the context cap by 1.0%; no answer run)
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
| k=3 | 0.772 | 0 up / 16 down, net −16 | 1,758 (0.58×) |
| k=5 (chain) | 0.853 | – | 3,034 |
| k=8 | 0.896 | 8 up / 0 down, net +8 | 4,599 (1.52×) |

Runs `dev_005_k3_retrieval`, `dev_005_k8_retrieval` (2026-10-21, 74 dev questions with gold pages). Other numbers (k=3 / 5 / 8): `page_hit` 0.973 / 0.986 / 0.986, `gold` 1.62 / 2.11 / 2.45. Questions with all evidence in context: 39 / 50 / 55; with none: 4 / 2 / 2.

- k=3 worsened: POS026 POS044 POS050 POS052 POS051 POS059 POS058 POS061 POS070 POS078 POS079 ADD-HP04 ADD-RP05 ADD-HF05 ADD-SE03 ADD-IN10 (none improved, as expected for fewer chunks).
- k=8 improved: POS047 POS050 POS059 POS064 ADD-RP06 ADD-HF10 ADD-IN01 ADD-IN08 (none worsened).
- Gates: **k=8**: `evid` +0.043 passes (≥ +0.03), net +8 passes (≥ 5), context 4,599 characters is over the cap 4,551 (1.516× vs 1.5×) → **fails the cap**, rejected by the rule; no headroom check. **k=3**: context 0.58× passes, `evid` 0.772 is under the floor 0.823 (chain − 0.03) → **fails**; no answer run.

## 6. Answer run (only if the gates passed)

Not run: neither variant passed its gate. LLM calls used: 0.

## 7. Decision and notes

- Decision by the criteria: **k stays 5.** MMR was not run (see section 1).
- Why, with question IDs: k=3 loses evidence for 16 questions and improves none, for 42% less context; k=8 is the best of the three on evidence (+0.043, 8 questions better, none worse, 55 questions with all evidence in context vs 50) but costs 52% more context characters and misses the pre-registered cap by 48 characters on average (1.0%). The cap was not changed after seeing the number.
- Open option for the owner: adopting k=8 despite the cap is a cost-for-evidence trade (about +1,560 characters, roughly +40% answer-input tokens, estimated from the characters; not measured) with no answer-level measurement. If adopted by the owner, the chain answer run `dev_004_hybrid` is no longer the baseline and the answer-model comparison (card 007) should be rerun on k=8.
- What the criteria missed, if anything: nothing was changed after the results. A cap of exactly 1.5× made the decision hinge on a 1% margin.
