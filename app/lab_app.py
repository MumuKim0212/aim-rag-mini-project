"""Lab report app: the whole RAG practice by topic, each topic with its own sub-pages.

    streamlit run app/lab_app.py

Reads committed files only (results/, golden/, corpus/, configs/, experiments/). The agent pages build the
agents from configs (no API); "질문 직접 실행" calls the API and needs the index in out/index and GOOGLE_API_KEY.
Serin's app (app/streamlit_app.py) is separate and unchanged.
"""

import streamlit as st

st.set_page_config(page_title="금융 문서 RAG 실습 결과", page_icon="📊", layout="wide")

P = "lab/"
nav = st.navigation({
    "개요": [
        st.Page(P + "home.py", title="실습 한눈에 보기", icon="🏠", default=True),
    ],
    "1. 데이터": [
        st.Page(P + "data_docs.py", title="문서와 페이지 추출", icon="📄"),
        st.Page(P + "data_golden.py", title="골든셋", icon="🎯"),
    ],
    "2. 청킹": [
        st.Page(P + "chunk_stats.py", title="청킹 방식별 청크", icon="✂️"),
        st.Page(P + "chunk_retrieval.py", title="청킹·검색 비교 (LLM 없이)", icon="🔍"),
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
nav.run()
