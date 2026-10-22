import os

import streamlit as st

from lab.common import ROOT, agent_of, golden, show_mermaid

import agent as A  # noqa: E402

st.title("▶️ 질문 직접 실행")
st.caption("에이전트에 질문 하나를 넣고, 지나간 노드와 판단을 한글로 봅니다. **API를 사용합니다** "
           "(질문 1개에 LLM 4~6회, 약 0.01~0.02 USD). dev 문항이나 직접 쓴 질문만 실행합니다.")

from rag.env import setup  # noqa: E402

setup()
if not os.environ.get("GOOGLE_API_KEY"):
    st.error("GOOGLE_API_KEY가 없습니다. 프로젝트 폴더의 .env에 키를 넣어야 실행할 수 있습니다.")
    st.stop()

MODES = {"복구 에이전트 (카드 015)": "configs/015-context-repair.yaml", "T3 에이전트": "configs/008b-agent-950.yaml"}
c1, c2 = st.columns([1, 2])
mode = c1.radio("에이전트", list(MODES))
how = c2.radio("질문", ["dev 골드셋 문항", "직접 쓰기"], horizontal=True)
ag, cfg = agent_of(MODES[mode])

from rag.golden import scope_of  # noqa: E402

item = None
if how == "dev 골드셋 문항":
    dev = [i for i in golden().values() if i.get("split") == "dev"]
    item = st.selectbox("문항", dev, format_func=lambda i: f"{i['qid']} · {i['question'][:60]}",
                        index=next((n for n, i in enumerate(dev) if i["qid"] == A.EXAMPLE_QID), 0))
    question, scope = item["question"], scope_of(item, cfg)
else:
    question = st.text_area("질문", "주택연금은 몇 살부터 가입할 수 있나요?")
    scope = st.radio("검색 범위", ["B", "A"], horizontal=True,
                     format_func=lambda s: {"A": "A (용어집 + 약관)", "B": "B (전체 23개 PDF)"}[s])

if not (ROOT / "out" / "index").exists():
    st.warning("out/index 에 인덱스가 없습니다. 먼저 `python scripts/build_index.py --config configs/015-context-repair.yaml`")

if st.button("실행", type="primary", disabled=not question.strip()):
    with st.spinner("에이전트 실행 중… (10~30초)"):
        result = A.run_question(ag, cfg, question, scope)
    st.session_state["live"] = (result, item, mode)

if "live" in st.session_state:
    result, item_, mode_ = st.session_state["live"]
    st.subheader(f"결과: {A.STATUS.get(result['status'], result['status'])}")
    k = st.columns(4)
    k[0].metric("LLM 호출", result["n_llm_calls"])
    k[1].metric("검색", result["n_searches"])
    k[2].metric("시간", f"{result['seconds']}초")
    k[3].metric("비용", f"{result['usd']:.4f} USD")
    left, right = st.columns([3, 2])
    with left:
        st.markdown("**답변**")
        st.markdown(result["answer"])
        st.markdown("**진행 과정**")
        st.text("\n".join(A.describe(result)))
        if item_:
            st.markdown("**기준 답**")
            st.markdown(item_.get("target_answer") or "–")
            shown = {(u["source"], p) for u in result["context"] for p in u.get("pages", [u["page"]])}
            cited = {(c["source"], c["page"]) for c in result["citations"]}
            for t in item_.get("targets") or []:
                key = (t["file"], t["page"])
                st.markdown(f"- 정답 페이지 {t['file']} p.{t['page']}: 문맥에 **{'있음' if key in shown else '없음'}**, "
                            f"인용 **{'함' if key in cited else '안 함'}**")
    with right:
        st.markdown("**지나간 노드 (노란색)**")
        show_mermaid(A.korean_mermaid(agent_of(MODES[mode_])[0], path=A.visited_path(result["steps"])))
    with st.expander(f"답변 단계에 넘어간 문맥 ({len(result['context'])}개)"):
        for n, u in enumerate(result["context"], 1):
            st.markdown(f"**[{n}] {u['source']} p.{u['page']}** · `{u['chunk_id']}`")
            st.text(u["content"][:1500] + ("…" if len(u["content"]) > 1500 else ""))
