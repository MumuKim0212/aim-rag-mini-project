<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 003: 문서명·조 제목 머리말 (구조 청킹 위)

Status: rejected (게이트 불통과, 답변 실행 없음)
Date: 2026-10-21

## 1. Hypothesis

- Change (one variable): 카드 002에서 채택한 구조 청킹 위에 `chunking.add_header: false` → `true` (`configs/003-header.yaml`, `base: 002-structure.yaml`). 청크 맨 앞에 머리말 한 줄을 붙인다
  - 용어집·약관 청크 702개 모두: `[문서명]`
  - 약관 청크 중 자기 조 머리글(`제N조(제목)`)로 시작하지 않는 것(긴 조의 이어지는 조각과 첫 페이지 앞부분): `[문서명 > 제N조(제목)]` — 이런 조각은 75개이고 머리말이 새 정보를 준다. 조 머리글로 시작하는 청크는 이미 조 제목이 있으므로 문서명만 붙인다
  - `chunk_size`는 본문 길이만 제한한다(머리말은 그 뒤에 붙는다, 청크당 평균 16자 늘어남). 범위 B의 가이드·추가 자료는 제목 위치를 얻는 방법이 없어(카드 002 1절) 이 카드에서 바꾸지 않는다. 머리말은 구조 청킹에서만 구현했다
- 알아 둘 점: 문서명은 이미 임베딩 텍스트에 들어간다(`embedding.text_format: gemini2_qa`의 `title: <문서명> | text: …`, PROCESS.md 0절). 그래서 이 변경이 임베딩에 새로 주는 정보는 이어지는 조각 75개의 조 제목뿐이고, 나머지 청크는 문서명이 두 번 들어간다. 답변 단계에는 문서명이 출처 파일명으로 이미 보인다(`render_context`의 `(파일명, p.N)`)
- Failure it targets: PLAN H2 — 15개 약관에 "약관의 적용", "통지" 같은 같은 이름의 조항이 반복되어 비슷한 조항이 섞인다. PROCESS.md 6절 분류에서 약관 근거가 일부만 들어온 문항 POS047, POS050
- Expected effect: 거의 없을 것으로 예상한다. 이유: (1) 문서명은 이미 임베딩에 있다, (2) 카드 002 이후 범위 A의 evid@5가 0.950이라 올릴 여지가 작다(아래 2절). 있다면 이어지는 조각 75개를 정답으로 하는 문항에서만 나타날 것이다

## 2. Measurement

- Baseline run (reused, not rerun): 검색 `dev_002_structure_retrieval`, 답변 `dev_002_structure` (카드 002에서 채택한 기준. 비교 기준이 바뀌었으므로 `compare_to: dev_002_structure`)
- 달라지는 문항: 범위 A 질문(base_positive·base_negative 50문항, evid@5 계산 34문항). 범위 B 질문의 청크는 변하지 않아 실행하지 않는다
- Proxy metric (step 4): **evid@5**, 위 34문항. 함께 보고: page_hit@5, MRR, 문맥 글자 수, 정답 페이지가 이어지는 조각(머리말에서 조 제목이 복원된 75개)에 있는 문항의 변화
- **기준의 여유가 작다(카드를 쓰기 전에 `dev_002_structure`의 기존 결과에서 확인한 사실):** 34문항 중 evid@5 < 1인 문항은 6개(POS026, POS045, POS047, POS050, POS054, POS058)뿐이고, 그중 정답 점수가 2점 미만인 문항은 3개(POS047 1점, POS050 1점, POS054 0점)다. 따라서 이 지표로 오를 수 있는 문항은 최대 6개, headroom의 upside는 최대 3이다
- Split: dev
- Noise (step 3): 카드 002와 같은 범위 A 한정 잡음 5 / 50 (PROCESS.md 0절, 2026-10-21 결정)

## 3. Go/no-go criteria (written before results)

- LLM-free gate: 범위 A의 evid@5 순증(오른 문항 − 내린 문항, 34문항) > 5
- Headroom gate: `evalkit/headroom.py --metric evid@5 --noise 5`로 범위 A 문항에서 upside − risk > 5
- **위 두 게이트는 구조상 통과할 수 없다:** 오를 수 있는 문항이 최대 6개이고 upside가 최대 3이라서, 순증 6 이상과 upside − risk 6 이상은 불가능하다. 기준을 낮추지 않는다. 결과를 보고 기준을 바꾸면 안 되고, 여지가 작은 것이 이 카드의 결과이기 때문이다
- 결정 규칙(미리 정함): 게이트를 통과하지 못하면 답변 실행 없이 **채택하지 않고** 머리말 없는 카드 002 설정을 유지한다. 이때 evid@5가 내려가면(내린 문항이 오른 문항보다 많으면) 그것을 해로움으로 적는다. 오른 문항이 있어도 게이트가 막는다 — 지표가 이미 포화되어 답변 실행으로 이득을 보여 줄 수 없기 때문이다
- Cost cap: 평균 문맥 글자 수 ≤ 카드 002 기준의 1.1배(머리말은 청크당 약 16자, 문맥 약 80자 늘어남)
- Adopt if (answer run): 게이트를 통과한 경우에만 `dev_002_structure`와 같은 50문항 짝비교에서 변형 우세 − 기준 우세 > 0이고 바뀐 문항 > 5

