<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 008: Basic RAG vs Agent (H4)

Status: planned
Date: 2026-10-21

## 1. Hypothesis

- Change: the system. Agent (`configs/008-agent.yaml`, `src/rag/agent.py`, graph in `submission/AGENT_GRAPH.md`) against the final RAG chain `dev_007_flash36`: same corpus and chunking (structure + 900/112), same hybrid retrieval k=5, same answer prompt `answer_v1`, same answer model `gemini-3.6-flash` (`thinking_level: low`), same judge. The agent adds: classify (question type, 1 LLM call), grade (is the evidence enough, 1 call per search), rewrite + re-search (at most 2 times, 1 call each), cite_check (code; one more generate call if a citation number is invalid or an `answered` result has none). Classify nodes use the answer model too (`agent.node_models` all null). Re-searched chunks are added to the context, which is capped at `agent.max_context` = 10 chunks (first search 5 + at most 5 new). Questions typed `needs_info` or `inappropriate` skip grading. The first search is the baseline's search for the same question.
- The draft's separate refuse / clarify / abstain nodes are not built: the shared answer step already writes those responses from retrieved context, and they need citations (see AGENT_GRAPH.md §6 after the run).
- Failure it targets (PROCESS.md §6): evidence missing from the context (retrieval misses and partial evidence) through grade + re-search; negative-question handling (NEG014 NEG025 NEG037 NEG039 and the content-poor NEG022 NEG023) through classify and the grade/abstain path.
- Expected effect (H4, PLAN.md §1): better than basic RAG on negative questions and on questions that need several pieces of evidence, at 2× the cost or more.

## 2. Measurement

- Baseline run (reused): `dev_007_flash36` (answers and grades). Judge fixed. Split: dev, 90 questions, one run. Noise: 14 of 90 changed in a rerun (net −8).
- Metrics: judge score paired per question (`scripts/compare.py`); `status_ok`; `citation_on_target`; by set, by negative behavior group and for questions with two or more gold pages; first-search context vs final context (`first_evid` vs `evid`, `first_page_hit` vs `page_hit`, `metrics.jsonl`); share of questions with re-search; for each question the agent answered better, whether it cited a chunk that only re-search found (`steps.cited_research_chunk`); LLM calls, tokens, USD, p50/p90 latency per question (warm-up of the first 12 questions reported separately); garbled outputs by kana.
- Not looked at: test split, self-written golden set.

## 3. Go/no-go criteria (written before results)

- The agent counts as better than basic RAG on dev if, paired against `dev_007_flash36`: net wins ≥ 9, more than 14 questions changed, and the 95% CI of the score difference excludes 0.
- The agent is the final system (T3 as the system to hand in) only if it is better by that rule **and** USD per question (answer + all agent calls) ≤ 6× the RAG's and p90 latency ≤ 15 s. Otherwise the final system is the basic RAG chain (T2). T3 is run on test either way, as PLAN.md §3.2 requires, and the result is reported as it is.
- Attribution is reported, not gated: among questions the agent improved, how many cite a chunk found only by re-search.
- Results are described as the effect of the whole structure; no claim about a single node (PLAN.md §3.2).

## 4. LLM budget

- About 3.6 LLM calls per question (classify 1, grade 1–3, rewrite 0–2, generate 1–2); 90 questions ≈ 320 calls, plus 90 judge calls. Estimated cost 1–1.5 USD (answer model price 0.75 / 3.75 USD per 1M tokens).
- Calls so far in the project: 1,906 (submission/PROCESS.md ledger).

## 5. Results

_..._

## 6. Decision and notes

- Decision: _..._
- Why, with question IDs: _..._
- What the criteria missed, if anything: _..._
