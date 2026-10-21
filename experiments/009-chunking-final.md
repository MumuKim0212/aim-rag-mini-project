<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 009: 청킹 3종 최종 비교 — 구조 / Recursive 800/100 / Recursive 1000/125 (검색 구성 고정)

Status: llm-free done (답변 수준 비교는 실행하지 않음)
Date: 2026-10-21

**이 카드는 사전 등록이 아니다.** LLM 없는 수치는 카드 001(Recursive 1000/125)과 카드 002(구조 청킹)에서 이미 계산해 본 실행을 재사용한다. 1~3절은 그 수치를 본 뒤에 쓴 것이다. 새 LLM 호출은 없다. 아직 실행하지 않은 답변 수준 비교(6절)의 기준만 실행 전에 적어 둔다.

## 1. Hypothesis

- Change (one variable): 청킹만 바꾼다. 검색 구성은 카드 004~006에서 모두 기각되어 **벡터 검색 k=5, MMR 없음, `gemini-embedding-2`(접두어 사용)** 로 고정되었다. 답변 프롬프트·모델도 같다. 후보 3개:
  - R800: Recursive 800/100 — 기준 (`configs/baseline.yaml`, 실행 `dev_000_baseline`)
  - R1000: Recursive 1000/125 (`configs/001-chunk1000.yaml`, 실행 `dev_001_chunk1000_retrieval`)
  - STRUCT: 구조 청킹 — 용어집은 용어 단위, 약관은 조 단위, 그 밖의 문서는 Recursive 800/100 (`configs/002-structure.yaml`, 실행 `dev_002_structure_all_retrieval`)
- Failure it targets: PROCESS.md 6절 병목 "근거 부족"(기준에서 근거가 일부만 들어온 문항 25개, PROCESS.md 6절 분류)
- Expected effect: 카드 001에서 R1000은 평균 근거 포함률을 올리지만 문맥이 1.2배로 늘고, 카드 002에서 STRUCT는 용어집·약관 문항을 크게 올리고 문맥은 줄인다. 두 방식이 서로 다른 문항을 푼다고 본다

## 2. Measurement

- Baseline run (reused, not rerun): R800 `dev_000_baseline`. 모든 후보가 같은 검색 구성의 같은 dev 90문항 실행이다
- Proxy metric: **evid@5**, 정답 페이지가 있는 dev 74문항. 함께 보고: page_hit@5, MRR, gold@5, 문맥 글자 수, 세트별 evid@5, 일회성 인덱스 구축 비용
- Split: dev
- Noise: 전체 (a) 14 / 90, (b) 3 / 90. 범위 A 한정 잡음은 5 / 50(PROCESS.md 0절)

## 3. Go/no-go criteria

- 후보 둘(R1000, STRUCT)을 각각 R800과 비교한다. 게이트는 프로젝트 규칙 그대로다: evid@5 순증 > 14, `evalkit/headroom.py --noise 14`의 upside − risk > 14. 통과하지 못하면 답변 실행을 하지 않는다. 카드 002의 사전 등록 기준(범위 A 한정 잡음 5)도 STRUCT에 대해 함께 보고한다
- STRUCT와 R1000의 직접 비교: evid@5 순증이 큰 쪽. 차이가 3문항 이내이면 문맥이 짧은 쪽
- Cost cap: 평균 문맥 글자 수 ≤ R800의 1.5배(3,064자 → 4,596자)

## 4. LLM budget

- 새 LLM 호출 없음. 인덱스도 새로 만들지 않았다(모두 기존 인덱스)
- 6절의 답변 수준 비교를 하려면: STRUCT 전체 dev 90문항 answers 90 + judge 90, R1000 answers 90 + judge 90 = answers 180 + judge 180, 약 0.5 USD(추정). **프로젝트 규칙상 게이트를 통과하지 못한 답변 실행은 허용되지 않는다. 이 실행은 사용자의 예외 승인이 있어야 한다**

## 5. LLM-free results

dev 90문항(evid@5 계산 74문항), 검색 구성 고정. 순증은 evid@5가 오른 문항 − 내린 문항.

| Config | evid@5 | page_hit@5 | MRR | gold@5 | Context chars (74문항 평균) | 인덱스 구축 |
|---|---|---|---|---|---|---|
| R800 (기준) | 0.697 | 0.878 | 0.800 | 1.92 | 3,064 | 0.140 USD |
| R1000 | 0.764 | 0.932 | 0.812 | 2.00 | 3,705 (1.21배) | 0.139 USD |
| STRUCT | **0.789** | **0.959** | **0.894** | 2.07 | **2,331 (0.76배)** | 0.140 USD |

세트별 evid@5:

| 세트 (n) | R800 | R1000 | STRUCT |
|---|---|---|---|
| base_positive (30) | 0.717 | 0.836 | **0.943** |
| life_guide (10) | 0.773 | **0.820** | 0.773 |
| additional (30) | 0.612 | **0.641** | 0.612 |

짝비교 (evid@5, 74문항, 잡음 14):

| 비교 | 평균 차이 (95% CI) | 오른 / 내린 | 순증 | headroom (upside / risk) |
|---|---|---|---|---|
| R1000 − R800 | +0.066 [+0.024, +0.118] | 17 / 7 | +10 | 11 / 6 → 5 |
| STRUCT − R800 | +0.092 [+0.031, +0.159] | 10 / 1 | +9 | 8 / 1 → 7 |
| STRUCT − R1000 | +0.026 [−0.033, +0.092] | 11 / 12 | **−1** | – |

