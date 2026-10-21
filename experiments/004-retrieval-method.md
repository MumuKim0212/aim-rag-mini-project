<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 004: 검색 방식 — 벡터 / BM25 / Hybrid (구조 청킹 위)

Status: rejected (게이트 불통과, 답변 실행 없음)
Date: 2026-10-21

## 1. Hypothesis

- Change (one variable): `retrieval.method`만 바꾼다. 청킹은 카드 002에서 채택한 구조 청킹(`configs/002-structure.yaml`), 임베딩·k=5·답변 프롬프트·모델은 그대로다
  - `configs/004-bm25.yaml`: `bm25` — Kiwi 형태소 분석으로 명사·동사/형용사 어간·어근·외국어·숫자만 남겨 토큰으로 쓰고(`src/rag/retrieval.py`의 `kiwi_tokens`), `rank_bm25.BM25Okapi` 기본값(k1=1.5, b=0.75)으로 점수를 매긴다. 임베딩 호출이 없고, 같은 청킹의 벡터 인덱스의 `chunks.jsonl`을 읽는다
  - `configs/004-hybrid.yaml`: `hybrid` — 벡터 상위 20개와 BM25 상위 20개(후보 수 `max(4k, 20)`)를 각각 0~1로 min-max 정규화하고 `0.5 × 벡터 + 0.5 × BM25`로 합산해 상위 k개를 고른다. 한쪽 목록에 없는 청크는 그쪽 점수가 0이다
  - **α(0.5), 후보 수, BM25 매개변수, 형태소 필터는 결과를 보기 전에 고정하고 조정하지 않는다.** 조정하면 변형이 늘어나 선택 편향이 생기기 때문이다
- Failure it targets: PLAN H3 — 정확한 용어를 묻는 질문은 BM25가, 상황을 풀어 쓴 질문은 벡터 검색이 잘 맞고 Hybrid가 둘 다 무난하다. 기준(구조 청킹)에서 근거가 일부만 들어온 문항은 74문항 중 33개이고, 대부분 additional 세트다(30문항 중 21개, life_guide 10문항 중 6개, base_positive 30문항 중 6개). 이 문항들이 BM25의 정확한 낱말 일치로 좋아지는지를 본다
- Expected effect: base_positive(용어·약관 문항)는 이미 evid@5 0.943이라 오를 여지가 작고, BM25 단독은 additional(상황 서술형, 질문 낱말과 문서 낱말이 다른 문항)에서 벡터보다 낮을 것으로 예상한다. Hybrid는 additional에서 약간 오를 수 있으나 크게 오를 것으로는 기대하지 않는다. 방향도 확신하지 않는다

## 2. Measurement

- Baseline run (reused, not rerun): 검색 `dev_002_structure_all_retrieval`(구조 청킹, 벡터 k=5, dev 90문항 전체. 범위 A 인덱스와 범위 B 인덱스 모두 구조 청킹). 카드 002 이전의 `dev_000_baseline`(Recursive 800/100)이 아니다
- 범위: 이 변경은 모든 dev 질문(범위 A 50 + 범위 B 40)의 검색 결과를 바꿀 수 있다. 그래서 잡음은 전체 기준 14를 쓴다(PROCESS.md 4절)
- Proxy metric (step 4): **evid@5**, 정답 페이지가 있는 74문항. 함께 보고: page_hit@5, MRR, gold@5, 문맥 글자 수, 세트별(base_positive / life_guide / additional) evid@5와 순증, 검색 시간
- Split: dev
- Noise (step 3): (a) 14 / 90, (b) 3 / 90

## 3. Go/no-go criteria (written before results)

변형 2개(bm25, hybrid) 각각을 기준과 비교한 뒤 아래 규칙으로 하나를 고른다.

- Cost cap: 평균 문맥 글자 수 ≤ 기준의 1.5배(기준 2,331자 → 3,496자). 넘는 변형은 후보에서 빼고 결과만 보고한다
- 선택 규칙: cost cap 안의 변형 중 evid@5 순증(오른 문항 − 내린 문항, 74문항)이 큰 쪽. 차이가 3문항 이내이면 **문맥이 짧은 쪽**을 고른다
- LLM-free gate: 고른 변형의 evid@5 순증 > 14
- Headroom gate: 고른 변형에서 `evalkit/headroom.py --metric evid@5 --noise 14`로 upside − risk > 14. 기준 점수는 `dev_002_structure`의 채점(범위 A 50문항)과 `dev_000_baseline`의 채점(범위 B 40문항)을 합쳐 쓴다. 범위 B 질문은 구조 청킹과 Recursive의 검색 결과가 같아서(카드 002 7절 정정: 40문항 중 ADD-RP04 하나만 다름) 기존 채점을 기준 점수로 쓸 수 있다
- 선택 편향: 변형이 둘이라 가장 좋은 값을 고르는 편향이 있다. 그래서 답변 실행은 고른 변형 하나만 한다
- Adopt if (answer run): 아래 4절의 기준 답변 실행(`dev_002_structure_all`)과 고른 변형을 dev 90문항에서 짝비교해 변형 우세 − 기준 우세 > 0이고 바뀐 문항 수 > 14. 95% CI가 0을 벗어나는지는 함께 보고하되 CI만으로는 채택하지 않는다
- 게이트를 통과하지 못하면 답변 실행 없이 벡터 검색을 유지하고, LLM 없는 지표로 비교 결과를 보고한다(PLAN 3.2, 2026-10-20 결정)

## 4. LLM budget

