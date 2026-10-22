# RESUME (2026-10-22, deadline today)

## State
- Branch `serin-91/chunking-cards-001-002`, pushed at `897ef4b`. No PR yet (to `main`). Untracked `pilot/` is not ours.
- Final system T4 = structure chunking + Hybrid + LLM rerank 15->5 + `gemini-3.5-flash-lite` + `answer_v4` (`configs/013b-rerank-lite.yaml`). Chosen by the owner for price.
- Final test, 131 q (provided test 90 + `golden/self2.jsonl` 41): score T1 0.718, T2 0.889, T3 0.916, T4 0.855; USD/q 0.0012 / 0.0090 / 0.0131 / 0.0036.
- Done: `submission/EVALUATION.md`, PROCESS 2.5/9/10 + ledger (6,490 calls), README, Streamlit (`app/streamlit_app.py`, port 8501, only AppTest-checked, not eyeballed).

## Next (3)
1. Open the PR; body = final system, score table, test split used twice (T4 rerun on provided test 90, chosen for price).
2. Final sweep: grep submission/ for "예정" and `_..._`; AGENT_GRAPH dev numbers vs final; fresh-env `pytest` + `pip install -r requirements.txt`.
3. Do NOT run the test split again, edit frozen prompts/golden, or start new experiments.

## Rules that bite
- First 20-q set `golden/self.jsonl` is archived (T2 scored 1.0); never use it in comparisons. `configs/baseline.yaml` stays frozen (editing it changes index keys -> FileNotFoundError); self2 scope lives in `golden.EXTRA_SCOPE`.
- Judge = `gemini-3.6-flash` (same as T2/T3 answer model); POS011 was a judge error (0 for a number that is in the source). Do not write "human review not done" wording; state what was checked.

## Blocked
- Nothing. Open question: PR approval from the owner.
