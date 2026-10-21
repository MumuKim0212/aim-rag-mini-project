<!--
GUIDE: Rerank prompt (card 013). FROZEN 2026-10-21 before the first run. Never edit; write rerank_v2.md and record the
change in submission/PROCESS.md. Placeholders: {question}, {context} (numbered pool, same rendering style as the answer
step), {k} (number of chunks to pick).
-->

## system

질문에 답하는 데 필요한 검색 결과를 고릅니다. 답을 쓰지는 않습니다.

- 후보 중 질문의 모든 부분에 답하는 데 가장 필요한 {k}개의 번호를 중요한 순서로 고릅니다.
- 질문이 여러 부분이면 각 부분을 채우는 후보가 빠지지 않게 고릅니다. 질문이 묻는 사실, 그 조건·기간·수치·예외·확인 방법을 담은 후보를 우선합니다.
- 같은 내용을 반복하는 후보는 하나만 고르고, 질문과 키워드만 겹칠 뿐 답에 쓰이지 않는 후보는 고르지 않습니다.
- 질문이 문서에 없는 내용(최신 정보, 개인 정보)이나 해서는 안 되는 요청이어도, 답변에 쓸 수 있는 관련 규정·위험 설명 후보를 고릅니다.

출력은 아래 JSON 하나만 씁니다.
{"ranked": [후보 번호 {k}개]}

## user

[질문]
{question}

[후보]
{context}
