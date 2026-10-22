"""Shared loaders and labels for the lab report app. Everything here reads committed files (results/, golden/,
corpus/, configs/, experiments/); only the agent pages build agents, and only the live page calls the API."""

import json
import re
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

RESULTS = ROOT / "results"

# Final-test systems (submission/EVALUATION.md, PROCESS §9) and their dev counterparts
SYSTEMS = {
    "T1": ("처음 RAG", "test_000_baseline", "dev_000_baseline"),
    "T2": ("개선된 RAG (큰 모델)", "test_013_rerank_flash36", "dev_013_rerank_flash36_fix"),
    "T3": ("Agent (큰 모델)", "test_008b_agent950", "dev_008b_agent950"),
    "T4": ("최종 시스템 (작은 모델)", "test_013b_rerank_lite", "dev_013b_rerank_lite_fix"),
}
LABELS = {
    "dev_000_baseline": "T1 처음 RAG",
    "dev_013_rerank_flash36_fix": "T2 개선된 RAG",
    "dev_008b_agent950": "T3 Agent",
    "dev_013b_rerank_lite_fix": "T4 최종 (작은 모델)",
    "dev_014_agent_v2": "Agent v2 (메모+검토)",
    "test_000_baseline": "T1 처음 RAG",
    "test_013_rerank_flash36": "T2 개선된 RAG",
    "test_008b_agent950": "T3 Agent",
    "test_013b_rerank_lite": "T4 최종 (작은 모델)",
}
SETS = {"base_positive": "기본 질문", "base_negative": "함정 질문", "life_guide": "생활 가이드", "additional": "추가 자료",
        "self": "자작(20)", "self2": "자작 v2(41)"}
STATUS = {"answered": "답변", "abstained": "보류", "clarify": "되묻기", "refused": "거절", "retrieval_only": "검색만",
          "error": "오류"}
SCORE_COLS = {
    "correctness_mean": "정답 점수", "fully_correct": "완전 정답률", "status_ok": "대응 일치율",
    "citation_on_target": "출처 일치율", "page_hit@5": "정답 페이지 포함", "evid@5": "근거 문장 포함률",
    "gold@5": "정답 청크 수", "mrr": "MRR", "usd_per_question": "USD/문항", "llm_per_question": "LLM 호출/문항",
    "p50": "p50 초", "p90": "p90 초", "chars": "문맥 글자 수",
}


def label(exp: str) -> str:
    return f"{LABELS[exp]} · {exp}" if exp in LABELS else exp


