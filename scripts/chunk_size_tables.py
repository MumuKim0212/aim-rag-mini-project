"""Tables for card 001 section 5 from results/ (no LLM calls): evid@5 and related metrics per chunk size, per set,
and for the question groups the card targets (PROCESS.md section 6). Run after evaluate.py for every variant.

    python scripts/chunk_size_tables.py
"""

import json
import statistics as st
import sys

import _paths  # noqa: F401
from rag import ROOT

sys.stdout.reconfigure(encoding="utf-8")


def load(n):
    return {r["qid"]: r for r in map(json.loads, (ROOT / "results" / n / "metrics.jsonl").open(encoding="utf-8"))}
names = {"800 (baseline)": "dev_000_baseline"} | {str(s): f"dev_001_chunk{s}_retrieval" for s in (300,400,600,1000,1200)}
M = {k: load(v) for k, v in names.items()}
base = M["800 (baseline)"]
q74 = [q for q, r in base.items() if r.get("evid@5") is not None]
def mean(M1, key, qs): 
    v = [M1[q][key] for q in qs if M1[q].get(key) is not None]; return sum(v)/len(v)
print("n evid questions", len(q74))
print("size | evid@5 | evid@3 | evid@10 | page_hit@5 | gold@5 | chars(74)")
for k, M1 in M.items():
    print(k, *[f"{mean(M1,m,q74):.3f}" for m in ("evid@5","evid@3","evid@10","page_hit@5","gold@5","chars")])
print("\nby set evid@5 (n):")
sets = sorted({base[q]["set"] for q in q74})
for s in sets:
    qs=[q for q in q74 if base[q]["set"]==s]
    print(s, len(qs), *[f"{k.split()[0]}={mean(M1,'evid@5',qs):.3f}" for k,M1 in M.items()])
targets = {"glossary(4)": ["POS001","POS006","POS013","POS021"]}
print("\nglossary 4: page_hit@5 / evid@5")
for q in targets["glossary(4)"]:
    print(q, [(k.split()[0], M1[q]["page_hit@5"], round(M1[q]["evid@5"],2) if M1[q].get("evid@5") is not None else None) for k,M1 in M.items()])
grp = {"근거 일부 누락 13": "ADD-HF06 ADD-HF07 ADD-HP09 ADD-IN10 ADD-PF01 ADD-RP05 ADD-RP06 ADD-SE06 ADD-SE08 POS047 POS050 POS061 POS078".split(),
       "과잉 보류 5": "ADD-PF08 ADD-PF09 POS045 POS057 POS058".split(),
       "검색 실패 7": "POS001 POS006 POS013 POS021 POS052 ADD-HF10 ADD-SE04".split()}
for g, qs in grp.items():
    print("\n", g)
    for k, M1 in M.items():
        v=[M1[q].get("evid@5") for q in qs if M1[q].get("evid@5") is not None]
        full=sum(1 for q in qs if M1[q].get("evid@5")==1.0)
        ph=sum(M1[q]["page_hit@5"] for q in qs if M1[q].get("evid@5") is not None)
        print(f"  {k:15s} mean evid@5 {sum(v)/len(v):.3f}  evid=1: {full}/{len(qs)}  page_hit@5 {ph}/{len(v)}")