- STRUCT − R800의 내린 1문항: POS026. 오른 10문항: POS001 POS006 POS013 POS017 POS021 POS044 POS050 POS052 POS057 POS058(모두 범위 A 질문)
- STRUCT − R1000: STRUCT가 나은 문항 POS006 POS013 POS017 POS045 POS052 POS074, ADD-HF06 ADD-HF07 ADD-IN08 ADD-PF01 ADD-SE08. R1000이 나은 문항 POS026 POS047 POS061 POS070, ADD-HP09 ADD-HP10 ADD-IN01 ADD-IN10 ADD-PF06 ADD-PF08 ADD-RP05 ADD-SE03
- 게이트 (전체 dev 90, 잡음 14): R1000 순증 +10 ≤ 14, headroom 5 ≤ 14 → 불통과. STRUCT 순증 +9 ≤ 14, headroom 7 ≤ 14 → 불통과
- 카드 002의 사전 등록 기준(범위 A 한정 잡음 5, 범위 A 문항 34개에서 비교)에서 STRUCT는 순증 +9 > 5, headroom 7 > 5로 통과했고 답변 실행(`dev_002_structure`, 범위 A 50문항)까지 마쳤다: 정답 점수 0.730 → 0.830, 우세 9 / 열세 2 / 같음 39
- 직접 비교 선택 규칙: STRUCT − R1000 순증 −1은 3문항 이내이므로 문맥이 짧은 STRUCT(2,331자 대 3,705자)를 고른다

## 6. Answer-level comparison (실행하지 않음, 사용자 승인 필요)

현재 답변 수준의 증거는 STRUCT의 범위 A 50문항 하나뿐이다(R800 대비). R1000의 답변 수준 증거는 없다(카드 001에서 게이트 불통과). 전체 dev 90문항에서 세 후보의 답변 점수를 비교하려면 STRUCT 전체와 R1000 전체의 답변 실행이 필요하다. 실행 전에 적어 두는 기준:

- 실험 이름 `dev_009_struct_all`(STRUCT), `dev_009_r1000_all`(R1000), 비교 기준은 `dev_000_baseline`(R800)
- 각 후보를 R800과 짝비교해 우세 − 열세 > 0이고 바뀐 문항 수 > 14일 때 R800보다 낫다고 본다. 95% CI는 함께 보고하고 CI만으로 판단하지 않는다
- STRUCT와 R1000을 직접 짝비교해 같은 규칙을 적용한다. 바뀐 문항이 14 이하이거나 우세 − 열세가 0이면 구분하지 못한 것으로 보고, 문맥이 짧은 STRUCT를 고른다
- 깨진 출력 건수(`scripts/garble_scan.py`)를 함께 보고한다

## 7. Decision and notes

- Decision (잠정): **구조 청킹(STRUCT)을 최종 후보로 정한다.** 답변 수준의 직접 비교는 하지 않았다
- Why, with question IDs:
  - STRUCT는 세 후보 중 evid@5(0.789), page_hit@5(0.959), MRR(0.894)이 가장 높고 문맥이 가장 짧다(2,331자). R1000은 R800보다 문맥이 1.21배로 늘면서 evid@5를 올린다
  - 답변 수준의 증거가 있는 후보는 STRUCT뿐이다: 범위 A 50문항에서 정답 점수 0.730 → 0.830(카드 002). 용어집 정의 4문항(POS001·006·013·021)이 해결되었고 이는 R1000이 풀지 못한 문항(POS006, POS013)을 포함한다
  - STRUCT − R1000은 순증 −1로 구분되지 않는다. 두 방식은 다른 문항을 푼다: STRUCT는 용어집·약관(base_positive 0.943 대 0.836)에서, R1000은 가이드·추가 자료(life_guide 0.820 대 0.773, additional 0.641 대 0.612)에서 낫다
  - 게이트(전체 dev, 잡음 14)에서는 STRUCT도 R1000도 R800보다 낫다고 말할 수 없다(순증 +9, +10). 범위 A 한정 기준(카드 002)에서만 STRUCT가 통과했다. 따라서 "STRUCT가 R800보다 낫다"는 범위 A 질문에 대한 결론이다
- What the criteria missed, if anything:
  - 이 카드는 사전 등록이 아니다(위). 기준 문장 일부가 수치를 본 뒤에 쓰였다
  - 두 방식이 서로 다른 영역에서 낫다. 구조 청킹의 "그 밖의 문서"를 1000/125로 바꾸고 용어집·약관만 구조 단위로 두는 조합(COMBO)은 두 이점을 합칠 수 있어 보였고, 카드 010에서 따로 사전 등록해 비교했다(결과: evid@5 0.805로 4개 후보 중 1위, 단 후보 간 차이는 구분되지 않음). 이 카드의 3개 후보 비교는 그대로 두었다
  - 전체 dev 90문항에서 답변 점수의 직접 비교는 없다. 범위 B 질문의 STRUCT 답변은 R800 답변과 문맥이 같아(ADD-RP04 하나 제외) 새로 실행해도 답변 변동만 나온다
