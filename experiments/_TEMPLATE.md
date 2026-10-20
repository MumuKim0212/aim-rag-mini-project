<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# NNN: _title_

Status: _planned / llm-free done / answer run done / decided_
Date: _YYYY-MM-DD_

## 1. Hypothesis

- Change (one variable): _e.g. pass whole pages instead of 5 chunks to the answer step_
- Failure it targets: _bucket from step 5, with question IDs_
- Expected effect: _what should move, and roughly how much_

## 2. Measurement

- Baseline run (reused, not rerun): _experiment name_
- Proxy metric (step 4): _name, and why_
- Split: dev
- Noise (step 3): _(a) X of N, (b) Y of N_

## 3. Go/no-go criteria (written before results)

- LLM-free gate: _proxy metric net gain ≥ __ questions on dev, larger than noise_
- Headroom gate: _upside − risk ≥ __ questions (evalkit/headroom.py)_
- Cost cap: _context / tokens ≤ __× baseline, p90 latency ≤ __ s_
- Adopt if (answer run): _paired net wins ≥ __ and 95% CI excludes 0 (or: same direction as an independent earlier run)_

## 4. LLM budget

- Planned calls if the gates pass: _answers __ + judge ___
- Calls so far in the project: _see submission/PROCESS.md ledger_

## 5. LLM-free results

| Config | Proxy metric (dev) | Net vs baseline (+/−) | Context chars / est. tokens |
|---|---|---|---|
| baseline | | – | |
| _variant_ | | | |

- Headroom: upside _N_ (_qids_), already correct among improved _N_, risk _N_ (_qids_)
- Gates passed? _yes / no — if no, skip section 6 and decide in section 7_

## 6. Answer run (only if the gates passed)

- Experiment name: _..._
- Paired vs baseline: _B better N / A better N / same N, diff ±0.000, 95% CI [_, _]_
- Tokens / latency vs baseline: _..._
- LLM calls used: _answers __ + judge ___

## 7. Decision and notes

- Decision: _adopt / reject / inconclusive_
- Why, with question IDs: _..._
- What the criteria missed, if anything: _..._
