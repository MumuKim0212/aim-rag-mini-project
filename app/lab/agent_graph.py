import streamlit as st

from lab.common import agent_of, picked, picked_note, show_mermaid

import agent as A  # noqa: E402  (repo root agent.py: Korean names for nodes and branches)

st.title("🧭 에이전트 흐름도")
st.caption("LangGraph가 컴파일한 그래프(`graph.get_graph()`)에서 바로 그린 그림입니다. 노드와 분기 이름만 한글로 바꿨으므로 "
           "코드가 바뀌면 그림도 같이 바뀝니다. API는 쓰지 않습니다.")
picked_note()
if picked():
    st.page_link("lab/langgraph.py", label="🤖 선택한 agent들의 흐름도는 '1. 데이터 › langgraph'에서 나란히 봅니다", icon="🧭")
st.caption("아래는 이 저장소(현재 브랜치)에 있는 에이전트 세 가지입니다.")

AGENTS = {
    "T3 에이전트 (세린님, 최종 test에 사용)": ("configs/008b-agent-950.yaml",
        "질문을 분류하고 검색한 뒤, 근거가 부족하면 검색어를 다시 써서 최대 2번 더 찾습니다. 답을 쓴 뒤 인용 번호를 코드로 확인합니다."),
    "에이전트 v2 (메모 + 답변 검토, 카드 014)": ("configs/014-agent-v2.yaml",
        "T3에 더해, 분류 결과와 '근거 부족' 메모를 답변 단계에 넘기고, 다른 모델(3.8-flash)이 답변을 검토해 문제가 있으면 한 번 고칩니다."),
    "복구 에이전트 (청크 잘림 진단, 카드 015)": ("configs/015-context-repair.yaml",
        "근거 판단 대신 '근거 진단'을 합니다. 부족한 원인이 청크 잘림이면 페이지 전체로 넓혀 다시 진단하고, 다른 근거가 필요하면 다시 검색하고, 글자가 깨졌으면 그 페이지를 기록합니다."),
}

name = st.radio("에이전트", list(AGENTS), horizontal=False)
config, about = AGENTS[name]
st.info(about)
ag, cfg = agent_of(config)
show_mermaid(A.korean_mermaid(ag))

with st.expander("노드 설명"):
    st.markdown("""
| 노드 | 하는 일 | LLM |
|---|---|---|
| 질문 유형 분류 | 문서로 답할 질문 / 질문자 정보가 더 필요 / 부적절한 요청 / 지시문 주입 포함 | 1회 |
| 문서 검색 | Hybrid 검색으로 후보 15개 → LLM 재정렬로 5개 | 1회 |
| 근거 충분한지 판단 · 근거 진단 | 검색 결과로 답할 수 있는지(진단은 부족한 원인까지) | 1회 |
| 검색어 다시 쓰기 | 빠진 정보를 찾는 새 검색어 (최대 2회) | 1회 |
| 잘린 청크를 페이지 전체로 확장 | 잘린 청크를 그 페이지 전체 글로 바꾸고 다시 진단 (질문당 1회) | 0 |
| 깨진 페이지 기록 | 나중에 다시 추출할 페이지로 기록 | 0 |
| 답변 작성 | 최종 체인과 같은 답변 프롬프트로 답변·보류·되묻기·거절 중 하나 | 1회 |
| 인용 번호 확인 | 인용 번호가 검색 결과 안에 있는지 코드로 확인, 틀리면 1회 다시 작성 | 0 |
| 답변 검토 (v2) | 빠진 내용·주의 문구·근거에 없는 숫자를 찾고, 있으면 1회 수정 | 1회 |
""")

with st.expander("설정 (주요 값)"):
    st.json({"chunking": cfg["chunking"], "retrieval": cfg["retrieval"], "answer": cfg["answer"], "agent": cfg["agent"]})
with st.expander("mermaid 원문"):
    st.code(A.korean_mermaid(ag), language="text")