## 4. LLM budget

- LLM-free 단계: 답변·채점 호출 0. 임베딩만 — 범위 A 인덱스 1회(702청크, 카드 002와 같은 규모 약 0.03 USD) + 질의 50개
- Planned calls if the gates pass: answers 50 + judge 50 (게이트를 통과할 가능성은 위 3절대로 매우 낮다)
- Calls so far in the project: submission/PROCESS.md 장부 참고

## 5. LLM-free results

dev 범위 A 50문항(evid@5 계산 34문항), `--retrieval-only`. 실험 이름 `dev_003_header_retrieval`, 범위 A 인덱스 702청크(카드 002와 같은 개수), 구축 0.032 USD. 순증은 evid@5가 오른 문항 − 내린 문항.

| Config | evid@5 (dev 34) | Net vs 002 (+/−) | page_hit@5 | MRR | Context chars (34문항 평균) |
|---|---|---|---|---|---|
| 002 structure | 0.950 | – | 1.000 | 0.985 | 1,795 |
| 003 header | 0.921 | **−1** (0 / 1), diff −0.029, 95% CI [−0.088, +0.000] | 0.971 | 0.956 | 1,871 (1.04배) |

- 내린 문항: POS052 하나. 정답 페이지 2곳(02_파생상품계좌설정약관 p.1, p.6)이 모두 상위 5개에서 빠졌다(evid@5 1.0 → 0, page_hit@5 1 → 0). 오른 문항은 없다
- 순위만 바뀐 문항: MRR이 POS018 0.5 → 1.0으로 오르고 POS058 1.0 → 0.5, POS052 1.0 → 0으로 내렸다. gold@5는 POS027 2 → 1, POS052 2 → 0, NEG033 2 → 3
- 조 제목이 복원된 조각(75개)이 정답 페이지에 있는 문항은 14개(POS019 POS028 POS037 POS039 POS044 POS045 POS047 POS050 POS051 POS052 POS058 NEG019 NEG031 NEG033)다. 이 중 evid@5가 바뀐 문항은 POS052 하나(내림)이고, 1절에서 겨냥한 POS047·POS050은 그대로(각 0.58, 0.88)다
- Headroom (`evalkit/headroom.py --metric evid@5 --noise 5`, 범위 A 34문항, 기준 `dev_002_structure`의 채점): upside 0, 이미 정답인데 오른 문항 0, risk 1 (POS052). upside − risk = **−1** vs 5
- Cost cap: 문맥 1.04배로 상한(1.1배) 안
- Gates passed? **no** — 순증 −1 ≤ 5, upside − risk −1 ≤ 5. 3절에서 밝혔듯이 기준의 여유가 작아 통과할 수 없는 게이트였고, 결과도 오른 문항이 없어 이득이 확인되지 않았다

## 6. Answer run (only if the gates passed)

게이트 불통과로 실행하지 않았다. LLM 호출 0.

## 7. Decision and notes

- Decision: **reject** — 머리말 없는 카드 002 설정을 유지한다. 답변 실행 없음
- Why, with question IDs:
  - 겨냥한 문항(POS047, POS050)이 오르지 않았고, 오른 문항이 하나도 없다. 내린 문항 POS052는 정답 페이지 2곳을 모두 잃었다
  - 이어지는 조각의 조 제목이 새 정보를 주는 곳은 75개 조각이지만, 그 조각이 정답 페이지에 있는 14문항 중 13문항은 검색이 같았다. 조 제목이 없어서 못 찾는 경우가 이 dev에 거의 없다는 뜻이다. 002 이후 evid@5 < 1인 문항 6개(POS026, POS045, POS047, POS050, POS054, POS058)는 머리말이 닿지 않는 원인이다(근거 구절이 문맥에 일부 없음)
- POS052가 내린 이유는 모른다. 추측: 문서명 `[02_파생상품…]`이 임베딩 텍스트에 두 번 들어가면서(이미 `title:` 접두어로 한 번 들어간다) 질문의 "선물 계좌"와 문서명이 겹치는 다른 약관 조각이 위로 올라왔을 수 있다. 확인하지 않았다(질문 하나이고 판정이 이미 났다)
- What the criteria missed, if anything:
  - 카드 002 이후 범위 A의 evid@5가 0.950이라 이 지표로는 개선을 보일 수 없다. 이 카드는 처음부터 게이트를 통과할 수 없었고, 결과는 "이득 없음, 해로울 수 있음"이다. 이득 여부를 가리려면 답변 단계 지표가 필요한데, 오른 문항이 없어서 답변 실행으로 얻을 것도 없다
  - 문서명 접두어가 이미 임베딩에 들어가는 설정(`text_format: gemini2_qa`)에서는 이 가설(문서명을 붙이면 비슷한 조항을 가린다)의 효과를 따로 볼 수 없다. 접두어 없이 비교(`text_format: none` 대 머리말)는 카드 006(임베딩)의 몫이다
  - 범위 B(가이드)에는 머리말을 구현하지 않았다. 가이드에 대해서는 모른다
- 다음: 004 검색 방식(BM25 / Hybrid). 구조 청킹(002)이 기준이다
