# 제출물

과제(`docs/assignment.md`)의 제출물 목록과 위치. 문서는 이 폴더에, 코드·데이터·결과는 레포의 해당 폴더에 있다.

| 제출물 | 위치 | 상태 |
|---|---|---|
| RAG 실험 계획: 목적·가설, 사용할 PDF·질문 세트, 비교할 설정과 고정 조건, 평가 지표·측정 방법, 결과 기록 항목·형식·비교 방법 | [PLAN.md](PLAN.md) | 작성됨 |
| Agent 그래프 구조도: 노드 역할, 흐름과 분기, 종료 조건 | [AGENT_GRAPH.md](AGENT_GRAPH.md) | 구현 반영, 최종 체인 수치와 v2 시도(7절) 포함 (2026-10-22) |
| RAG Agent와 평가 루프 구현 코드, 실행 방법 | 코드 `src/`, `scripts/`, `evalkit/` · 실행 방법 [../README.md](../README.md), 화면으로 보기 `streamlit run app/streamlit_app.py` | 완료 |
| 사용한 PDF·질문 세트, 직접 작성한 골든셋(기준 답변·근거 포함) | PDF `01_data/` · 질문 `02_questions/`, `03_answers/` · 골든셋(제공 180 + 자작 41문항)과 기록 `golden/` | 완료 |
| 실행 기록 | `results/<experiment>/` (`summary.json`, `grades.jsonl`, `metrics.jsonl`, 주요 실험은 `runs.jsonl`) | 완료 |
| 비교 실험 결과 | 실험 카드 `experiments/`, 요약 [PROCESS.md](PROCESS.md) 7절, 최종 비교 [EVALUATION.md](EVALUATION.md) | 완료 |
| 실패 사례와 개선점 | [PROCESS.md](PROCESS.md) 6·10절, [EVALUATION.md](EVALUATION.md) | 완료 |
| 회고 (과제 목록 밖, 추가) | [RETROSPECTIVE.md](RETROSPECTIVE.md) | 작성됨 (2026-10-22) |
