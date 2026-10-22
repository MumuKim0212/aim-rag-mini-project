import altair as alt
import pandas as pd
import streamlit as st

from lab.common import paired, summary_table

st.title("🔍 청킹·검색 비교 (LLM 없이)")
st.caption("답변을 만들지 않고 검색 결과만 채점한 실험들입니다(`--retrieval-only`). 정답 페이지와 근거 문장이 "
           "검색 결과 상위 5개에 들어왔는지로 청킹·검색 방식을 비교합니다. 비용은 질문 임베딩뿐입니다.")

with st.expander("지표 설명"):
    st.markdown("""
| 지표 | 뜻 |
|---|---|
| 정답 페이지 포함 (page_hit@5) | 상위 5개 청크 중 정답 페이지의 청크가 하나라도 있는 문항 비율 |
| 근거 문장 포함률 (evid@5) | 골든셋 근거 문장이 상위 5개 청크에 글자 그대로 들어 있는 비율 (문항 평균) |
| MRR | 처음 나온 정답 청크 순위의 역수 평균 (1위면 1, 2위면 0.5) |
| 문맥 글자 수 | 답변 단계에 넘어갈 글자 수 (길수록 비용·지연 증가) |
""")

t = summary_table()
r = t[(t["split"] == "dev") & (t["종류"] == "검색만")].copy()
r = r[["실험", "설명", "정답 페이지 포함", "근거 문장 포함률", "MRR", "문맥 글자 수", "카드"]].sort_values("근거 문장 포함률", ascending=False)
st.dataframe(r.style.format({"정답 페이지 포함": "{:.3f}", "근거 문장 포함률": "{:.3f}", "MRR": "{:.3f}",
                             "문맥 글자 수": "{:,.0f}"}), width="stretch", hide_index=True)

st.altair_chart(alt.Chart(r).mark_circle(size=120).encode(
    x=alt.X("문맥 글자 수:Q", scale=alt.Scale(zero=False)), y=alt.Y("근거 문장 포함률:Q", scale=alt.Scale(zero=False)),
    color=alt.Color("정답 페이지 포함:Q", scale=alt.Scale(scheme="viridis")),
    tooltip=["실험", "설명", "정답 페이지 포함", "근거 문장 포함률", "MRR", "문맥 글자 수"]), width="stretch")
st.caption("오른쪽 위로 갈수록 근거는 많이 담지만 문맥이 길어집니다. 왼쪽 위가 효율이 좋은 방식입니다.")

st.subheader("두 방식 짝비교")
names = r["실험"].tolist()
c1, c2, c3 = st.columns(3)
a = c1.selectbox("기준 (A)", names, index=names.index("dev_001e_chunk950chain_retrieval") if "dev_001e_chunk950chain_retrieval" in names else 0)
b = c2.selectbox("비교 (B)", names, index=names.index("dev_014_mixedchunk_retrieval") if "dev_014_mixedchunk_retrieval" in names else 1)
metric = c3.selectbox("지표", ["evid@5", "page_hit@5", "mrr", "gold@5"])
if a != b:
    res = paired(a, b, metric)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("A 평균", f"{res['mean_a']:.3f}")
    k2.metric("B 평균", f"{res['mean_b']:.3f}", f"{res['diff']:+.3f}")
    k3.metric("B 우세 / A 우세", f"{len(res['b_better'])} / {len(res['a_better'])}", f"순증 {len(res['b_better']) - len(res['a_better']):+d}")
    k4.metric("95% 신뢰구간", f"[{res['ci95'][0]:+.3f}, {res['ci95'][1]:+.3f}]")
    st.caption("판정 기준(팀 규칙): 바뀐 문항이 잡음(90문항 중 14개)보다 많고 신뢰구간이 0을 포함하지 않아야 차이가 있다고 봅니다.")
    with st.expander("문항 목록"):
        st.markdown("**B가 나은 문항** " + (" ".join(res["b_better"]) or "–"))
        st.markdown("**A가 나은 문항** " + (" ".join(res["a_better"]) or "–"))
