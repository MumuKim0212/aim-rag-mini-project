from collections import Counter

import altair as alt
import pandas as pd
import streamlit as st

from lab.common import SETS, has, label, paired, rows, summary

st.title("🤖 에이전트 비교 (dev 90문항)")
st.caption("같은 청킹·검색·답변 모델 위에서 그래프만 다른 에이전트들을 비교합니다. 기준은 같은 체인의 RAG(T2)입니다.")

CANDIDATES = ["dev_013_rerank_flash36_fix", "dev_008b_agent950", "dev_014_agent_v2"]
extra = st.text_input("다른 팀원 에이전트 실험 이름 추가 (쉼표로 구분, results/ 에 있어야 함)", "")
names = CANDIDATES + [e.strip() for e in extra.split(",") if e.strip() and has(e.strip(), "grades.jsonl")]


def run_stats(exp: str) -> dict:
    runs = rows(exp, "runs.jsonl")
    metrics = {m["qid"]: m for m in rows(exp, "metrics.jsonl")}
    steps = [r.get("steps") or {} for r in runs]
    decisions = [d for s in steps for d in s.get("decisions", [])]
    grades = [d for d in decisions if d.get("node") in ("grade", "diagnose") and "sufficient" in d]
    first = [m.get("first_evid") for m in metrics.values() if m.get("first_evid") is not None]
    final = [m.get("evid") for m in metrics.values() if m.get("first_evid") is not None]
    return {
        "재검색한 문항": sum(1 for r in runs if (r.get("n_searches") or 1) > 1),
        "근거 부족 판단 (횟수)": sum(1 for d in grades if not d["sufficient"]),
        "재검색 청크를 인용한 문항": sum(1 for s in steps if s.get("cited_research_chunk")),
        "첫 검색 근거 포함률": sum(first) / len(first) if first else None,
        "최종 문맥 근거 포함률": sum(final) / len(final) if final else None,
        "종료 이유": dict(Counter(s.get("termination_reason") for s in steps if s.get("termination_reason"))),
    }


table = []
for e in names:
    s = summary(e)
    sc, co, ca, la = s["scores"], s["cost"], s["calls"], s["latency_s"]
    row = {"실험": label(e), "정답 점수": sc["correctness_mean"], "완전 정답률": sc["fully_correct"],
           "대응 일치율": sc["status_ok"], "출처 일치율": sc["citation_on_target"], "USD/문항": co["usd_per_question"],
           "LLM 호출/문항": ca["llm_per_question"], "검색/문항": ca.get("searches_per_question"), "p90 초": la["p90"]}
    if e != CANDIDATES[0]:
        r = paired(CANDIDATES[0], e)
        row["T2 대비 순증"] = len(r["b_better"]) - len(r["a_better"])
        row["T2 대비 95% CI"] = f"[{r['ci95'][0]:+.3f}, {r['ci95'][1]:+.3f}]"
    table.append(row)
table = pd.DataFrame(table)
st.dataframe(table.style.format({c: "{:.3f}" for c in ["정답 점수", "완전 정답률", "대응 일치율", "출처 일치율"]}
                                | {"USD/문항": "{:.4f}", "LLM 호출/문항": "{:.2f}", "검색/문항": "{:.2f}", "p90 초": "{:.1f}",
                                   "T2 대비 순증": "{:+.0f}"}, na_rep="–"), width="stretch", hide_index=True)
st.caption("채택 규칙(카드 008·014): 기준 대비 순증 ≥ +9, 바뀐 문항 > 14, 95% 신뢰구간이 0을 포함하지 않음. "
           "점수가 구별되지 않으면 비용·속도·단순함으로 고릅니다.")

st.subheader("세트별 정답 점수")
by = pd.DataFrame([{"실험": label(e), "세트": SETS.get(k, k), "정답 점수": v["correctness_mean"]}
                   for e in names for k, v in (summary(e).get("by_set") or {}).items()])
st.altair_chart(alt.Chart(by).mark_bar().encode(
    y=alt.Y("실험:N", title=None), x=alt.X("정답 점수:Q", scale=alt.Scale(domain=[0, 1])), color="실험:N",
    row=alt.Row("세트:N", title=None), tooltip=["실험", "세트", "정답 점수"]))

st.subheader("에이전트가 실제로 한 일")
agents = [e for e in names if summary(e).get("system", "").startswith("agent")]
st.dataframe(pd.DataFrame({label(e): run_stats(e) for e in agents}).astype(str), width="stretch")
st.caption("첫 검색 근거 포함률은 기본 RAG와 같은 첫 검색, 최종 문맥 근거 포함률은 재검색까지 누적한 문맥 기준입니다. "
           "둘의 차이가 재검색으로 더 찾은 근거입니다.")
