import streamlit as st

from lab.common import picked_note, summary_table

st.title("📋 전체 실험 결과표")
st.caption("results/ 폴더의 모든 실험 요약(summary.json)과, agent_list에서 고른 agent의 실행(🤖)입니다. 열 제목을 누르면 정렬됩니다.")
picked_note()

t = summary_table()
c1, c2, c3 = st.columns(3)
split = c1.multiselect("split", sorted(t["split"].dropna().unique()), default=["dev"])
kind = c2.multiselect("종류", ["선택 agent", "RAG", "Agent", "검색만"], default=["선택 agent", "RAG", "Agent"])
word = c3.text_input("실험 이름·설명 검색")
view = t
if split:
    view = view[view["split"].isin(split)]
if kind:
    view = view[view["종류"].isin(kind)]
if word:
    view = view[view["실험"].str.contains(word, case=False) | view["설명"].fillna("").str.contains(word, case=False)]

num = ["정답 점수", "완전 정답률", "대응 일치율", "출처 일치율", "정답 페이지 포함", "근거 문장 포함률", "MRR"]
st.dataframe(
    view.drop(columns=["만든 시각"]).style.format({c: "{:.3f}" for c in num} | {
        "USD/문항": "{:.4f}", "LLM 호출/문항": "{:.2f}", "p50 초": "{:.1f}", "p90 초": "{:.1f}", "문맥 글자 수": "{:,.0f}"},
        na_rep="–").background_gradient(subset=["정답 점수"], cmap="Greens")
        .apply(lambda r: ["font-weight:700" if r["종류"] == "선택 agent" else "" for _ in r], axis=1),
    width="stretch", hide_index=True, height=520)
st.caption(f"{len(view)}개 실험. 정답 점수가 비어 있는 행은 답변을 만들지 않은 검색 비교 실험입니다. "
           "같은 이름에 _r2가 붙은 것은 잡음 측정을 위한 재실행, _fix는 버그 수정 뒤 재실행입니다.")

st.download_button("CSV로 받기", view.to_csv(index=False).encode("utf-8-sig"), "experiments.csv", "text/csv")
