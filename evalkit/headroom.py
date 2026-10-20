"""Headroom and risk check. Run it BEFORE spending LLM calls on an answer run (workflow step 6).

A change can only raise answer scores on questions the current setup gets wrong, and can only lower
them on questions it currently gets (partly) right. Given the baseline's per-question answer scores and
an LLM-free proxy metric measured before and after the change:

- upside : metric improved, baseline score below max   -> questions the change could fix
- spent  : metric improved, baseline already at max    -> improvement lands where there is nothing to gain
- risk   : metric worsened, baseline score above 0     -> questions the change could break

If len(upside) - len(risk) is not larger than the measured noise, an answer run cannot show a gain:
skip it and record why. Upside is a ceiling, not a forecast; more context can also distract the answer.

    python -m evalkit.headroom --scores grades_base.jsonl --max-score 2 \
        --before context_metrics.jsonl --before-where config=chunk5 \
        --after context_metrics.jsonl --after-where config=page \
        --metric evid_full --noise 5
"""

import argparse

from . import load_jsonl, parse_where, to_map


def headroom(scores: dict, before: dict, after: dict, max_score: float, higher_is_better: bool = True) -> dict:
    """scores: {qid: baseline answer score}; before/after: {qid: proxy metric value}."""
    sign = 1 if higher_is_better else -1
    qids = sorted(scores.keys() & before.keys() & after.keys())
    improved = [q for q in qids if sign * (after[q] - before[q]) > 0]
    worsened = [q for q in qids if sign * (after[q] - before[q]) < 0]
    return {
        "n": len(qids),
        "improved": len(improved),
        "worsened": len(worsened),
        "upside": [q for q in improved if scores[q] < max_score],
        "spent": [q for q in improved if scores[q] >= max_score],
        "risk": [q for q in worsened if scores[q] > 0],
    }


def passes(result: dict, noise: int) -> bool:
    return len(result["upside"]) - len(result["risk"]) > noise


def report(r: dict, noise: int | None = None) -> str:
    lines = [
        f"n={r['n']}  metric improved {r['improved']}, worsened {r['worsened']}",
        f"upside {len(r['upside'])} (improved, baseline not fully correct): {' '.join(r['upside'])}",
        f"spent  {len(r['spent'])} (improved, baseline already fully correct)",
        f"risk   {len(r['risk'])} (worsened, baseline scored above 0): {' '.join(r['risk'])}",
    ]
    if noise is not None:
        net = len(r["upside"]) - len(r["risk"])
        verdict = "run the answer evaluation" if passes(r, noise) else "skip the answer run: it cannot show a gain"
        lines.append(f"upside - risk = {net} vs noise {noise}: {verdict}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Headroom/risk check before an answer run.")
    parser.add_argument("--scores", required=True, help="baseline grades (JSONL with qid and score field)")
    parser.add_argument("--field", default="correctness", help="score field in --scores")
    parser.add_argument("--max-score", type=float, default=1.0, help="score of a fully correct answer (2 for 0/1/2)")
    parser.add_argument("--before", required=True, help="proxy metric per question for the baseline (JSONL)")
    parser.add_argument("--after", required=True, help="proxy metric per question for the change (JSONL)")
    parser.add_argument("--metric", required=True, help="metric field, e.g. evid_full or gold@5")
    parser.add_argument("--where", nargs="*", default=[], help="key=value filters for --before and --after")
    parser.add_argument("--before-where", nargs="*", default=[], help="key=value filters for --before only")
    parser.add_argument("--after-where", nargs="*", default=[], help="key=value filters for --after only")
    parser.add_argument("--lower-is-better", action="store_true", help="for metrics like rank or length")
    parser.add_argument("--noise", type=int, default=None, help="questions changed in the step-3 noise run")
    args = parser.parse_args()

    scores = to_map(load_jsonl(args.scores), args.field)
    before = to_map(load_jsonl(args.before, parse_where(args.where, args.before_where)), args.metric)
    after = to_map(load_jsonl(args.after, parse_where(args.where, args.after_where)), args.metric)
    result = headroom(scores, before, after, args.max_score, higher_is_better=not args.lower_is_better)
    print(report(result, args.noise))


if __name__ == "__main__":
    main()
