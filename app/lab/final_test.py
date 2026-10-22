import re

import altair as alt
import pandas as pd
import streamlit as st

from lab.common import ROOT, SETS, SYSTEMS, final_frame, final_stats

st.title("🏁 최종 test 결과")
st.caption("네 시스템을 test 전에 고정하고(PROCESS.md 9절) test 131문항(제공 90 + 자작 v2 41)에서 한 번씩 실행한 결과입니다. "
           "test 세트는 다시 돌리지 않습니다.")

st.markdown("""
| | 시스템 | 설정 |
|---|---|---|
| **T1** | 처음 RAG | Recursive 800/100, 벡터 검색 k=5, `gemini-3.5-flash-lite`, 답변 프롬프트 v1 |
| **T2** | 개선된 RAG (큰 모델) | 구조 단위 + 950/119, Hybrid + LLM 재정렬 15→5, `gemini-3.6-flash`, 프롬프트 v4 |
| **T3** | Agent (큰 모델) | T2와 같은 검색·모델·프롬프트 위의 LangGraph 에이전트 |
| **T4** | **최종** (작은 모델) | T2와 같은 검색, `gemini-3.5-flash-lite` + 프롬프트 v4 (가격 때문에 선택) |
""")

stats = pd.DataFrame({f"{k} {SYSTEMS[k][0]}": final_stats(k) for k in SYSTEMS}).T
st.dataframe(stats.style.format({c: "{:.3f}" for c in stats.columns if c not in ("n", "평균 초", "p90 초", "LLM 호출/문항", "USD/문항")}
                                | {"n": "{:.0f}", "평균 초": "{:.1f}", "p90 초": "{:.1f}", "LLM 호출/문항": "{:.2f}",
                                   "USD/문항": "{:.4f}"}), width="stretch")

st.subheader("효과 나눠 보기 (짝비교)")
from evalkit.paired import compare  # noqa: E402

frames = {k: final_frame(k).set_index("qid")["correctness"].to_dict() for k in SYSTEMS}
effects = []
for name, a, b in (("설정 튜닝", "T1", "T2"), ("구조 (Agent)", "T2", "T3"), ("모델 크기", "T2", "T4"), ("최종 vs 처음", "T1", "T4")):
    r = compare(frames[a], frames[b], max_score=2.0)
    effects.append({"효과": name, "비교": f"{b} − {a}", "점수 차이": r["diff"],
                    "95% CI": f"[{r['ci95'][0]:+.3f}, {r['ci95'][1]:+.3f}]",
                    "우세 / 열세 / 같음": f"{len(r['b_better'])} / {len(r['a_better'])} / {r['same']}",
                    "판정": "차이 있음" if r["ci95"][0] > 0 or r["ci95"][1] < 0 else "구별 안 됨"})
st.dataframe(pd.DataFrame(effects).style.format({"점수 차이": "{:+.3f}"}), width="stretch", hide_index=True)

st.subheader("세트별 정답 점수")
by = pd.concat([final_frame(k).assign(시스템=f"{k} {SYSTEMS[k][0]}") for k in SYSTEMS])
by["세트"] = by["set"].map(lambda s: SETS.get(s, s))
agg = by.groupby(["시스템", "세트"]).agg(점수=("correctness", lambda s: s.mean() / 2), 문항=("qid", "count")).reset_index()
st.altair_chart(alt.Chart(agg).mark_bar().encode(
    x=alt.X("시스템:N", title=None, axis=alt.Axis(labelAngle=-30)), y=alt.Y("점수:Q", scale=alt.Scale(domain=[0, 1])),
    color="시스템:N", column=alt.Column("세트:N", title=None), tooltip=["시스템", "세트", "점수", "문항"]))

st.subheader("대응별 결과")
st.caption("답변 가능 문항은 답해야 하고, 답변 불가 문항은 보류·되묻기·거절을 골라야 합니다.")
grp = by.groupby(["시스템", "behavior_group"]).agg(대응_일치율=("status_ok", "mean"), 정답_점수=("correctness", lambda s: s.mean() / 2),
                                                 문항=("qid", "count")).reset_index().rename(columns={"behavior_group": "기대 대응"})
st.dataframe(grp.style.format({"대응_일치율": "{:.3f}", "정답_점수": "{:.3f}"}), width="stretch", hide_index=True)

with st.expander("EVALUATION.md 결론 부분 읽기"):
    text = (ROOT / "submission" / "EVALUATION.md").read_text(encoding="utf-8")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    st.markdown(text)
