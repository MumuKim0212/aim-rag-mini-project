<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 011: Answer model back to gemini-3.5-flash-lite, prompt tuned for it

Status: decided (lite + prompt v4 is the best lite setting by point estimate; T2 stays on 3.6-flash until the owner decides)
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

## 5. Results

### L1 `dev_011_lite_v2` (lite + prompt v2; dev 90, 0 errors, answer 0.123 USD)

- Score **0.822** (fully correct 64 of 90, status match 93.3%, citation on gold page 94.6%) against 0.861 / 69 for 3.6-flash (`dev_010_answerv2`). Paired: lite better 5 (NEG011 NEG037 POS070 POS074 POS078), 3.6-flash better 9 (ADD-HF10 ADD-HP10 ADD-IN08 NEG013 NEG039 POS044 POS047 POS054 POS061), 76 same; diff −0.039, CI [−0.089, +0.011]. Answer cost 0.42×, p90 latency 3.0 s.
- Lite's 26 imperfect answers (read in full): (1) one dense paragraph that leaves out a part of the question or the evidence's conditions (POS047 POS054 POS059 POS061 POS066 POS076 ADD-HP09 ADD-HP10 ADD-HF10 ADD-IN04 ADD-PF01 ADD-PF08); (2) abstains or clarifies although part of the evidence is in context (POS044 ADD-IN08 ADD-SE06); (3) answers instead of asking for an unspecified account (NEG013 NEG014); (4) adds figures that are not in the results (POS050 "T+2", POS061 "50%"); (5) planned dates / proposals read as in force (NEG037 ADD-HF06).
- `answer_v3.md` was written from these (frozen before its run, see the file header).

### L2 `dev_011b_lite_v3` (lite + prompt v3; dev 90, 0 errors)

- Score **0.844** (fully correct 67, status match 94.4%, citation on gold page 96.0%). Paired against L1: v3 better 8 (ADD-HF10 ADD-IN08 ADD-PF01 ADD-SE06 NEG037 NEG039 POS044 POS047), L1 better 4 (ADD-HF06 ADD-HP10 POS058 POS078), diff +0.022, CI [−0.022, +0.067], net +4. Against 3.6-flash v2: −0.017, CI [−0.067, +0.033], net −2. Answer cost 1.17× L1 (0.49× of 3.6-flash), p90 3.1 s.
- By the choosing rule (net ≥ 5): +4 does not qualify; v3 is not chosen on its own.
- General failure pattern in the v3 changes: the refusal rule, now first in the order, sent answerable questions to `refused` (POS078 scam-case question, NEG039, ADD-HP06) and the risk statement leaked into normal answers. `answer_v4.md` (v3 with a narrowed rule ① only) is the last allowed version.

### L3 `dev_011c_lite_v4` (lite + prompt v4; dev 90, 0 errors after resuming one read timeout)

- Score **0.856** (fully correct 67, status match 95.6%, citation on gold page 93.2%). Paired against L2 (v3): v4 better 6 (ADD-HF06 ADD-HP10 POS054 POS058 POS061 POS078), v3 better 4 (ADD-HF10 ADD-IN01 POS022 POS057), diff +0.011, CI [−0.022, +0.044], net +2. Against L1 (v2): better 9 (ADD-IN08 ADD-PF01 ADD-SE06 NEG037 NEG039 POS044 POS047 POS054 POS061), worse 4 (ADD-IN01 POS022 POS057 POS078), diff +0.033, CI [−0.011, +0.072], net +5. Against 3.6-flash + v2 (0.861): diff −0.006, CI [−0.050, +0.044], 6 better / 7 worse, not distinguishable.
- Answer cost per question 0.00164 USD vs 0.00329 (0.50×); p90 latency 3.7 s vs 4.3 s; tokens 3,762 vs 3,376.

## 6. Answer run
See section 5 (three lite runs, 90 answers + 90 judge each, one resumed call).

## 7. Decision and notes

- By the criteria: v4 against L1 meets net ≥ 5 (+5) and drops no fully correct answer beyond the limit (ADD-IN01, POS022, POS078 were 2 under v2, 3 drops ≤ 5), so v4 is the chosen lite prompt; against its immediate predecessor v3 the gain is +2, inside the noise, so the v3 → v4 step alone is "not distinguishable". The lite setting is 0.822 → 0.844 → 0.856; the distance to 3.6-flash (0.861) is not distinguishable at this size, at half the answer cost.
- Honest limits: v3 and v4 were written from dev answers of this same set, so 0.856 is optimistic (the 9 gains include NEG037 NEG039 POS044 POS047 which were named when v3 was written); the unbiased check is the test. The loop is closed (v3, v4 used; no v5).
- Not done: `configs/008b`/T2/T3 were not switched. If the owner wants lite in the final system, T2 becomes `configs/011c-lite-v4.yaml` (and T3 follows) and PROCESS.md §9 must be updated before the test.
