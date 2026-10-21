"""Count escape-garbled answers in logged runs, without LLM calls (POS054 pattern, submission/PROCESS.md 6절).

gemini-3.5-flash-lite sometimes writes the JSON answer string as \\uXXXX escapes and picks the wrong code points,
so the visible text is nonsense (kana, pseudo-Korean). The visible answer is short but the call's output tokens are
not: escapes cost several tokens per character. Normal answers use 0.6-1.0 output tokens per answer character.

    python scripts/garble_scan.py dev_000_baseline dev_000_baseline_r2 [more experiments]

Flags a run when the answer contains kana or the generate calls' output tokens (thinking tokens excluded: a
model that thinks, like gemini-3.1-flash-lite, would otherwise be flagged for every short answer) exceed 2 per
visible answer character. Report the count next to every answer-run result (decision 2026-10-21: PROCESS.md 6절).
"""

import re
import sys

import _paths  # noqa: F401
from evalkit.runlog import RunLog
from rag import ROOT

KANA = re.compile(r"[぀-ヿ]")
TOKENS_PER_CHAR = 2.0


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    log = RunLog(ROOT / "out" / "runs.db")
    for experiment in sys.argv[1:]:
        runs = log.latest(experiment)
        flagged = []
        for r in runs:
            body = (r["answer"] or "").split("\n\n출처:")[0]
            # output_tokens includes thinking tokens; escapes are written output, so thinking is subtracted
            tokens = sum(c["output_tokens"] - c.get("thinking_tokens", 0) for c in r["steps"]["calls"]
                         if c.get("kind") == "llm" and c["node"] == "generate")
            if KANA.search(body) or (body and tokens / len(body) > TOKENS_PER_CHAR):
                flagged.append((r["qid"], len(body), tokens, r["status"]))
        print(f"{experiment}: {len(flagged)}/{len(runs)} flagged", flagged)


if __name__ == "__main__":
    main()
