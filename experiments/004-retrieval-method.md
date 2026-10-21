<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 004: Retrieval method — vector vs BM25 vs Hybrid (H3)

Status: planned
Date: 2026-10-21

## 1. Hypothesis

- Change (one variable): `retrieval.method` on the adopted chain. The chain is card 002b's candidate B (structure units for glossary/terms, Recursive 900/112 for the rest), adopted as the improved RAG by the project owner on 2026-10-21 (by point estimate and cost, not by the adopt rule; PROCESS.md §7). Variants `configs/004-bm25.yaml` (BM25 over Kiwi content morphemes, no embedding) and `configs/004-hybrid.yaml` (vector and BM25, top 50 from each, min-max scaled, `hybrid_alpha` 0.5 weight on vector). The indexes of the chain are reused. Alpha is not tuned: no other value is tried.
- Failure it targets: evidence missing from the context. In the chain's dev answers (`dev_002b_structure900`), the remaining misses are listed in section 5 once the retrieval run is evaluated; the earlier baseline misses are in PROCESS.md §6 (situational questions ADD-HF10, ADD-SE04 were retrieval misses).
- Expected effect (H3, PLAN.md §1): exact-term questions (`base_positive`, glossary and terms) are matched better by BM25; situational questions (`additional`, `life_guide`) are matched better by vector search; hybrid is fine on both.

## 2. Measurement

- Baseline for this card: `dev_002b_structure900` (answers) and `dev_002b_structure900_retrieval` (retrieval-only): `evid@5` 0.838, context 2,700 characters, `page_hit@5` / `mrr` / `gold@5` from its summary.
- Proxy metric `evid@5` (card 001). Also `page_hit@5`, `mrr`, `gold@5`, context characters, and **per question set**: `base_positive` (and the 4 answerable `base_negative`), `life_guide`, `additional`.
- Split: dev, the 74 questions with gold pages. Retrieval is deterministic for a fixed index and query embedding; answer-level noise is 14 of 90.
- Known differences between the methods that are part of what is measured: BM25 sees the chunk text only (the vector side embeds `title: <document title> | text: …`); BM25 uses Kiwi 0.23.2 morphemes of nouns, verbs/adjectives, roots, foreign words, numbers, hanja.
- Not looked at: test split, self-written golden set.

## 3. Go/no-go criteria (written before results)

- LLM-free gate (per variant): mean `evid@5` ≥ chain + 0.03 (≥ 0.868) and (higher − lower) ≥ 5 questions, and mean context ≤ 1.5× chain (≤ 4,050).
- H3 reading (reported whatever the gate says): H3 is supported if BM25 − vector `evid@5` is positive on `base_positive` and negative on `additional` + `life_guide` together, and hybrid is within 0.02 of the better of the two in each group. Otherwise it is reported as not supported.
- Headroom gate for a passing variant: `evalkit.headroom --scores results/dev_002b_structure900/grades.jsonl --metric evid@5 --noise 14`: upside − risk > 14. If it fails or no variant passes, there is no answer run and the retrieval stays vector; the retrieval-level comparison is the result of this card (PLAN.md §3.2). No waiver is assumed.
- Answer run adopt rule (only if allowed): paired against `dev_002b_structure900` net wins ≥ 9, more than 14 questions changed, 95% CI excludes 0, tokens per question ≤ 1.3× the chain's, p90 latency ≤ 3.0 s; garbled-output count reported. If both variants adopt, the higher mean score; within 0.01 the cheaper.

## 4. LLM budget

- Retrieval-only runs: query embeddings only (vector and hybrid; BM25 none), well below 0.01 USD. Answer run only if allowed: answers 90 + judge 90 per adoptable variant (about 0.23 USD each).
- Calls so far in the project: 1,186 (submission/PROCESS.md ledger, after card 002b).

## 5. LLM-free results

| Config | evid@5 (dev) | Net vs chain (+/−) | Context chars |
|---|---|---|---|
| chain: vector | 0.838 | – | 2,700 |
| bm25 | | | |
| hybrid α=0.5 | | | |

- Per set: _..._
- H3 reading: _..._
- Headroom: _..._

## 6. Answer run (only if allowed)

_..._

## 7. Decision and notes

- Decision: _..._
- Why, with question IDs: _..._
- What the criteria missed, if anything: _..._
