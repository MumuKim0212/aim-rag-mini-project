import altair as alt
import pandas as pd
import streamlit as st

from lab.common import SETS, golden, graded, label, paired, picked_compare, picked_note, picked_runs, rows, summary

st.title("⚖️ 두 실험 짝비교")
st.caption("같은 문항을 두 실험이 각각 몇 점 받았는지 문항별로 짝지어 비교합니다(`scripts/compare.py`와 같은 계산). "
           "agent_list에서 고른 agent(🤖)는 목록 맨 앞에 있습니다.")
picked_note()
if len(picked_runs()) >= 2:
    picked_compare("선택한 agent 전부 한 번에 비교")
    st.divider()
    st.subheader("두 개씩 자세히")

split = st.radio("split", ["dev", "test"], horizontal=True)
mine = [r["experiment"] for r in picked_runs()] if split == "dev" else []
names = mine + [e for e in graded(split) if e not in mine]
default_a = mine[0] if len(mine) >= 2 else ("dev_013_rerank_flash36_fix" if split == "dev" else "test_013_rerank_flash36")
default_b = mine[1] if len(mine) >= 2 else ("dev_008b_agent950" if split == "dev" else "test_008b_agent950")
c1, c2 = st.columns(2)
a = c1.selectbox("기준 (A)", names, index=names.index(default_a) if default_a in names else 0, format_func=label)
b = c2.selectbox("비교 (B)", names, index=names.index(default_b) if default_b in names else 1, format_func=label)
if a == b:
    st.warning("서로 다른 두 실험을 고르세요.")
    st.stop()

res = paired(a, b)
net = len(res["b_better"]) - len(res["a_better"])
changed = len(res["b_better"]) + len(res["a_better"])
k = st.columns(5)
k[0].metric("문항 수", res["n"])
k[1].metric("A 정답 점수", f"{res['mean_a']:.3f}")
k[2].metric("B 정답 점수", f"{res['mean_b']:.3f}", f"{res['diff']:+.3f}")
k[3].metric("B 우세 / A 우세 / 같음", f"{len(res['b_better'])} / {len(res['a_better'])} / {res['same']}", f"순증 {net:+d}")
k[4].metric("95% 신뢰구간", f"[{res['ci95'][0]:+.3f}, {res['ci95'][1]:+.3f}]")

significant = changed > 14 and (res["ci95"][0] > 0 or res["ci95"][1] < 0)
(st.success if significant else st.info)(
    ("차이가 있습니다: " if significant else "잡음과 구별되지 않습니다: ")
    + f"바뀐 문항 {changed}개 (잡음 기준 14개), 신뢰구간 {'0 미포함' if res['ci95'][0] > 0 or res['ci95'][1] < 0 else '0 포함'}.")

sa, sb = summary(a), summary(b)
cost = pd.DataFrame({
    "A": [sa["cost"].get("usd_per_question"), sa["calls"].get("llm_per_question"), sa["latency_s"].get("p90"),
          sa["cost"].get("tokens_per_question")],
    "B": [sb["cost"].get("usd_per_question"), sb["calls"].get("llm_per_question"), sb["latency_s"].get("p90"),
          sb["cost"].get("tokens_per_question")]},
    index=["USD/문항", "LLM 호출/문항", "p90 초", "토큰/문항"])
cost["B ÷ A"] = cost["B"] / cost["A"]
st.subheader("비용·속도")
st.dataframe(cost.style.format("{:.4g}"), width="stretch")

st.subheader("세트별 점수")
by = []
for name, s in (("A", sa), ("B", sb)):
    for k_, v in (s.get("by_set") or {}).items():
        by.append({"실험": name, "세트": SETS.get(k_, k_), "정답 점수": v.get("correctness_mean"), "문항": v.get("n")})
by = pd.DataFrame(by)
if len(by):
    st.altair_chart(alt.Chart(by).mark_bar().encode(
        x=alt.X("실험:N", title=None), y=alt.Y("정답 점수:Q", scale=alt.Scale(domain=[0, 1])), color="실험:N",
        column=alt.Column("세트:N", title=None), tooltip=["세트", "실험", "정답 점수", "문항"]))

st.subheader("점수가 갈린 문항")
items = golden()
ga = {r["qid"]: r for r in rows(a, "grades.jsonl")}
gb = {r["qid"]: r for r in rows(b, "grades.jsonl")}
diff = pd.DataFrame([{
    "qid": q, "세트": SETS.get(items.get(q, {}).get("set"), ""), "A 점수": ga[q]["correctness"], "B 점수": gb[q]["correctness"],
    "질문": items.get(q, {}).get("question", ""), "A 채점 이유": ga[q].get("reason"), "B 채점 이유": gb[q].get("reason"),
} for q in res["b_better"] + res["a_better"]])
st.dataframe(diff, width="stretch", hide_index=True)
st.caption("문항 하나를 자세히 보려면 '6. 문항별 결과' 페이지에서 qid를 고르세요.")
