import pandas as pd
import streamlit as st

from lab.common import PALETTE, all_runs, picked, picked_compare, picked_note, summary, summary_table

st.title("📋 전체 실험 결과표")
st.caption("위: agent_list에서 고른 agent별 실행 결과. 아래: results/ 폴더의 팀 실험 전체(summary.json). 열 제목을 누르면 정렬됩니다.")
picked_note()

FMT = {"정답 점수": "{:.3f}", "완전 정답률": "{:.3f}", "대응 일치율": "{:.3f}", "출처 일치율": "{:.3f}", "근거 문장 포함률": "{:.3f}",
       "정답 페이지 포함": "{:.3f}", "USD/문항": "{:.4f}", "LLM 호출/문항": "{:.2f}", "검색/문항": "{:.2f}", "p50 초": "{:.1f}",
       "p90 초": "{:.1f}", "걸린 분": "{:.1f}"}

# ---------------------------------------------------------------- one block per picked agent
sel = picked()
if sel:
    st.subheader("🤖 agent별 실험 결과")
    for n, a in enumerate(sel, 1):
        color = PALETTE[(n - 1) % len(PALETTE)]
        st.markdown(f'<div style="border-left:6px solid {color};padding-left:10px;margin-top:8px">'
                    f'<b>{n}. {a["label"]}</b> · 만든 사람 {a.get("maker", "-")} · 설정 {a["config"]} · 커밋 {a["commit"]}<br>'
                    f'<span style="font-size:0.85em">{a["description"]}</span></div>', unsafe_allow_html=True)
        runs = all_runs(a)
        if not runs:
            st.caption("아직 실행 결과가 없습니다. agent_list에서 실행하세요.")
            continue
        table = []
        for i, r in enumerate(runs, 1):
            s = summary(r["experiment"])
            sc, rt = s.get("scores", {}), s.get("retrieval", {})
            table.append({"회차": i, "실행 시각": r["started"][5:16], "문항 수": r["n"], "정답 점수": sc.get("correctness_mean"),
                          "완전 정답률": sc.get("fully_correct"), "대응 일치율": sc.get("status_ok"),
                          "출처 일치율": sc.get("citation_on_target"), "근거 문장 포함률": rt.get("evid"),
                          "정답 페이지 포함": rt.get("page_hit"), "USD/문항": r["usd_per_question"],
                          "LLM 호출/문항": r["llm_per_question"], "검색/문항": r.get("searches_per_question"),
                          "p50 초": r["p50"], "p90 초": r["p90"], "걸린 분": r.get("minutes"), "실험": r["experiment"]})
        st.dataframe(pd.DataFrame(table).style.format(FMT, na_rep="–"), width="stretch", hide_index=True)
    st.markdown("&nbsp;")
    picked_compare("선택한 agent 나란히 비교 (각 agent의 최근 실행, 함께 푼 문항 기준)")
    st.divider()

# ---------------------------------------------------------------- team experiments
st.subheader("팀 실험 전체 (만든 사람별)")
st.caption("만든 사람 = 그 실험 결과(results/<실험>)를 처음 커밋한 사람입니다.")
t = summary_table()
t = t[t["종류"] != "선택 agent"]
c1, c2, c3 = st.columns(3)
split = c1.multiselect("split", sorted(t["split"].dropna().unique()), default=["dev"])
kind = c2.multiselect("종류", ["RAG", "Agent", "검색만"], default=["RAG", "Agent"])
word = c3.text_input("실험 이름·설명 검색")
view = t
if split:
    view = view[view["split"].isin(split)]
if kind:
    view = view[view["종류"].isin(kind)]
if word:
    view = view[view["실험"].str.contains(word, case=False) | view["설명"].fillna("").str.contains(word, case=False)]

num = ["정답 점수", "완전 정답률", "대응 일치율", "출처 일치율", "정답 페이지 포함", "근거 문장 포함률", "MRR"]
for who, part in view.groupby("만든 사람", sort=False):
    st.markdown(f"**{who}** · {len(part)}개 실험")
    st.dataframe(
        part.drop(columns=["만든 시각", "만든 사람"]).style.format({c: "{:.3f}" for c in num} | {
            "USD/문항": "{:.4f}", "LLM 호출/문항": "{:.2f}", "p50 초": "{:.1f}", "p90 초": "{:.1f}", "문맥 글자 수": "{:,.0f}"},
            na_rep="–").background_gradient(subset=["정답 점수"], cmap="Greens"),
        width="stretch", hide_index=True, height=min(520, 38 + 35 * len(part)))
st.caption(f"{len(view)}개 실험. 정답 점수가 비어 있는 행은 답변을 만들지 않은 검색 비교 실험입니다. "
           "같은 이름에 _r2가 붙은 것은 잡음 측정을 위한 재실행, _fix는 버그 수정 뒤 재실행입니다.")

st.download_button("CSV로 받기", view.to_csv(index=False).encode("utf-8-sig"), "experiments.csv", "text/csv")
