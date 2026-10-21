<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 011: Answer model back to gemini-3.5-flash-lite, prompt tuned for it

Status: running
Date: 2026-10-21

## 1. Hypothesis

- Requested by the project owner on 2026-10-21: "lower the answer model to 3.5 flash lite, fit the prompt to it, make it as high as possible". Purpose: a cheaper answer model that keeps as much of the 0.861 as possible.
- Change: answer model `gemini-3.6-flash` → `gemini-3.5-flash-lite` in the final chain (structure + 950/119, hybrid k=5). Retrieval, judge (`judge_v1`, `gemini-3.6-flash`) and everything else unchanged.
  - L1 `configs/011-lite-v2.yaml`: lite with the existing prompt `answer_v2.md` (isolates the model effect).
  - L2 `configs/011b-lite-v3.yaml`: lite with `answer_v3.md`, written after reading the L1 answers that lost points against `dev_010_answerv2` (what lite does differently from 3.6-flash).
  - L3 `answer_v4.md` only if L2 leaves a clear, general failure pattern; the loop stops after v4.
- Honest limits: (1) v3/v4 are written from dev answers, so the dev gain is optimistic; the test is the unbiased check. (2) The judge is `gemini-3.6-flash`; with a lite answer model the self-preference concern of card 007 is smaller, not larger. (3) The 3.6-flash result (0.861) and the lite result are single runs, noise 14 of 90.
- Expected effect: lite drops below 0.861 (earlier lite chain results were 0.772 with v1 on the 900 chain vs 0.822 for 3.6-flash on the same chain); a prompt that is more explicit about format and rules may recover part of the gap.

## 2. Measurement

- Runs: `dev_011_lite_v2`, `dev_011b_lite_v3` on dev, 90 questions, one run each. Reference: `dev_010_answerv2` (0.861, 69 fully correct).
- Metrics: score paired per question, fully correct count, status match, citation on gold page, tokens and USD per question, p90 latency, garbled outputs (kana; `garble_scan.py` is invalid for thinking models, so count kana directly).
- Not looked at: test split, self-written golden set.

## 3. Go/no-go criteria (written before results)

- Goal metric: dev answer score of the lite chain; the reference to approach is 0.861. No hard bar for "adopt" because the owner asked for the lite model; the card reports how far it gets.
- Choosing among L1, L2, L3: the prompt with the highest score is chosen only if paired against the previous lite prompt net wins ≥ 5 and the number of previously fully correct answers that drop is ≤ 5; otherwise the earlier prompt stays (v3 and v4 cannot be chosen by a gain inside the noise of 14).
- Cost cap: answer USD per question ≤ 1.0× that of `dev_010_answerv2` (it should be far lower with lite); p90 latency ≤ 5 s.
- At most two new prompt versions (v3, v4). The target 1.0 does not extend this limit. The best prompt is frozen before the test.
- A gain inside the noise is described as "not distinguishable".

## 4. LLM budget

- Answers 90 + judge 90 per version; up to 3 versions (L1, L2, L3), about 0.15–0.35 USD each.
- Calls so far in the project: 2,820 (submission/PROCESS.md ledger, 2026-10-21)
