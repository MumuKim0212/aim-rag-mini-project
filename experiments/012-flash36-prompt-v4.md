<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 012: Answer prompt v4 on gemini-3.6-flash

Status: running
Date: 2026-10-21

## 1. Hypothesis

- Requested by the project owner on 2026-10-21: run v4 on 3.6 flash for a fair comparison with lite + v4 (card 011), since lite got two prompt versions and 3.6 flash only v2.
- Change (one variable): answer prompt `answer_v2.md` → `answer_v4.md` (written for lite, frozen) in `configs/012-flash36-v4.yaml` (final chain, `gemini-3.6-flash`). No new prompt version is written; the prompt-version limit of card 011 is not extended.
- Expected effect: 3.6 flash follows the explicit rules at least as well as lite, so 0.86–0.88; inside the noise of 14 of 90 is likely.
- Limit: v4 was written from dev answers, so any dev gain is optimistic; the test is the unbiased check.

## 2. Measurement

- Run `dev_012_flash36_v4`, dev 90, one run. References: `dev_010_answerv2` (3.6 flash + v2, 0.861, 69 fully correct), `dev_011c_lite_v4` (lite + v4, 0.856, 67).
- Metrics as in card 011. Not looked at: test split, self-written golden set.

## 3. Go/no-go criteria (written before results)

- v4 replaces v2 for 3.6 flash only if, paired against `dev_010_answerv2`: net wins ≥ 5, no more than 5 of the 69 fully correct answers drop below 2, answer USD per question ≤ 1.5× and p90 latency ≤ 5 s. Otherwise v2 stays for 3.6 flash.
- Which model goes into T2 is an owner decision; this card reports the paired numbers of 3.6 flash + best prompt vs lite + v4 (gain inside the noise is "not distinguishable").

## 4. LLM budget

- Answers 90 + judge 90 (about 0.5 USD).
- Calls so far in the project: 3,361 (submission/PROCESS.md ledger, 2026-10-21)
