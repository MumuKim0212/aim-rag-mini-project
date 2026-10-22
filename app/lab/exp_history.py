import altair as alt
import streamlit as st

from lab.common import picked_note, summary_table

st.title("📈 점수 변화")
st.caption("답변까지 채점한 dev 실험을 실행한 순서대로 놓았습니다. 실험마다 한 요소만 바꿨고, 채택된 변경이 다음 실험의 기준이 됩니다. "
           "agent_list에서 고른 agent의 실행(🤖)도 실행 시각 순서에 함께 놓입니다.")
picked_note()

t = summary_table()
d = t[(t["split"] == "dev") & t["정답 점수"].notna()].sort_values("만든 시각").reset_index(drop=True)
d["순서"] = d.index + 1
d["표시"] = d["이름"].fillna("")

metric = st.radio("지표", ["정답 점수", "완전 정답률", "대응 일치율", "출처 일치율"], horizontal=True)
base = alt.Chart(d).encode(x=alt.X("순서:Q", title="실행 순서"), tooltip=["실험", "설명", metric, "USD/문항", "p90 초"])
line = base.mark_line(color="#bbb").encode(y=alt.Y(f"{metric}:Q", scale=alt.Scale(zero=False)))
pts = base.mark_circle(size=110).encode(y=f"{metric}:Q", color=alt.Color("종류:N"))
txt = base.mark_text(dy=-12, fontSize=11).encode(y=f"{metric}:Q", text="표시:N")
noise = alt.Chart(d).mark_rule(strokeDash=[4, 4], color="red").encode(y=alt.datum(0.722))
st.altair_chart(line + pts + txt + noise, width="stretch")
st.caption("빨간 점선 = 처음 RAG(dev_000_baseline) 정답 점수 0.722. 같은 설정을 다시 돌리면 90문항 중 약 14문항이 바뀌므로 "
           "작은 차이는 잡음일 수 있습니다(실험 카드의 짝비교로 판정).")

st.subheader("비용과 점수")
st.altair_chart(alt.Chart(d).mark_circle(size=140).encode(
    x=alt.X("USD/문항:Q", title="문항당 비용 (USD)"), y=alt.Y("정답 점수:Q", scale=alt.Scale(zero=False)),
    color="종류:N", tooltip=["실험", "설명", "정답 점수", "USD/문항", "LLM 호출/문항", "p90 초"]), width="stretch")

st.dataframe(d[["순서", "실험", "표시", "종류", "정답 점수", "완전 정답률", "대응 일치율", "USD/문항", "p90 초", "설명"]],
             width="stretch", hide_index=True)
