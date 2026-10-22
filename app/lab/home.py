import pandas as pd
import streamlit as st

from lab.common import SYSTEMS, final_stats, kpi_row, picked_compare, picked_note, summary_table

st.title("🏠 금융 문서 RAG 실습 한눈에 보기")
st.caption("금융 PDF 23개를 검색해 근거(파일·페이지)와 함께 답하는 RAG와 Agent를 만들고, 직접 만든 평가 루프로 개선한 실습의 결과입니다.")
picked_note()
picked_compare("선택한 agent 한눈에 비교 (dev)")

stats = {k: final_stats(k) for k in SYSTEMS}
st.subheader("최종 결과 (test 131문항: 제공 90 + 자작 41)")
kpi_row([
    ("처음 RAG (T1)", f"{stats['T1']['정답 점수']:.3f}", "처음 만든 기본 RAG"),
    ("개선된 RAG (T2)", f"{stats['T2']['정답 점수']:.3f}", "실험으로 고른 설정 + 큰 모델"),
    ("Agent (T3)", f"{stats['T3']['정답 점수']:.3f}", "T2와 같은 검색·모델 위의 LangGraph 에이전트"),
    ("최종 시스템 (T4)", f"{stats['T4']['정답 점수']:.3f}", "작은 모델: 가격 때문에 최종 선택"),
])

table = pd.DataFrame({f"{k} {SYSTEMS[k][0]}": v for k, v in stats.items()}).T
st.dataframe(table.style.format({c: "{:.3f}" for c in table.columns if c != "n"} | {"n": "{:.0f}"}),
             width="stretch")
st.caption("정답 점수 = 채점 모델이 매긴 0/1/2점 평균 ÷ 2. 대응 일치율 = 답변·보류·되묻기·거절을 기대대로 골랐는지. "
           "출처 일치율 = 인용한 페이지가 정답 페이지인지. 숫자는 results/ 폴더에서 다시 계산했습니다(EVALUATION.md와 같음).")

st.subheader("실습 흐름")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("""
**1. 데이터**
- PDF 23개를 페이지별로 추출 (표·그림은 VLM으로 보충) → `corpus/pages.jsonl`
- 제공 질문 180개를 골든셋으로 변환, dev 90 / test 90 분할
- 직접 만든 질문 41개 (자작 v2)

**2. 청킹**
- 크기 300~1200 비교 → 950/119
- 구조 단위: 용어집은 용어 1개, 약관은 조 1개
""")
with c2:
    st.markdown("""
**3. 검색·답변 실험** (dev, 한 번에 한 요소만)
- 검색: 벡터 → Hybrid(벡터+BM25)
- 검색량 k, MMR 비교
- 답변 모델·프롬프트 (v1 → v4)
- LLM 재정렬 (후보 15 → 5)

모든 실험은 결과를 보기 전에 카드에 기준을 적고 진행
""")
with c3:
    st.markdown("""
**4. 에이전트 (LangGraph)**
- 질문 분류 → 검색 → 근거 판단 → 재검색 → 답변 → 인용 확인
- v2 (메모 + 답변 검토), 복구 (청크 잘림 진단 → 페이지 확장)

**5. 최종 test** (한 번만)
- T1~T4를 고정한 뒤 test 131문항
""")

t = summary_table()
dev, test = t[t["split"] == "dev"], t[t["split"] == "test"]
st.subheader("실험 규모")
kpi_row([
    ("dev 실험", f"{len(dev)}개", "검색만 비교한 실험 포함"),
    ("답변까지 채점한 dev 실험", f"{dev['정답 점수'].notna().sum()}개", None),
    ("test 실행", f"{len(test)}개", "최종 test (자작 세트 포함)"),
    ("실험 카드", f"{dev['카드'].dropna().nunique()}장", None),
])
st.info("왼쪽 메뉴에서 주제를 고르면 하위 페이지로 들어갑니다. 대부분의 페이지는 저장된 결과만 읽고, "
        "'질문 직접 실행'만 API를 사용합니다.")
