import pandas as pd
import streamlit as st

from lab.common import SETS, STATUS, golden, graded, label, rows

st.title("🔎 문항 하나씩 보기")
st.caption("실험 하나를 고르고 문항별로 질문·기준 답·시스템 답·채점 이유·검색된 청크·에이전트 판단을 봅니다.")

split = st.radio("split", ["dev", "test"], horizontal=True)
names = graded(split)
default = "dev_008b_agent950" if split == "dev" else "test_013b_rerank_lite"
exp = st.selectbox("실험", names, index=names.index(default) if default in names else 0, format_func=label)

items = golden()
runs = {r["qid"]: r for r in rows(exp, "runs.jsonl")}
metrics = {m["qid"]: m for m in rows(exp, "metrics.jsonl")}
grades = {g["qid"]: g for g in rows(exp, "grades.jsonl")}
table = pd.DataFrame([{
    "qid": q, "세트": SETS.get(m.get("set"), m.get("set")), "점수": grades.get(q, {}).get("correctness"),
    "상태": STATUS.get(m.get("status"), m.get("status")), "대응 맞음": bool(m.get("status_ok")),
    "정답 페이지 포함": m.get("page_hit"), "근거 포함률": m.get("evid"), "검색 수": m.get("n_searches"),
    "LLM 호출": m.get("n_llm_calls"), "초": m.get("latency_s"), "질문": items.get(q, {}).get("question", ""),
} for q, m in metrics.items()])

f1, f2, f3 = st.columns(3)
score = f1.multiselect("점수", [0, 1, 2], default=[])
sets = f2.multiselect("세트", sorted(table["세트"].dropna().unique()))
wrong = f3.checkbox("대응이 틀린 문항만")
view = table
if score:
    view = view[view["점수"].isin(score)]
if sets:
    view = view[view["세트"].isin(sets)]
if wrong:
    view = view[~view["대응 맞음"]]
st.dataframe(view, width="stretch", hide_index=True, height=260)
st.caption(f"{len(view)}문항 · 0점 {int((table['점수'] == 0).sum())}, 1점 {int((table['점수'] == 1).sum())}, "
           f"2점 {int((table['점수'] == 2).sum())}")

if not len(view):
    st.stop()
qid = st.selectbox("자세히 볼 문항", view["qid"].tolist())
it, run, m, g = items.get(qid, {}), runs.get(qid, {}), metrics.get(qid, {}), grades.get(qid, {})

st.markdown(f"### {qid} · {SETS.get(it.get('set'), it.get('set'))}")
st.markdown(f"**질문** {it.get('question') or run.get('question')}")
k = st.columns(5)
k[0].metric("점수 (0~2)", g.get("correctness", "–"))
k[1].metric("상태", STATUS.get(run.get("status"), run.get("status")), "대응 맞음" if m.get("status_ok") else "대응 틀림",
            delta_color="normal" if m.get("status_ok") else "inverse")
k[2].metric("근거 포함률", f"{m.get('evid', 0):.2f}" if m.get("evid") is not None else "–")
k[3].metric("LLM 호출 / 검색", f"{m.get('n_llm_calls')} / {m.get('n_searches')}")
k[4].metric("시간", f"{m.get('latency_s', 0):.1f}초")

left, right = st.columns(2)
with left:
    st.markdown("#### 시스템 답")
    st.markdown(run.get("answer") or "(runs.jsonl 없음)")
    st.markdown("#### 채점 이유")
    st.info(g.get("reason") or "–")
with right:
    st.markdown("#### 기준 답")
    st.markdown(it.get("target_answer") or "(없음)")
    st.markdown(f"**기대 대응** `{it.get('expected_behavior')}`")
    st.markdown("**반드시 포함** " + (", ".join(it.get("must_include") or []) or "–"))
    st.markdown("**정답 페이지** " + (", ".join(f"{t['file']} p.{t['page']}" for t in it.get("targets") or []) or "없음"))
    with st.expander("근거 문장"):
        for e in it.get("evidence") or []:
            st.markdown(f"> {e}")

targets = {(t["file"], t["page"]) for t in it.get("targets") or []}
cited = {c["chunk_id"] for c in run.get("citations") or []}
ctx = run.get("context") or []
st.markdown(f"#### 답변 단계에 넘어간 청크 ({len(ctx)}개)")
st.caption("🎯 = 정답 페이지의 청크, 📌 = 답변이 인용한 청크")
for n, u in enumerate(ctx, 1):
    hit = any((u["source"], p) in targets for p in u.get("pages") or [u["page"]])
    mark = ("🎯" if hit else "") + ("📌" if u["chunk_id"] in cited else "")
    with st.expander(f"{mark} [{n}] {u['source']} p.{u['page']} · {len(u['content'])}자"):
        st.text(u["content"])

steps = run.get("steps") or {}
if steps.get("decisions"):
    st.markdown("#### 에이전트 판단 기록")
    st.dataframe(pd.DataFrame(steps["decisions"]).astype(str), width="stretch", hide_index=True)
if run.get("searches"):
    with st.expander("검색 기록"):
        st.dataframe(pd.DataFrame([{"검색어": s["query"], "청크": ", ".join(s["chunk_ids"]), "초": s.get("seconds")}
                                   for s in run["searches"]]), width="stretch", hide_index=True)
if steps.get("calls"):
    with st.expander("LLM·임베딩 호출"):
        st.dataframe(pd.DataFrame(steps["calls"]), width="stretch", hide_index=True)
