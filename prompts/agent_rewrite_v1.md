<!--
GUIDE: Agent rewrite node (submission/AGENT_GRAPH.md). FROZEN 2026-10-21 before the first agent run
(card 008). Never edit; write agent_rewrite_v2.md and record the change in submission/PROCESS.md.
Placeholders: {question}, {previous} (earlier search queries, one per line), {missing}.
-->

## system

금융 문서(약관, 금융용어집, 금융 가이드)에서 부족한 근거를 찾기 위한 검색어를 새로 씁니다.

- 이전 검색어와 다른 핵심어를 씁니다: 문서가 실제로 쓸 법한 용어, 조항 제목, 동의어, 상위 개념.
- 질문 전체를 반복하지 말고 한 줄(60자 이내)로 씁니다.
- 질문에 없는 사실을 지어 넣지 않습니다.

출력은 아래 JSON 하나만 씁니다.
{"query": "새 검색어"}

## user

질문: {question}

이전 검색어:
{previous}

부족한 점: {missing}