- LLM-free 단계: 답변·채점 호출 0. 인덱스는 구조 청킹 인덱스를 그대로 쓴다(새로 만들지 않음). 질의 임베딩 90개는 벡터 검색과 Hybrid에만 든다. BM25는 임베딩 호출도 없다
- Planned calls if the gates pass: 구조 청킹 위 기준 답변 실행 `dev_002_structure_all`(answers 90 + judge 90, 기존 `dev_002_structure`는 범위 A 50문항뿐이라 B를 포함한 같은 조건의 짝비교용 기준이 필요하다) + 고른 변형(answers 90 + judge 90) = answers 180 + judge 180
- Calls so far in the project: submission/PROCESS.md 장부 참고

## 5. LLM-free results

dev 90문항 전체(evid@5 계산 74문항), `--retrieval-only`. 실험 이름 `dev_004_bm25_retrieval`, `dev_004_hybrid_retrieval`. 인덱스는 새로 만들지 않았다. 순증은 evid@5가 오른 문항 − 내린 문항.

| Config | evid@5 (dev 74) | Net vs baseline (+/−) | page_hit@5 | MRR | gold@5 | Context chars (90문항 평균) |
|---|---|---|---|---|---|---|
| structure + vector (baseline) | 0.789 | – | 0.960 | 0.894 | 2.07 | 2,331 |
| bm25 | 0.714 | −4 (14 / 18), diff −0.075, 95% CI [−0.155, +0.006] | 0.892 | 0.752 | 1.66 | 2,496 (1.07배) |
| **hybrid** (α 0.5) | **0.804** | **+5** (12 / 7), diff +0.015, 95% CI [−0.027, +0.058] | 0.973 | 0.898 | 1.97 | 2,503 (1.07배) |

세트별 evid@5 (오른 문항 / 내린 문항):

| 세트 (n) | 벡터(기준) | bm25 | hybrid |
|---|---|---|---|
| base_positive (30) | 0.943 | 0.781 (1 / 8) | 0.909 (1 / 4) |
| life_guide (10) | 0.773 | 0.582 (0 / 4) | 0.751 (1 / 1) |
| additional (30) | 0.612 | 0.686 (13 / 5) | 0.691 (10 / 2) |

- 선택 규칙 적용: 두 변형 모두 문맥 상한(3,496자) 안이다. 순증이 큰 쪽은 hybrid(+5 대 −4)라 **hybrid**를 골랐다
- LLM-free gate: hybrid의 순증 +5 ≤ 14 → **불통과**
- Headroom (`evalkit/headroom.py --metric evid@5 --noise 14`; 기준 점수는 `scripts/merge_grades.py`로 범위 A는 `dev_002_structure`, 범위 B는 `dev_000_baseline`의 채점을 합침)
  - hybrid: upside 9 (ADD-HF07 ADD-HF10 ADD-PF01 ADD-PF08 ADD-PF09 ADD-RP06 ADD-SE06 ADD-SE08 POS054), 이미 정답인데 오른 문항 3, risk 7 (ADD-HP04 ADD-IN08 POS045 POS050 POS058 POS059 POS079). upside − risk = **2** ≤ 14
  - bm25(참고): upside 11, risk 17, upside − risk = −6
- Gates passed? **no** — 6절은 비운다

## 6. Answer run (only if the gates passed)

게이트 불통과로 실행하지 않았다. LLM 호출 0.

## 7. Decision and notes

- Decision: **reject** — 벡터 검색을 유지한다(구조 청킹 + 벡터 k=5). 답변 실행 없음
- Why, with question IDs:
  - Hybrid는 additional에서 evid@5를 0.612 → 0.691로 올렸지만(10문항 오름: ADD-HF07, HF10, IN01, PF01, PF08, PF09, RP06, SE03, SE06, SE08; 2문항 내림: ADD-HP04, ADD-IN08) base_positive에서 0.943 → 0.909로 내렸다(POS045, POS050, POS058, POS059 4문항). 합치면 순증 +5로 잡음 14 안이다
  - 1절의 예상은 방향이 틀렸다. "정확한 용어 질문은 BM25, 상황 서술형은 벡터"로 예상했는데 반대였다. BM25 단독은 용어·약관 문항(base_positive)에서 8문항을 내렸고(POS021, POS044, POS045, POS050, POS051, POS052, POS058, POS059; 오른 것은 POS054 하나), 상황 서술형 additional에서는 13문항이 올랐다(ADD-HF05, HF06, HF07, HF10, IN01, PF01, PF08, PF09, RP05, RP06, SE03, SE06, SE08; 내린 것은 ADD-HP04, HP06, HP10, IN08, PF06). 원인은 확인하지 않았다. 추측: 용어집 청크가 아주 짧아(평균 약 100자) BM25의 낱말 일치 점수가 안정적이지 않고, additional 문항은 문서 본문의 낱말을 질문에 풀어 쓴 경우가 많아 낱말 일치가 도움이 됐을 수 있다
  - 구조 청킹 이후 base_positive의 evid@5가 이미 0.943이라 이 세트는 내릴 일만 남아 있었다
- What the criteria missed, if anything:
  - 세트별로 효과가 반대라 세트(질문 유형)에 따라 검색 방식을 고르면 이득이 있을 수 있다(additional에는 hybrid). 그러나 질문 유형을 미리 알 수 없고, 이 결과를 본 뒤 만든 규칙이라 이 카드의 판정에는 쓰지 않았다. 후속 카드가 필요하면 사전 등록으로 따로 해야 한다
  - 3절의 α(0.5) 조정은 하지 않았다. 다른 α가 더 나은지는 모른다
  - 질문마다 BM25 토큰(`있` 같은 의미 없는 어간이 들어간다)을 거르는 정도는 조정하지 않았다
- 다음: 005 검색량(k=3 / 8, MMR). 기준은 구조 청킹 + 벡터 검색이다
