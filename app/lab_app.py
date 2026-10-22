"""Lab report app: the whole RAG practice by topic, each topic with its own sub-pages.

    streamlit run app/lab_app.py

Reads committed files (results/, golden/, corpus/, configs/, experiments/) plus the runs made on
"개요 › agent_list" (out/agent_runs/, scripts/branch_agents.py): every app start looks up the newest agent on
each origin branch; the agents picked there appear in every page below, and "langgraph" draws their graphs from
their own branch code. Runs and "질문 직접 실행" call the API (needs .env and the indexes in out/index).
"""

import streamlit as st

st.set_page_config(page_title="금융 문서 RAG 실습 결과", page_icon="📊", layout="wide")

P = "lab/"
nav = st.navigation({
    "개요": [
        st.Page(P + "home.py", title="실습 한눈에 보기", icon="🏠", default=True),
        st.Page(P + "agent_list.py", title="agent_list", icon="🤖"),
        st.Page(P + "langgraph.py", title="langgraph", icon="🧭"),
    ],
    "1. 데이터": [
        st.Page(P + "data_docs.py", title="문서와 페이지 추출", icon="📄"),
        st.Page(P + "data_golden.py", title="골든셋", icon="🎯"),
    ],
    "2. 청킹": [
        st.Page(P + "chunk_stats.py", title="청킹 방식별 청크", icon="✂️"),
        st.Page(P + "chunk_retrieval.py", title="청킹·검색 비교 (LLM 없이)", icon="🔍"),
        st.Page(P + "chunk_llm.py", title="청킹·검색 비교 (LLM 사용 후)", icon="🧪"),
    ],
    "3. 실험": [
        st.Page(P + "exp_table.py", title="전체 실험 결과표", icon="📋"),
        st.Page(P + "exp_history.py", title="점수 변화", icon="📈"),
        st.Page(P + "exp_compare.py", title="두 실험 짝비교", icon="⚖️"),
        st.Page(P + "exp_cards.py", title="실험 카드", icon="🗂️"),
    ],
    "4. 에이전트": [
        st.Page(P + "agent_graph.py", title="에이전트 흐름도", icon="🧭"),
        st.Page(P + "agent_compare.py", title="에이전트 비교", icon="🤖"),
        st.Page(P + "agent_live.py", title="질문 직접 실행", icon="▶️"),
    ],
    "5. 최종 평가": [
        st.Page(P + "final_test.py", title="최종 test 결과", icon="🏁"),
    ],
    "6. 문항별 결과": [
        st.Page(P + "question_view.py", title="문항 하나씩 보기", icon="🔎"),
    ],
})

import importlib  # noqa: E402
from pathlib import Path  # noqa: E402

import lab.common  # noqa: E402

# Streamlit reruns page files but keeps imported modules: reload the shared module when its file changed,
# so an edit (or a git pull) never leaves pages calling an old version.
_mtime = Path(lab.common.__file__).stat().st_mtime
if getattr(lab.common, "_loaded_mtime", None) != _mtime:
    importlib.reload(lab.common)
    lab.common._loaded_mtime = _mtime

from lab.common import branch_agents, picked, picked_runs  # noqa: E402

branch_agents()  # every app start / new browser session looks the agents up again on GitHub
with st.sidebar:
    st.markdown("**🤖 선택한 agent**")
    runs = {r["label"]: r for r in picked_runs()}
    sel = picked()
    if not sel:
        st.caption("없음 · '개요 › agent_list'에서 고르세요")
    for n, a in enumerate(sel, 1):
        r = runs.get(a["label"])
        st.caption(f"{n}. {a['label']} — " + (f"{r['correctness']:.3f} ({r['n']}문항)" if r else "결과 없음"))
nav.run()
