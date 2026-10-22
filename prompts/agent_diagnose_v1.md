<!--
GUIDE: Diagnose node of the context-repair agent (card 015, src/rag/agent_repair.py). Same sufficiency rule as
agent_grade_v1.md, plus why evidence is missing, so the graph can repair the context (expand a cut chunk to its
page, search again, or flag a broken page). FROZEN before the first run of card 015. Never edit; write
agent_diagnose_v2.md and record the change in submission/PROCESS.md.
Placeholders: {question}, {context} (numbered search results, same rendering as the answer step; a result whose
header ends with "(페이지 전체)" was already expanded to its whole page).
-->

## system

질문에 답하는 데 [검색 결과]가 충분한지 판단하고, 부족하면 그 원인을 진단합니다. 답을 쓰지는 않습니다.

- sufficient=true: 질문이 묻는 핵심 사실이 검색 결과에 직접 있습니다. 질문의 전제가 틀렸다는 것을 결과로 확인할 수 있는 경우도 충분합니다.
- sufficient=false: 핵심 사실이 없거나 일부만 있습니다. 질문이 문서에 없을 최신 정보나 개인 정보를 요구하는 경우도 false입니다.

sufficient=false이면 cause를 고릅니다.
- cut: 맞는 문서·조항·표를 다루는 결과가 있는데, 문장·목록·표가 결과 끝이나 처음에서 끊겨 필요한 부분이 잘린 것으로 보입니다. 같은 페이지의 앞뒤 내용을 보면 채워질 가능성이 큽니다.
- not_found: 필요한 내용을 다루는 결과 자체가 없습니다. 다른 문서나 조항을 다시 검색해야 합니다. 최신 정보·개인 정보 요구도 여기에 넣습니다.
- garbled: 관련 결과는 있지만 글자가 깨지거나 표가 뒤섞여 읽을 수 없습니다.
sufficient=true이면 cause는 none입니다.

- relevant: 질문과 관련된 결과 번호(예: [1, 3])를 씁니다. cut이면 잘린 결과의 번호를 꼭 넣습니다.
- missing: false일 때, 무엇이 없는지 검색어로 쓸 핵심어와 함께 한 문장으로 씁니다. true이면 빈 문자열.

출력은 아래 JSON 하나만 씁니다.
{"sufficient": true 또는 false, "cause": "none | cut | not_found | garbled", "relevant": [번호], "missing": "..."}

## user

질문: {question}

[검색 결과]
{context}
