<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 004: Retrieval method — vector vs BM25 vs Hybrid (H3)

Status: decided (gate outcome: no variant passed; owner adopted hybrid into the chain on 2026-10-21)
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
| bm25 | 0.732 | 12 up / 19 down, net −7 | 2,967 |
| hybrid α=0.5 | 0.853 | 10 up / 7 down, net +3 | 3,034 |

Runs `dev_004_bm25_retrieval`, `dev_004_hybrid_retrieval` (2026-10-21, 74 dev questions with gold pages, indexes of the chain reused). Other numbers (vector / bm25 / hybrid): `page_hit@5` 1.000 / 0.878 / 0.986, `mrr` 0.927 / 0.770 / 0.906, `gold@5` 2.14 / 1.59 / 2.11. Questions with `evid@5` = 1: 47 / 42 / 50; with 0: 3 / 10 / 2. Search time p90: BM25 0.02 s, hybrid 0.75 s (query embedding included).

- Per set, `evid@5` (vector / bm25 / hybrid): base_positive + 4 answerable base_negative (n=34) 0.962 / 0.798 / 0.951; life_guide (n=10) 0.744 / 0.651 / 0.796; additional (n=30) 0.729 / 0.684 / 0.762.
- bm25 improved: POS026 POS054 POS070 POS074 ADD-RP05 ADD-RP06 ADD-HF05 ADD-HF06 ADD-SE03 ADD-SE06 ADD-PF08 ADD-PF09; worsened: POS017 POS044 POS047 POS045 POS050 POS051 POS058 POS059 NEG019 POS061 POS064 POS078 ADD-HP04 ADD-HP09 ADD-HP10 ADD-SE04 ADD-IN08 ADD-IN10 ADD-PF05.
- hybrid improved: POS026 POS054 POS070 POS074 POS079 ADD-RP05 ADD-HF05 ADD-SE03 ADD-SE06 ADD-PF08; worsened: POS047 POS045 POS050 POS059 POS064 ADD-HF10 ADD-IN08.
- H3 reading: **not supported.** BM25 − vector on the exact-term questions (`base_positive`) is −0.164, i.e. BM25 is clearly worse there, not better; on `additional` + `life_guide` it is also lower (0.676 vs 0.733). Hybrid is within 0.02 of the better method in both groups (0.951 vs 0.962; 0.771 vs 0.733), but that part alone does not rescue H3.
- Gates: bm25 fails (−0.106, net −7). Hybrid fails (+0.015 < +0.03, net +3 < 5). Context cap holds for both (3,034 ≤ 4,050). No headroom check and no answer run (nothing passed).

## 6. Answer run (only if allowed)

Chain answer run `dev_004_hybrid` (hybrid α 0.5, the owner-adopted chain), dev 90, 0 errors, 2026-10-21; it is also the baseline answer run for cards 005, 007 and 008. Calls: 90 answers + 90 judge (about 0.23 USD).

| | Vector chain `dev_002b_structure900` | Hybrid chain `dev_004_hybrid` | Original baseline `dev_000_baseline` |
|---|---|---|---|
| Answer score (0–1) | 0.756 | **0.772** | 0.722 |
| Paired vs the vector chain | – | 13 better / 9 worse / 68 same, diff +0.017, CI [−0.044, +0.078], net +4 | – |
| Paired vs the original baseline | – | 17 / 9 / 64, diff +0.050, CI [−0.028, +0.128], net +8 | – |
| Tokens / question | 2,622 | 2,813 (1.07×) | 2,916 |
| USD / question (answer) | 0.00107 | 0.00115 | 0.00116 |
| p90 latency | 1.88 s | 3.51 s (see below) | 2.07 s |
| Garbled outputs | 0 | 1 (NEG008, abstained) | – |

- Hybrid better than the vector chain: ADD-HF07 ADD-PF09 ADD-RP01 ADD-RP05 ADD-RP07 ADD-SE03 NEG009 NEG022 POS022 POS037 POS045 POS054 POS057; worse: ADD-HF06 ADD-HP06 ADD-HP10 ADD-IN01 ADD-IN08 NEG039 POS017 POS052 POS061. Net +4 is inside the noise (14 changed questions in a rerun): the answer-level effect of hybrid is not distinguishable from zero.
- Latency: the four slowest runs in run order are the first four questions (3.5–4.2 s) and a few more above 3 s early on: the BM25 index of each scope is tokenized (Kiwi) on first use and that time is counted in the question's latency. Without the first 12 questions in run order the p50 is 1.72 s and the p90 2.19 s (vector chain 1.58 s / 2.07 s overall). The run's p90 of 3.51 s exceeds the 3.0 s cap used in earlier cards; the steady-state figure is 2.19 s. The harness was not changed to exclude warm-up.

## 7. Decision and notes

- Decision by the criteria: **bm25 rejected; hybrid not adopted (retrieval would stay vector search, k=5).** The retrieval comparison PLAN.md §3.2 asks for is done at the retrieval level.
- **Owner decision (2026-10-21): hybrid (α 0.5) is adopted into the chain**, chosen by the highest point estimate (0.853) and the most questions with all evidence in context (50), not by the gate. Later cards use `configs/004-hybrid.yaml` as their base. Its answer-level effect is measured by the chain answer run `dev_004_hybrid` (section 6).
- Why, with question IDs: the chain's glossary and terms chunks are short, title-prefixed units that the embedding already matches almost perfectly on term questions (`base_positive` 0.962); BM25 loses 12 questions the vector search gets right there and elsewhere (e.g. POS044 POS047 POS050 POS058 POS059) and wins 12 (POS026 POS054 POS070 POS074 ADD-RP05 ADD-RP06 ADD-HF05 ADD-HF06 ADD-SE03 ADD-SE06 ADD-PF08 ADD-PF09). Hybrid keeps the vector strengths and picks up some of BM25's wins (POS026 POS054 POS070 POS074 ADD-RP05 ADD-HF05 ADD-SE03 ADD-SE06 ADD-PF08) and raises the number of questions with all evidence in context from 47 to 50, but loses 7 and the gain (+0.015, 3 questions net) is below both bars.
- Not tested: other `hybrid_alpha` values (pre-registered as not tuned), BM25 text with the title prefix, a different BM25 tokenizer. A hybrid that wins on dev by tuning alpha would be a pick among several tries on 74 questions.
- What the criteria missed, if anything: nothing was changed after the results. The BM25 side differs from the vector side by more than the method (no title prefix, Kiwi morphemes), so "BM25 is worse" means this BM25 configuration.
