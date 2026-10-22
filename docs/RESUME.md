# RESUME (2026-10-22, deadline today)

## State
- Branch `serin-91/chunking-cards-001-002` (includes `serin-91/agent-v2`, card 014). PR to `main`: see `gh pr list`.
- Final system T4 = structure chunking + Hybrid + LLM rerank 15->5 + `gemini-3.5-flash-lite` + `answer_v4` (`configs/013b-rerank-lite.yaml`), chosen by the owner for price.
- Final test 131 q: T1 0.718, T2 0.889, T3 0.916, T4 0.855 (EVALUATION.md).
- After the final test: card 014 agent v2 (memo + answer check + 1 revision) = 0.928 on dev, same as T2 -> not adopted. T3 ran on dev for the first time: 0.939.
- Done: EVALUATION, PROCESS (1.1 filled, 8, 10, 11, ledger 7,775 calls), AGENT_GRAPH section 7, RETROSPECTIVE.md, fresh-venv `pip install -r requirements.txt` + 42 tests pass (Python 3.13.16).

## Next (3)
1. Owner reviews and merges the PR.
2. Optional: eyeball the Streamlit app (only AppTest-checked) and the AGENT_GRAPH mermaid on GitHub.
3. Do NOT run the test split again, edit frozen prompts/golden, or start new experiments.

## Rules that bite
- `golden/self.jsonl` (first 20 q) is archived; never compare on it. `configs/baseline.yaml` stays frozen (index keys).
- Judge = `gemini-3.6-flash`, same as the T2/T3 answer model (limitation, EVALUATION section 7).

## Blocked
- Nothing.
