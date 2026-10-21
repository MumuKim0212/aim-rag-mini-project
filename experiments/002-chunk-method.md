<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 002: Structure-unit chunking vs Recursive (H1)

Status: llm-free done (gates passed except headroom; answer run needs an explicit waiver from the project owner)
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
| structure | 0.795 | 11 up / 1 down, net +10 | 2,512 |

Run `dev_002_structure_retrieval` (2026-10-21, 74 dev questions with gold pages). Other numbers (baseline → structure): `page_hit@5` 0.878 → 0.959, `mrr` 0.800 → 0.901, `gold@5` 1.92 → 2.11. Questions with `evid@5` = 1: 34 → 42; with 0: 11 → 5. Chunks: scope A 309 → 633, scope B 1,212 → 1,536 (glossary median about 90 characters, terms median about 270).

- Improved: POS001 POS006 POS013 POS017 POS021 POS044 POS047 POS050 POS052 POS057 POS058 (all four glossary misses POS001 POS006 POS013 POS021 are among them). Worsened: POS026. Questions outside `base_*` did not change.
- Cut quotes (`scripts/chunk_stats.py`, dev, scope A + B): baseline 1 + 6 = 7, structure 0 + 6 = 6. The 6 in scope B (ADD-HF10 ADD-HP09 ADD-PF09 POS061 POS076 POS078) are in documents this experiment does not change.
- Headroom (`evid@5`, noise 14): upside 9 (POS001 POS006 POS013 POS021 POS047 POS050 POS052 POS057 POS058), already correct among improved 2, risk 1 (POS026). Upside − risk = 8 ≤ 14.
- Gates passed? LLM-free gate yes (+0.098, net +10, cut quotes 7 → 6), context cap yes (2,512 = 0.82× baseline), headroom gate **no** (8 ≤ 14). Section 6 is skipped.

## 6. Answer run (only if the gates passed)

Not run (headroom gate). LLM calls used: 0. Embedding cost: index builds 0.138 USD, scopes A and B.

## 7. Decision and notes

- Decision: **inconclusive for now, not adopted.** By the criteria above no answer run is allowed (CLAUDE.md: no batch LLM run without passed gates), so the structure chunking cannot enter the adopted chain by the "adopt if" rule. Whether to run the answer run anyway is a decision for the project owner (see below).
- Why, with question IDs: retrieval clearly improves on the questions this method targets — 11 better, 1 worse (POS026), `evid@5` = 0 questions 11 → 5, with a smaller context. The headroom gate fails because only 9 improved questions are not already fully answered (the baseline answers POS017 and POS044 fully), and the rule needs more than 14. H1 is supported at the retrieval level for glossary and terms documents only; it is not tested for the guide documents (not implemented) and not tested at the answer level.
- Not investigated: why POS026 got worse (the glossary lists "공매도" twice, dicId 1859 and 1865, with the same definition — POS026 and POS043 ask about it; I did not check whether two near-identical chunks take two of the five slots).
- What the criteria missed, if anything: nothing was changed after the results. The headroom bar of 14 is as high as the answer-level noise, and this change can touch at most the 34 `base_*` questions, so even a clean retrieval gain would not pass it. A waiver, if given, must be recorded here with the date and who gave it, and the answer run must use a new experiment name.
