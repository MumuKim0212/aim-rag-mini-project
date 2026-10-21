<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 008: Basic RAG vs Agent (H4)

Status: decided (dev: agent not better by the criteria; final system = basic RAG chain; T3 still runs on test)
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

Run `dev_008_agent` (2026-10-21, dev 90, 0 errors) against `dev_007_flash36`.

| | Basic RAG `dev_007_flash36` | Agent `dev_008_agent` |
|---|---|---|
| Answer score (0–1) | 0.822 | **0.856** |
| Fully correct / status match / citation on a gold page | 71.1% / 94.4% / 93.2% | 74.4% / 96.7% / 95.9% |
| Paired vs RAG (better / worse / same) | – | 7 / 4 / 79, diff +0.033, CI [−0.011, +0.083], net +3, 11 changed |
| By set (base_pos / base_neg / life_guide / additional) | 0.883 / 0.800 / 0.750 / 0.800 | 0.933 / 0.850 / 0.750 / 0.817 |
| LLM calls / question | 1.0 | 3.16 |
| Searches / question | 1.0 | 1.14 (81 questions 1 search, 5 two, 4 three) |
| Tokens / question | 2,842 | 5,818 (2.05×) |
| USD / question (answer side) | 0.00262 | 0.00506 (1.94×) |
| p50 / p90 latency | 2.65 s / 4.15 s | 5.52 s / 9.12 s (9.17 s without the first 12 questions) |
| Garbled outputs (kana) | 0 | 0 |

- Agent better: ADD-HF06 ADD-IN08 NEG022 NEG034 POS051 POS059 POS074; RAG better: ADD-HP06 ADD-SE04 POS070 POS079.
- Question types from classify: document 74, inappropriate 8, injection 4, needs_info 4. cite_check found no invalid citation (no retry in any question).
- Context (74 gold questions): first search `evid` 0.853 (identical to the RAG's, as designed) → final context 0.868; `page_hit` 0.986 → 0.986; context 3,189 characters vs 3,034.
- Re-search happened for 9 questions (grade said "insufficient" for 9 of 90): POS059 POS058 NEG009 NEG034 POS074 ADD-HF06 ADD-IN01 ADD-SE06 ADD-IN08. Their score RAG → agent: POS059 1→2, POS074 0→2, ADD-HF06 0→2, ADD-IN08 1→2, NEG034 1→2, the other four unchanged (ADD-SE06 stays 0). `evid` of the gold-page ones went up for POS059 (0.83→1.0), POS074 (0.35→0.65), ADD-SE06 (0.33→0.56), ADD-IN08 (0.57→1.0).
- Attribution: of the 7 improved questions, 3 cite a chunk that only re-search found (POS059 POS074 ADD-IN08); 2 more were re-searched without citing a new chunk (NEG034, ADD-HF06); 2 had no re-search (POS051, NEG022), so those 2 are generation/classification variation, not re-search. Of the 4 worse, none had a re-search.
- Subsets (descriptive): questions with two or more gold pages (35): 0.771 → 0.814; `base_negative` (20): 0.800 → 0.850 with the same status match (90%); behavior groups: refuse (5) 0.70 → 0.80, injection (3) 0.83 → 1.0, clarify (4) 0.50 → 0.50.
- Cost: agent 0.456 USD + judge 0.127 USD for 284 + 90 calls.

## 6. Decision and notes

- Decision by the criteria: **the agent is not better than basic RAG on dev** (net +3 vs 9 required, 11 changed vs more than 14, CI includes 0). The final system to hand in is therefore **the basic RAG chain (T2)**; T3 is still run on test as required, and reported as it is.
- Why, with question IDs: the agent's +0.033 is inside the noise of a rerun (14 changed questions, net −8). Re-search, the part of the structure that targets the main dev failure, ran for only 9 of 90 questions because grade judged the first 5 chunks sufficient for the others; it helped POS059 POS074 ADD-IN08 (cited re-searched chunks) and left ADD-IN01, ADD-SE06, NEG009, POS058 unchanged. The signs on negative questions and multi-page questions agree with H4 (0.80 → 0.85, 0.77 → 0.81) but are 1–3 questions each. The cost side of H4 holds: about 2× USD, 3.2× calls, 2.2× p90 latency. The 2 improvements without re-search (POS051, NEG022) and the 4 losses (ADD-HP06 ADD-SE04 POS070 POS079) show the same kind of answer variation as the rerun noise.
- Limits: one run, 90 dev questions; the classify node only skips grading (it does not route to separate refuse / clarify / abstain nodes); grade, classify, rewrite use the answer model; max re-search 2 and context cap 10 were fixed before the run and not tuned. A different agent design (for example one that always re-searches multi-document questions) was not tried.
- What the criteria missed, if anything: nothing was changed after the results. T3 − T2 on test measures the structure on the final chain only.
