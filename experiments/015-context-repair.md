<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 015: Agent context repair — diagnose why evidence is missing, expand cut chunks to the page, re-check

Status: decided (gate failed, smoke only)
Date: 2026-10-22
Owner: LimDaeJin (branch `LimDaeJin/card-015-context-repair`, based on `serin-91/chunking-cards-001-002`)

## 1. Hypothesis

- Change (one variable): the agent's grade step diagnoses the cause of missing evidence and repairs the context
  before answering. Everything else is the T3 agent (`configs/008b-agent-950.yaml`): same classify / rewrite /
  generate / cite_check nodes and prompts, same retrieval (950/119 structure, hybrid + LLM rerank 15 → 5),
  same answer model (`gemini-3.6-flash`) and answer prompt (`answer_v4`).
  - `grade` → `diagnose` (`prompts/agent_diagnose_v1.md`): sufficient, plus when insufficient a cause
    `cut` (the right document and page, but the chunk stops mid-sentence / mid-table) | `not_found` (another
    document or article is needed) | `garbled` (the text itself is broken), and the result numbers that are relevant
  - `cut` → new node `expand_context` (code, no LLM): the relevant chunks are replaced by their whole page from
    `corpus/pages.jsonl`, at most once per question and 3 pages, total context ≤ 20,000 characters; then
    `diagnose` runs again on the repaired context (the re-check)
  - `not_found` → the existing `rewrite` → `retrieve` loop
  - `garbled` → new node `flag_page` (code): the page goes to `steps.repair_queue` for offline re-extraction
    (not done inside the graph: re-chunking changes the index, which would break the comparison), then `generate`
  - New code lives in `src/rag/agent_repair.py` (subclass of `rag.agent.Agent`) and `system: agent_repair`;
    no existing prompt, config, golden set, or result is changed
- Failure it targets: evidence cut at chunk boundaries. On the 1000/125 recursive chain (LimDaeJin card-008
  branch, `dev_008_agent`), 23 of 74 answerable dev questions had the target page in context but evid < 1, and
  page expansion raised evid on 13 of them. Structure chunking (950/119) should cut less; the headroom below
  measures how much is left on this chain.
- Expected effect: small. At most the not-fully-correct questions whose evidence page expansion recovers.

## 2. Measurement

- Baseline (reused, not rerun): `dev_008b_agent950` (T3 agent on dev, 0.939). T2 reference: `dev_013_rerank_flash36_fix` (0.928)
- LLM-free headroom (computed from `results/dev_008b_agent950/runs.jsonl` + `corpus/pages.jsonl`, no LLM):
  replace every chunk of the baseline's final context by its whole page and recompute `evid`
  (`evalkit.metrics.context_metrics`). upside = questions not fully correct (score < 2) whose evid rises;
  already-correct questions whose evid rises are reported separately (they cannot gain)
- Answer-run metrics: judge score paired per question (`scripts/compare.py`), status_ok, citation_on_target;
  diagnose cause distribution, number expanded / flagged, evid before vs after expansion on expanded questions;
  LLM calls, USD, p50/p90 latency
- Split: dev 90 only. The provided test split and the self-written sets are not run (final test is done; RESUME.md)
- Noise: 14 of 90 changed in a rerun (PROCESS §4)

## 3. Go/no-go criteria (written before results)

- LLM-free gate: upside ≥ 3 questions. Otherwise skip the dev answer run and decide from the headroom
  (implementation and the smoke check are still done)
- Better than the T3 agent if, paired against `dev_008b_agent950`: net wins ≥ 9, more than 14 questions changed,
  95% CI excludes 0 (same rule as cards 008 / 014)
- Cost cap: USD/question ≤ 1.5 × `dev_008b_agent950` (0.0109 → 0.0163), p90 latency ≤ 15 s
- The final system is **not** changed by this card (T4 chosen by the owner, test split not run again).
  The result is reported as a tried change in PROCESS / AGENT_GRAPH

## 4. LLM budget

- Index build for the 950/119 chain on this PC (embeddings, no generation): about 0.15 USD
- Smoke check: 3 dev questions (not graded), about 15 calls
- If the gate passes: `dev_015_context_repair` about 4.6 calls / question ≈ 415 + judge 90, about 1.3 + 0.14 USD

## 5. LLM-free results

Computed 2026-10-22 from `results/dev_008b_agent950` (final context of each question, every chunk replaced by its page).

| | Questions |
|---|---|
| Answerable dev questions | 74 |
| Target page in context but evid < 1 (cut evidence) | 12 (23 on the 1000/125 recursive chain) |
| Page expansion raises evid, not fully correct (upside) | **2**: ADD-HP09 (0.70 → 0.75, score 1), ADD-SE06 (0.67 → 1.00, score 1) |
| Page expansion raises evid, already fully correct | 3 |
| Not fully correct in the baseline | 10 |
| Context chars per question, chunks → whole pages | 3,032 → 6,751 |

- Gate (upside ≥ 3): **not passed** (2). The dev answer run is skipped; section 6 stays empty
- Structure chunking already removed most cuts: 12 cut questions vs 23 on the recursive chain, and only 2 of them
  are among the 10 questions the T3 agent still gets wrong

## 6. Answer run

Skipped: the LLM-free gate failed (section 5).

Smoke check only (3 dev questions, not graded, not in `out/runs.db`; index for the 950/119 chain built on this PC,
`A-41303e2739` 633 chunks, `B-4cc3daa594` 1,426 chunks):

| qid | Path | LLM calls | USD |
|---|---|---|---|
| ADD-HP09 | classify → retrieve → diagnose (**cut**, results 1–2) → **expand_context** (housing_pension_2026 p.50, p.105; 4,425 chars) → diagnose (sufficient) → generate → cite_check | 5 | 0.0157 |
| ADD-SE06 | classify → retrieve → diagnose (sufficient) → generate → cite_check | 4 | 0.0130 |
| POS001 | classify → retrieve → diagnose (sufficient) → generate → cite_check | 4 | 0.0063 |

- The repair path works end to end: the re-check after expansion is the second diagnose call
- ADD-HP09's expansion added p.105 (a target page) but its other target p.16 was never retrieved; the cut
  diagnosis repaired the page it saw, not the one it lacked. This is the kind of question where expansion alone
  cannot reach the missing evidence (not_found would have)

## 7. Decision and notes

- Decision: **not run on dev, not adopted** (gate: upside 2 < 3). The T3 agent stays the agent of the write-up;
  the final system (T4) is unchanged
- Why: on the final chain structure chunking already removed most cut evidence (12 cut questions vs 23 on the
  1000/125 recursive chain), and only 2 of the 10 questions the T3 agent gets wrong could gain from page expansion
- What stays useful: `system: agent_repair` is implemented and tested (tests/test_agent_repair.py) without
  changing any existing prompt, config, golden set or result; the graph is drawn with
  `python scripts/show_graph.py --config configs/015-context-repair.yaml`. On a chain with more cut evidence
  (recursive chunking) the gate would be worth recomputing first
- `flag_page` / `steps.repair_queue` is the hook for the offline loop (re-extract and re-chunk flagged pages under a
  new card); no page was flagged in the smoke check
