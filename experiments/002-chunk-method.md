<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 002: Structure-unit chunking vs Recursive (H1)

Status: planned
Date: 2026-10-21

## 1. Hypothesis

- Change (one variable): chunking method. `configs/002-structure.yaml` (`chunking.method: structure`, `max_chars: 1600`) against Recursive 800/100. Rules (`src/rag/chunking.py`, `structure`):
  - Glossary: one chunk per term + definition. Term boundaries are the 228 terms of the glossary's own source list, matched in order against the body lines (all 228 match exactly).
  - Standard terms (15 PDFs): one chunk per article (`제N조(제목)`, also `제N조 (제목)`, `제N조의M`), plus one preamble chunk (title, base date, version). Article counts equal the entries of each PDF's source list (checked for all 15, `tests/test_chunking_structure.py`). An article over 1,600 characters is cut before a paragraph mark (①…); 7 chunks stay above 1,600 because they have no mark (e.g. the definitions article of 08 with 2,979 characters). Articles run over page breaks: `page` = start page, `pages` = all pages; `evalkit.metrics.is_gold` counts every listed page (backward compatible: baseline chunks have one page).
  - Other documents (financial life guide and the 6 additional PDFs): unchanged, Recursive 800/100. The "guide by heading" part of H1 (PLAN.md §1) is **not** tested here: those documents have no uniform heading markup, and one method per document family would be a different experiment.
- Failure it targets: glossary retrieval misses POS001, POS006, POS013, POS021 (a definition buried in an 800-character chunk with about 8 other terms, PROCESS.md §1.3 and §6) and partial evidence in terms questions POS047, POS050 (missing second article/page); POS052 (needs 02약관 p.1 and p.6).
- Expected effect: `evid@5` rises on `base_*` questions (34 of the 74 dev questions with gold pages; questions of the other sets cannot change because their documents are untouched, except when they retrieve glossary/terms chunks). Chunks are much smaller (glossary median about 90 characters, terms median about 270), so the context shrinks a lot at k=5; that is a side effect of the method, reported and not corrected. Risk: short glossary chunks may crowd out other relevant pages in scope B.

## 2. Measurement

- Baseline run (reused, not rerun): `dev_000_baseline`
- Proxy metric (step 4): `evid@5` (same reasons as card 001). Also: `page_hit@5`, `mrr`, `gold@5`, context characters. Chunk-level, no retrieval: **cut quotes** = evidence quotes of dev questions that no single chunk contains in full (`scripts/chunk_stats.py`, after squash), per config over all chunks of the scope.
- Split: dev, the 74 questions with gold pages. Indexes: scope A for `base_*`, scope B for the other sets.
- Noise (step 3): (a) 14 of 90 answers changed on a rerun, (b) 3 of 90 on a regrade; retrieval is deterministic for a fixed index.
- Not looked at: test split, self-written golden set. The three questions seen during the pre-check (POS001, POS020 in dev, NEG001 in test) were seen with the baseline only.

## 3. Go/no-go criteria (written before results)

- LLM-free gate: mean `evid@5` ≥ baseline + 0.03 (0.697 → 0.727) **and** questions with higher `evid@5` minus questions with lower ≥ 5, **and** cut quotes fewer than the baseline's.
- Context cap: mean context characters ≤ 1.5× baseline (≤ 4,596). A smaller context passes.
- Headroom gate: `evalkit.headroom --metric evid@5 --noise 14`: upside − risk > 14. If not, no answer run.
- Cost cap (answer run): tokens per question ≤ 1.3× baseline (3,790), p90 latency ≤ 3.0 s.
- Adopt if (answer run): paired net wins ≥ 9, more than 14 questions changed, 95% CI of the score difference excludes 0, no more garbled outputs than the baseline run's (`scripts/garble_scan.py`).
- Before an answer run, the answer step must show a cross-page chunk with all its pages (`render_context` prints only `page`; `map_citations` returns only `page`), otherwise `citation_on_target` is biased against this method. That code change would be made first and the comparison with the baseline noted in this card.
- If 001 adopted a chunk size, this card still compares against the 800/100 baseline run (the "other documents" part uses 800/100). Whether the two adoptions combine is decided in section 7.

## 4. LLM budget

- Planned calls if the gates pass: answers 90 + judge 90 (about 0.23 USD); 0 if they fail. Indexes and the retrieval-only run use embeddings only (about 0.14 USD).
- Calls so far in the project: 826 (submission/PROCESS.md ledger, 2026-10-21)

## 5. LLM-free results

| Config | Proxy metric (dev) | Net vs baseline (+/−) | Context chars / est. tokens |
|---|---|---|---|
| baseline | 0.697 | – | 3,064 |
| structure | | | |

- Cut quotes: baseline _N_, structure _N_
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
