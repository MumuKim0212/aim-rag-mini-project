import altair as alt
import pandas as pd
import streamlit as st

from lab.common import SETS, golden, kpi_row

st.title("🎯 골든셋")
st.caption("모든 판단의 잣대가 되는 질문·기준 답·근거 세트입니다. 검색 색인에는 절대 넣지 않습니다.")

items = golden()
df = pd.DataFrame([{
    "qid": i["qid"], "세트": SETS.get(i.get("set"), i.get("set")), "split": i.get("split"),
    "답변 가능": i.get("answerable"), "기대 대응": i.get("expected_behavior"), "난이도": i.get("difficulty"),
    "근거 형태": i.get("context_type"), "정답 페이지 수": len(i.get("targets") or []),
    "근거 문장 수": len(i.get("evidence") or []), "질문": i.get("question"),
} for i in items.values()])

kpi_row([
    ("전체 문항", f"{len(df)}", "제공 180 + 자작 20(보관) + 자작 v2 41"),
    ("dev", f"{(df['split'] == 'dev').sum()}", "튜닝과 모든 결정에 사용"),
    ("test", f"{(df['split'] == 'test').sum()}", "최종 확인에 한 번만 사용"),
    ("답변 불가 문항", f"{(~df['답변 가능'].astype(bool)).sum()}", "올바른 보류·거절을 재는 문항"),
])

st.subheader("세트 × 분할")
pivot = df.pivot_table(index="세트", columns="split", values="qid", aggfunc="count", fill_value=0)
st.dataframe(pivot, width="stretch")

c1, c2 = st.columns(2)
for col, field in ((c1, "기대 대응"), (c2, "근거 형태")):
    counts = df[field].fillna("(없음)").value_counts().reset_index()
    counts.columns = [field, "문항 수"]
    col.altair_chart(alt.Chart(counts).mark_bar().encode(
        x="문항 수:Q", y=alt.Y(f"{field}:N", sort="-x", title=field), tooltip=[field, "문항 수"]),
        width="stretch")

st.subheader("문항 찾아보기")
f1, f2, f3 = st.columns(3)
sets = f1.multiselect("세트", sorted(df["세트"].dropna().unique()))
split = f2.multiselect("split", sorted(df["split"].dropna().unique()))
word = f3.text_input("질문에 들어간 단어")
view = df
if sets:
    view = view[view["세트"].isin(sets)]
if split:
    view = view[view["split"].isin(split)]
if word:
    view = view[view["질문"].str.contains(word, na=False)]
st.dataframe(view, width="stretch", hide_index=True, height=300)

qid = st.selectbox("자세히 볼 문항", view["qid"].tolist()) if len(view) else None
if qid:
    it = items[qid]
    st.markdown(f"**질문** {it['question']}")
    st.markdown(f"**기준 답** {it.get('target_answer') or '(없음)'}")
    c1, c2 = st.columns(2)
    c1.markdown("**반드시 포함** " + (", ".join(it.get("must_include") or []) or "–"))
    c2.markdown("**포함하면 안 됨** " + (", ".join(it.get("must_not_include") or []) or "–"))
    st.markdown("**정답 페이지** " + (", ".join(f"{t['file']} p.{t['page']}" for t in it.get("targets") or []) or "없음 (답변 불가)"))
    for e in it.get("evidence") or []:
        st.markdown(f"> {e}")
    if it.get("note"):
        st.caption("메모: " + it["note"])