@st.cache_data
def jsonl(path: str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


@st.cache_data
def summary(exp: str) -> dict:
    p = RESULTS / exp / "summary.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def experiments() -> list[str]:
    return sorted(p.parent.name for p in RESULTS.glob("*/summary.json"))


def has(exp: str, name: str) -> bool:
    return (RESULTS / exp / name).exists()


def rows(exp: str, name: str) -> list[dict]:
    return jsonl(str(RESULTS / exp / name))


@st.cache_data
def summary_table() -> pd.DataFrame:
    out = []
    for exp in experiments():
        s = summary(exp)
        sc, rt, co, ca, la = (s.get(k) or {} for k in ("scores", "retrieval", "cost", "calls", "latency_s"))
        kind = "검색만" if s.get("retrieval_only") else ("Agent" if str(s.get("system", "")).startswith("agent") else "RAG")
        out.append({
            "실험": exp, "이름": LABELS.get(exp, ""), "split": s.get("split"), "종류": kind, "문항 수": s.get("n_questions"),
            "정답 점수": sc.get("correctness_mean"), "완전 정답률": sc.get("fully_correct"),
            "대응 일치율": sc.get("status_ok"), "출처 일치율": sc.get("citation_on_target"),
            "정답 페이지 포함": rt.get("page_hit@5"), "근거 문장 포함률": rt.get("evid@5"), "MRR": rt.get("mrr"),
            "문맥 글자 수": rt.get("chars"), "USD/문항": co.get("usd_per_question"),
            "LLM 호출/문항": ca.get("llm_per_question"), "p50 초": la.get("p50"), "p90 초": la.get("p90"),
            "카드": s.get("card"), "설명": s.get("description"), "기준": s.get("compare_to"),
            "만든 시각": s.get("created_at"),
        })
    return pd.DataFrame(out)


def graded(split: str | None = None) -> list[str]:
    return [e for e in experiments() if has(e, "grades.jsonl") and (split is None or e.startswith(split + "_"))]


@st.cache_data
def final_frame(system: str) -> pd.DataFrame:
    """One row per final-test question of system T1..T4: provided test 90 + self-written v2 41 (EVALUATION.md);
    the archived 20-question `self` set is left out, as in the write-up."""
    test = SYSTEMS[system][1]
    metrics = rows(test, "metrics.jsonl") + rows(test + "_self2", "metrics.jsonl")
    grades = {r["qid"]: r for r in rows(test, "grades.jsonl") + rows(test + "_self2", "grades.jsonl")}
    out = {}
    for m in metrics:
        if m["set"] == "self":
            continue
        g = grades.get(m["qid"], {})
        out[m["qid"]] = {**m, "correctness": g.get("correctness"), "reason": g.get("reason")}
    return pd.DataFrame(list(out.values()))


def final_stats(system: str) -> dict:
    df = final_frame(system)
    ans = df[df["behavior_group"] == "answer"]
    return {"n": len(df), "정답 점수": df["correctness"].mean() / 2, "완전 정답률": (df["correctness"] == 2).mean(),
            "대응 일치율": df["status_ok"].mean(), "출처 일치율": df["citation_on_target"].mean(),
            "보류율 (답변 가능)": (ans["status"] != "answered").mean(),
            "평균 초": df["latency_s"].mean(), "p90 초": df["latency_s"].quantile(0.9),
            "LLM 호출/문항": df["n_llm_calls"].mean(), "USD/문항": df["usd"].mean()}


@st.cache_data
def golden() -> dict:
    items = {}
    for name in ("provided.jsonl", "self.jsonl", "self2.jsonl"):
        for it in jsonl(str(ROOT / "golden" / name)):
            items.setdefault(it["qid"], it)
    return items


@st.cache_data
def pages() -> list[dict]:
    return jsonl(str(ROOT / "corpus" / "pages.jsonl"))


def paired(a: str, b: str, metric: str | None = None) -> dict:
    """evalkit.paired.compare on grades (score 0-2) or on a metrics.jsonl column."""
    from evalkit.paired import compare
    if metric:
        ma = {r["qid"]: r[metric] for r in rows(a, "metrics.jsonl") if r.get(metric) is not None}
        mb = {r["qid"]: r[metric] for r in rows(b, "metrics.jsonl") if r.get(metric) is not None}
        top = 5.0 if metric.startswith("gold@") else 1.0
        return compare(ma, mb, max_score=top)
    ga = {r["qid"]: r["correctness"] for r in rows(a, "grades.jsonl")}
    gb = {r["qid"]: r["correctness"] for r in rows(b, "grades.jsonl")}
    return compare(ga, gb, max_score=2.0)


@st.cache_data
def cards() -> list[dict]:
    out = []
    for p in sorted((ROOT / "experiments").glob("[0-9]*.md")):
        text = re.sub(r"<!--.*?-->", "", p.read_text(encoding="utf-8"), flags=re.S).strip()
        title = next((l[2:].strip() for l in text.splitlines() if l.startswith("# ")), p.stem)
        status = next((l.split(":", 1)[1].strip() for l in text.splitlines() if l.startswith("Status:")), "")
        out.append({"file": p.name, "title": title, "status": status, "text": text})
    return out


def pct(x) -> str:
    return "–" if x is None or pd.isna(x) else f"{x:.3f}"


def kpi_row(items: list[tuple[str, str, str | None]]):
    cols = st.columns(len(items))
    for col, (name, value, help_) in zip(cols, items):
        col.metric(name, value, help=help_)


@st.cache_resource
def agent_of(config: str):
    from rag.config import load_config
    from rag.systems import build_system
    cfg = load_config(ROOT / config)
    return build_system(cfg), cfg


@st.cache_data(show_spinner="흐름도를 그리는 중…")
def mermaid_png(mermaid: str) -> bytes | None:
    try:
        from langchain_core.runnables.graph_mermaid import draw_mermaid_png
        return draw_mermaid_png(mermaid)
    except Exception:
        return None


def show_mermaid(mermaid: str):
    png = mermaid_png(mermaid)
    if png:
        st.image(png)
    else:
        st.warning("mermaid.ink 에 연결할 수 없어 mermaid 원문을 보여 줍니다. https://mermaid.live 에 붙여 넣으면 그림으로 볼 수 있습니다.")
        st.code(mermaid, language="text")
