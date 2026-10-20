<!--
GUIDE: 제출물 "Agent 그래프 구조도". 각 노드의 역할, 노드 간 흐름과 분기, 종료 조건을 적는다.
- 지금은 구현 전 초안이다. 구현 후에는 LangGraph에서 생성한 mermaid(graph.get_graph().draw_mermaid())로 2절을 바꾸고,
  초안과 달라진 점을 4절에 남긴다.
- 노드 구성을 바꾸면 PROCESS.md 8절에 이유(실패 분석의 어떤 유형 때문인지, 문항 ID)를 적는다.
이 안내 주석은 채운 뒤에도 지우지 않는다.
-->

# Agent 그래프 구조도

상태: 초안 (구현 전, 2026-10-20)

## 1. 설계 의도

- 기본 RAG와 같은 답변 프롬프트(`prompts/answer_v1.md`)를 쓴다. 차이는 아래 구조뿐이다(PLAN.md 3.3절).
- 기본 RAG가 LLM 1회로 하던 판단을 나눈다: 답할 질문인지(classify), 근거가 충분한지(grade), 인용이 맞는지(cite_check).
- 근거가 부족하면 질문을 고쳐 다시 검색한다(rewrite → retrieve, 최대 2회).

## 2. 그래프

```
START
  └─ classify ── 질문 유형 판단: 문서 질의 / 정보 부족 / 개인화·예측 요청 / 부적절 요청 / 주입 포함
       ├─ 부적절·개인화 요청 → refuse  → END
       ├─ 정보 부족          → clarify → END (되묻기)
       └─ 문서 질의 (주입 문구는 제거)
            └─ retrieve ── 검색 도구: query → 상위 k 청크 (chunk_id, 파일, 페이지)
                 └─ grade ── 근거로 답할 수 있는가
                      ├─ 부족 & 재검색 < 2회 → rewrite (질문 재작성) → retrieve
                      ├─ 부족 & 재검색 2회   → abstain (보류 + 확인할 자료 안내) → END
                      └─ 충분 → generate (인용 포함 답변, 잘못된 전제는 정정)
                                 └─ cite_check ── 인용한 청크가 실제 문맥에 있는가 (코드)
                                      ├─ 통과 → END
                                      └─ 실패 → generate 1회 재시도 → END
```

## 3. 노드

| 노드 | 역할 | LLM | 출력 |
|---|---|---|---|
| classify | 질문 유형을 나누고, 질문 속 주입 문구를 떼어 낸다 | 1회 | 유형, 정리한 질문 |
| refuse | 거절 이유와 문서로 말할 수 있는 일반 정보 안내 | 0–1회 | status=refused |
| clarify | 답에 필요한데 질문에 없는 정보를 묻는다 | 0–1회 | status=clarify |
| retrieve | 검색 도구 호출. 결과는 누적 문맥에 더한다 | 0 (임베딩만) | 청크 목록 |
| grade | 누적 문맥으로 답할 수 있는지 판단, 부족하면 무엇이 없는지 적는다 | 1회 | 충분 / 부족 + 이유 |
| rewrite | 부족한 이유를 바탕으로 검색어를 다시 쓴다 | 1회 | 새 검색어 |
| abstain | 보류 이유와 확인할 자료 안내 | 0–1회 | status=abstained |
| generate | 답변 프롬프트로 답변과 인용 번호 생성 | 1회 | status, answer, citations |
| cite_check | 인용 번호가 실제로 넘긴 문맥 안에 있는지 코드로 확인 | 0 | 통과 / 실패 |

## 4. 종료 조건

- END에 도달하는 경우는 넷이다: 답변 완료(answered), 보류(abstained), 되묻기(clarify), 거절(refused).
- 재검색은 최대 2회, 인용 재시도는 최대 1회. 최악의 경우 LLM 호출은 8회(classify 1, grade 3, rewrite 2, generate 2)이며, refuse·clarify·abstain이 LLM을 쓰면 그 1회가 더해진다.

## 5. 측정 장치 (구현 전에 정함)

- 첫 검색 문맥과 누적 문맥을 따로 `metrics.context_metrics`로 채점한다. Agent의 첫 검색은 같은 질문에 대한 기본 RAG의 검색과 같으므로 직접 비교한다.
- 답변이 재검색으로만 찾은 청크를 인용했는지 기록한다(재검색의 효과를 문항 단위로 확인).
- 노드마다 판단, 모델, 토큰, 시간을 `steps`에 남긴다.

## 6. 초안과 달라진 점

_구현 후 작성_
