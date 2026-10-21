<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 010: Answer prompt v2 (aim: as many fully correct answers as possible)

Status: planned
Date: 2026-10-21

## 1. Hypothesis

- Change (one variable): answer prompt `prompts/answer_v1.md` → `prompts/answer_v2.md` in the final RAG chain (`configs/010-answer-v2.yaml`: structure + 950/119, hybrid k=5, `gemini-3.6-flash`). v1 stays frozen for T1. The agent's generate node uses the same prompt file, so if v2 is adopted the agent config of T3 follows (`configs/008b-agent-950.yaml` would point to v2).
- Requested by the project owner on 2026-10-21: "fix the prompt and aim for 1.0". A score of 1.0 is a target, not an expectation: the judge changes 3 of 90 grades on a regrade and a rerun changes 14 of 90 answers.
- Failure it targets (the 23 imperfect answers of `dev_001e_chunk950chain`: 5 zero, 18 one, read in full): (1) answers that leave out a part of the question or the conditions, caveats and limits that the evidence states (1-point answers: POS037 POS045 POS047 POS050 POS059 POS076 POS078 ADD-HP02 ADD-HP09 ADD-SE08 ADD-IN04 ADD-IN08 ADD-PF08); (2) over-abstention with partial evidence in context (POS051 POS074 ADD-SE06); (3) refusals without the risk statement (NEG022 NEG023 NEG025); (4) answering instead of asking when the question does not say which account or market (NEG013 NEG014); (5) saying "not in the documents" when it is, or reading a proposal as enforced (POS079 ADD-HF06).
- Honest limit: v2 was written after reading these answers, so the dev result is optimistic for these questions. The unbiased check is the final test (T1 uses v1, T2 uses the adopted prompt).
- Expected effect: fewer 1-point answers and fewer wrong abstentions; risk: longer answers that add content the judge's `must_not_include` forbids, and over-clarifying.

## 2. Measurement

- Baseline run (reused): `dev_001e_chunk950chain` (answers and grades), same retrieval and answer model. Judge fixed (`judge_v1`, `gemini-3.6-flash`). Split: dev, 90 questions, one run. Noise: 14 of 90 changed in a rerun, net −8.
- Metrics: score paired per question; split into the 67 questions that were fully correct before (regressions = how many drop) and the 23 that were not (gains); `status_ok`; by set; answer length (output tokens per question); USD and p90 latency; garbled outputs (kana).
- Not looked at: test split, self-written golden set.

## 3. Go/no-go criteria (written before results)

- v2 is adopted if, paired against `dev_001e_chunk950chain`: net wins ≥ 9, more than 14 questions changed, 95% CI of the score difference excludes 0, no more than 5 of the 67 previously fully correct questions drop below 2, output tokens per question ≤ 1.5× baseline, p90 latency ≤ 5 s. Otherwise v1 stays.
- At most two prompt versions are tried (v2, then v3 only if v2 shows a clear, general failure pattern in the regressions). The target 1.0 does not extend this limit; the loop stops after v3 and the best adopted prompt is frozen before the test.
- A gain inside the noise is described as "not distinguishable".

## 4. LLM budget

- Answers 90 + judge 90 per version (about 0.36 USD). Up to 2 versions.
- Calls so far in the project: 2,640 → 2,820 after v2.

## 5. Results

_..._

## 6. Decision and notes

- Decision: _..._
- Why, with question IDs: _..._
