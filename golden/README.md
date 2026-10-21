<!--
GUIDE: Rules for the golden set in this folder. The golden set file(s) live next to this README
(e.g. golden_set.jsonl, plus a review log). Update the "This project" section when the set is built.
Keep guide comment in place after filling in.
-->

# Golden set

The golden set is the yardstick for every decision. Mistakes in it look like system failures, so build it carefully and keep a review log.

**Never add the golden set to the search index.**

## Format (one JSON object per line)

```json
{
  "qid": "Q001",
  "split": "dev",
  "question": "…",
  "answerable": true,
  "target_answer": "…",
  "evidence": ["verbatim quote copied from the extracted page text", "…"],
  "targets": [{"file": "report.pdf", "page": 12}],
  "domain": "finance",
  "context_type": "paragraph",
  "question_type": "fact",
  "note": ""
}
```

- `evidence`: verbatim quotes, copied from the extracted text of the target page, not paraphrased. `evalkit.metrics` matches them line by line after normalization; this is what makes evidence coverage computable without an LLM.
- `targets`: every page that contains the answer. A question needing two documents gets one target per document.
- `answerable: false` questions have no targets or evidence; put the reason in `note`. They measure correct refusal.
- `context_type` (text / paragraph / table / image) and `question_type` let results be broken down later. Add fields you will want to slice by now; adding them later means re-reviewing.

## Review checklist

- [ ] Every evidence quote auto-matches the target page's extracted text (normalize with NFKC and strip whitespace). A failing quote means a wrong page, a typo, or an extraction problem — all worth knowing before step 2.
- [ ] Same content elsewhere (a press release and its attachment, a ruling and its appendix): list all those pages as targets, or the page metrics will count a correct retrieval as a miss.
- [ ] No question depends on unstated context ("원고가…", "이 사건", "해당 표", "세 가지 주제"). Rewrite it to stand alone or drop it.
- [ ] Reference answers checked against the source, not just copied from a provided set. Record every fix (question, answer, page) in a review log.
- [ ] Some questions phrased like real users: short, vague, using words the document does not use. Questions written while looking at the page are easy to retrieve and overstate quality.
- [ ] A set of unanswerable questions, including near-misses (the document covers the topic but not the asked fact).
- [ ] File names normalized (Unicode NFC) on both sides of every comparison.

## Splits

- Split before building the system, stratified by domain and context type.
- All tuning and decisions use dev. Test is run once, at the end — this includes LLM-free retrieval metrics.
- Size dev so the differences you care about exceed the noise measured in step 3.

## This project

Files (read by `src/rag/golden.py`; both are frozen once a run has used them — a fix means a new version and a note in `submission/PROCESS.md`):

| File | Contents | Split |
|---|---|---|
| `provided.jsonl` | 180 provided questions converted to the format below | dev 90 / test 90, stratified by set × difficulty (× category for negatives); seed recorded in `review_log.md` |
| `self.jsonl` | Self-written set (submission/PLAN.md §2.3), draft of 20 questions written 2026-10-22 (15 answerable, 5 not; `evidence_reviewed: false` until a human checks it; see `review_log.md`) | all `test`, evaluated only at workflow step 8 |
| `review_log.md` | Every fix to a question, reference answer, or page, with the reason; split seed | – |

Fields used in this project, on top of the general format above:

| Field | Values |
|---|---|
| `qid` | provided `case_id` (`POS001`, `NEG001`, `ADD-HP01`), self-written `SELF001`… |
| `set` | `base_positive`, `base_negative`, `life_guide`, `additional`, `self` — decides the index scope (`configs/baseline.yaml` `corpus.set_scope`) |
| `expected_behavior` | provided value; self-written questions use the same vocabulary. Allowed system statuses per value: `BEHAVIORS` in `src/rag/golden.py` (review it during conversion; `tests/test_golden.py` checks coverage) |
| `must_include`, `must_not_include`, `difficulty`, `category` | copied from the provided answers; given to the judge |
| `source_ids` | the provided `expected_source_ids`, kept for traceability |
| `targets` | `[{"file": <file name, NFC>, "page": <1-based>}]`, converted from `source_ids` and checked against the PDF (submission/PLAN.md §2.2) |
| `evidence` | verbatim quotes from `corpus/pages.jsonl` text of the target pages; must auto-match |

Extra fields written by `scripts/convert_golden.py`: `evidence_pages` (`{file, page, source}` per quote, source
`text` = PDF text layer, `vlm` = VLM supplement in corpus/pages.jsonl), `evidence_source`, `source_kind`
(glossary / terms / page), `context_type` (text / paragraph / table / chart), `evidence_reviewed`, `note`,
plus `source_file` / `source_locator` for the additional set. `golden/evidence.jsonl` holds the hand-reviewed
quotes (and `extra_targets`) the converter reads; edit that file, not provided.jsonl.

**provided.jsonl, built 2026-10-20** (seed 20261020; details and every fix in `review_log.md`)

| Set | dev | test | answerable (dev / test) |
|---|---|---|---|
| base_positive | 30 | 30 | 30 / 30 |
| base_negative | 20 | 20 | 4 / 4 (correction cases with sources) |
| life_guide | 10 | 10 | 10 / 10 |
| additional | 30 (5 per document) | 30 (5 per document) | 30 / 30 |

- Difficulty and `context_type` are balanced per split (life guide basic/intermediate off by one; odd strata).
- 353 evidence quotes for 148 answerable items, all auto-matching; 19 items also use VLM quotes, checked against
  the page images. 0 reference answers or questions changed.
- `kofia-terms-X-V-A`: A is the article's position in the terms PDF's source list, not its article number (they
  differ in 02_파생상품계좌설정약관, which has 제10조의2·3).
- Known weaknesses: 34 questions assume a document context ("이 자료", "책에서"); POS079's table is split across two
  pages and only text-layer fragments cover it; 71 items have several target pages (read `evid` next to `page_hit`).
