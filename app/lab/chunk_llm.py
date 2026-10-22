import pandas as pd
import streamlit as st

from lab.common import agent_bars, picked_note, picked_runs, styled, summary

st.title("🧪 청킹·검색 비교 (LLM 사용 후)")
st.caption("검색만 비교한 실험(LLM 없이) 중 실제로 LLM이 답을 쓰고 채점까지 한 실험들입니다. 같은 청킹·검색 설정을 "
           "LLM 없이 잰 수치(검색 상위 5개)와 LLM 답변 점수를 한 표에 놓아, 검색 지표가 오른 만큼 답도 좋아졌는지 봅니다.")
picked_note()

# answered chunking / retrieval experiments, in the order they were adopted; the twin is its --retrieval-only run
RUNS = [
    ("처음: Recursive 800/100", "dev_000_baseline", None),
    ("Recursive 900/112", "dev_001b_chunk900", "dev_001b_chunk900_retrieval"),
    ("구조 단위 + 900/112", "dev_002b_structure900", "dev_002b_structure900_retrieval"),
    ("+ Hybrid 검색", "dev_004_hybrid", "dev_004_hybrid_retrieval"),
    ("+ 답변 모델 3.6-flash (참고)", "dev_007_flash36", None),
    ("구조 단위 + 1000/125 체인", "dev_001d_chunk1000chain", "dev_001d_chunk1000chain_retrieval"),
    ("구조 단위 + 950/119 체인 (최종)", "dev_001e_chunk950chain", "dev_001e_chunk950chain_retrieval"),
    ("+ LLM 재정렬 15→5", "dev_013_rerank_flash36_fix", None),
]

cols = {}
for name, exp, twin in RUNS:
    s = summary(exp)
    if not s:
        continue
    t = summary(twin) if twin else {}
    sc, rt, co, la, cfg = s["scores"], s["retrieval"], s["cost"], s["latency_s"], s.get("config") or {}
    cols[name] = {
        "LLM 없이: 정답 페이지 포함": (t.get("retrieval") or {}).get("page_hit@5"),
        "LLM 없이: 근거 문장 포함률": (t.get("retrieval") or {}).get("evid@5"),
        "정답 점수": sc["correctness_mean"], "완전 정답률": sc["fully_correct"], "대응 일치율": sc["status_ok"],
        "출처 일치율": sc["citation_on_target"], "근거 문장 포함률": rt.get("evid@5"), "정답 페이지 포함": rt.get("page_hit@5"),
        "USD/문항": co["usd_per_question"], "p90 초": la["p90"],
        "답변 모델": (cfg.get("answer") or {}).get("model", "").replace("gemini-", ""), "실험": exp}
for r in picked_runs():  # the agents picked on agent_list, answered and graded the same way
    s = summary(r["experiment"])
    sc, rt, co, la, cfg = s["scores"], s["retrieval"], s["cost"], s["latency_s"], s.get("config") or {}
    cols["🤖 " + r["name"]] = {
        "LLM 없이: 정답 페이지 포함": None, "LLM 없이: 근거 문장 포함률": None,
        "정답 점수": sc["correctness_mean"], "완전 정답률": sc["fully_correct"], "대응 일치율": sc["status_ok"],
        "출처 일치율": sc["citation_on_target"], "근거 문장 포함률": rt.get("evid"), "정답 페이지 포함": rt.get("page_hit"),
        "USD/문항": co["usd_per_question"], "p90 초": la["p90"],
        "답변 모델": (cfg.get("answer") or {}).get("model", "").replace("gemini-", ""), "실험": r["experiment"]}

df = pd.DataFrame(cols)
num = df.drop(index=["답변 모델", "실험"])
st.dataframe(styled(num.apply(pd.to_numeric, errors="coerce")), width="stretch")
st.dataframe(df.loc[["답변 모델", "실험"]], width="stretch")
st.caption("열 = 실험(🤖는 agent_list에서 고른 agent), 초록 = 가장 좋은 값, 빨강 = 가장 나쁜 값. 위 두 줄은 LLM 없이 잰 검색 지표"
           "(그 설정의 --retrieval-only 실행, 상위 5개), 나머지는 LLM이 답하고 채점한 결과입니다. dev 90문항 기준이며 🤖 agent는 "
           "agent_list에서 실행한 문항 수 기준이라 문항 수가 다를 수 있습니다.")

agent_bars(num.apply(pd.to_numeric, errors="coerce"),
           ["정답 점수", "완전 정답률", "근거 문장 포함률", "LLM 없이: 근거 문장 포함률", "USD/문항"], height=150)

st.markdown("""
**읽는 법**
- 청크 크기만 바꾼 900/112는 답 점수가 처음과 거의 같았습니다(0.722 → 0.717). 청크 크기만으로는 답이 좋아지지 않았습니다.
- 구조 단위(0.756)와 Hybrid 검색(0.772)은 조금씩 올렸지만, 같은 설정을 다시 돌리면 90문항 중 약 14문항이 바뀌는 잡음 범위 안의 차이입니다.
- 950/119와 1000/125 체인은 답변 모델이 3.6-flash로 바뀐 뒤의 실행이라, 앞 열들과의 점수 차이에는 모델 효과가 섞여 있습니다(답변 모델 줄 참고).
- 재정렬(15→5) 열은 답변 프롬프트 v4도 들어간 체인입니다. 재정렬만의 효과는 실험 카드 013에서 같은 모델·프롬프트(3.6-flash + v4, 0.883)와 짝비교했고, 0.928로 순승 +7, 신뢰구간이 0을 넘지 않은 프로젝트 첫 변경이었습니다.
""")
