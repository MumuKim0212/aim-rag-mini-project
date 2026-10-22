import streamlit as st

from lab.common import A, BA, picked, show_mermaid

st.title("🧭 langgraph")
st.caption("agent_list에서 고른 agent마다, 그 브랜치의 코드로 LangGraph 그래프를 만들어 순서도로 그립니다. "
           "노드와 분기 이름만 한글로 바꿨고, API는 쓰지 않습니다.")


@st.cache_data(show_spinner="그 브랜치 코드에서 LangGraph 그래프를 꺼내는 중… (처음 한 번 10~30초)")
def graph_text(sha: str, config: str) -> str:
    return BA.graph_of(sha, config)


sel = picked()
if not sel:
    st.info("👈 '1. 데이터 › agent_list'에서 agent를 고르면 여기에 흐름도가 나옵니다.")
    st.stop()

with st.expander("노드 이름 읽는 법", expanded=False):
    st.markdown("""
| 노드 | 하는 일 |
|---|---|
| 질문 유형 분류 | 문서로 답할 질문인지, 질문자 정보가 더 필요한지, 부적절한 요청인지, 지시문이 섞였는지 |
| 문서 검색 | 검색 (최종 체인은 Hybrid 후보 15개 → LLM 재정렬 5개) |
| 근거 충분한지 판단 · 근거 진단 | 검색 결과로 답할 수 있는지 (진단은 부족한 원인: 청크 잘림 / 다른 근거 필요 / 글자 깨짐) |
| 검색어 다시 쓰기 | 빠진 정보를 찾을 새 검색어로 다시 검색 |
| 잘린 청크를 페이지 전체로 확장 | 잘린 청크를 그 페이지 전체로 바꾸고 다시 진단 |
| 깨진 페이지 기록 | 나중에 다시 추출할 페이지로 기록 |
| 답변 작성 · 인용 번호 확인 | 답을 쓰고, 인용 번호가 검색 결과 안에 있는지 코드로 확인 |
| 답변 검토 | (v2) 다른 모델이 답을 검토하고 문제가 있으면 1회 수정 |
""")

cols = st.columns(min(len(sel), 3))
for n, a in enumerate(sel, 1):
    with cols[(n - 1) % len(cols)]:
        st.subheader(f"{n}. {a['label']}")
        st.caption(f"설정 {a['config']} · 커밋 {a['commit']} · 답변 모델 {a['answer_model']}")
        try:
            text = A.translate(graph_text(a["sha"], a["config"]))
        except Exception as e:
            st.warning(f"그래프를 꺼내지 못했습니다: {str(e)[-300:]}")
            continue
        show_mermaid(text)
        nodes = [line.split("(")[0].strip() for line in text.splitlines()
                 if "(" in line and "-->" not in line and "-.->" not in line and not line.strip().startswith(("class", "graph"))]
        st.caption("노드: " + " → ".join(A.NODES.get(x, x).split("<br>")[0] for x in nodes if x not in ("__start__", "__end__")))
        st.caption(a["description"])
