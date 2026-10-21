"""Where can retrieval still gain? Diagnostics for the adopted setup, embedding calls only (no LLM answer or judge
calls; about 150 query embeddings, well under 0.01 USD). Not an experiment: nothing is written to runs.db.

    python scripts/ceiling_diagnostics.py [--config configs/002-structure.yaml]

1. evidence coverage `evid` of the top-k chunks for k = 3, 5, 8, 10, 20, 50 (dev questions with gold evidence).
2. oracle reranker: from the top-N vector candidates (N = 20, 50) choose the best 5 chunks per question using the
   gold evidence (greedy cover). No real reranker can beat it, so it bounds what reranking could bring into the
   top 5 (submission/PROCESS.md section 7, "남은 개선 여지").
Only the dev split is read.
"""

import argparse
import json
import statistics as st
import sys

import _paths  # noqa: F401
from evalkit.metrics import context_metrics
from rag import ROOT, env, retrieval
from rag.config import load_config

KS = (3, 5, 8, 10, 20, 50)


def oracle_five(item: dict, units: list[dict]) -> float:
    chosen: list[int] = []
    for _ in range(5):
        best, best_score = None, -1.0
        for i, unit in enumerate(units):
            if i in chosen:
                continue
            score = context_metrics(item, [units[j] for j in chosen] + [unit])["evid"]
            if score > best_score:
                best, best_score = i, score
        chosen.append(best)
    return context_metrics(item, [units[j] for j in chosen])["evid"]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    env.setup()
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/002-structure.yaml")
    args = parser.parse_args()
    cfg = load_config(ROOT / args.config)
    golden = [g for g in map(json.loads, (ROOT / "golden" / "provided.jsonl").open(encoding="utf-8"))
              if g["split"] == "dev" and g.get("evidence") and g.get("targets")]
    retrievers = {scope: retrieval.load_retriever(cfg, scope) for scope in "AB"}
    at_k, oracle = {}, {20: {}, 50: {}}
    for item in golden:
        units = retrievers[cfg["corpus"]["set_scope"][item["set"]]].search_n(item["question"], max(KS), {})
        at_k[item["qid"]] = {k: context_metrics(item, units[:k])["evid"] for k in KS}
        for n in oracle:
            oracle[n][item["qid"]] = oracle_five(item, units[:n])
    print(f"{len(at_k)} dev questions with gold evidence, config {args.config}")
    for k in KS:
        values = [r[k] for r in at_k.values()]
        print(f"top-{k:<3d} evid mean {st.mean(values):.3f}   questions with complete evidence {sum(v == 1 for v in values)}")
    incomplete = [q for q, r in at_k.items() if r[5] < 1]
    print(f"\nincomplete at k=5: {len(incomplete)} questions")
    for k in (8, 10, 20, 50):
        print(f"  complete by top-{k}: {sum(at_k[q][k] == 1 for q in incomplete)}   improved: "
              f"{sum(at_k[q][k] > at_k[q][5] for q in incomplete)}   still zero: {sum(at_k[q][k] == 0 for q in incomplete)}")
    for n, values in oracle.items():
        print(f"oracle best 5 out of top-{n}: evid mean {st.mean(values.values()):.3f}, complete "
              f"{sum(v == 1 for v in values.values())}/{len(values)}; of the {len(incomplete)} incomplete: "
              f"complete {sum(values[q] == 1 for q in incomplete)}, improved {sum(values[q] > at_k[q][5] for q in incomplete)}")


if __name__ == "__main__":
    main()
