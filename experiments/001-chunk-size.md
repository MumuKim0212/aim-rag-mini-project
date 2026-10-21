<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 001: 청크 크기 탐색 (300–1200)

Status: rejected (게이트 불통과, 답변 실행 없음)
Date: 2026-10-21

## 1. Hypothesis

- Change (one variable): Recursive 청킹의 `chunk_size`만 바꾼다. 후보는 300 / 400 / 600 / 800(기준) / 1000 / 1200자이고, 결과를 보기 전에 이 목록을 고정한다. 겹침 비율은 기준과 같은 약 12.5%로 둔다(300/40, 400/50, 600/75, 1000/125, 1200/150). 청킹 방식, 임베딩, k=5, 답변 프롬프트·모델은 기준과 같다. 설정: `configs/001-chunk<size>.yaml`. `rag_chunking_lab_simple.py`의 `CHUNK_SETTINGS` 탐색을 팀 공통 도구(골든셋 dev, evid@5)로 옮긴 것이다
- 겹침 크기는 이 카드에서 바꾸지 않는다. 필요하면 채택한 크기에서 별도 카드로 비교한다(한 번에 한 요소)
- Failure it targets (PROCESS.md 6절, `dev_000_baseline`):
  - 검색 실패 중 용어집 정의 4문항 POS001, POS006, POS013, POS021 — 800자 청크 하나에 용어 약 8개가 섞여 정의 하나의 임베딩이 묻힌다(1.3절). **400이 유리할 것으로 본다**
  - 근거 일부 누락 13문항(ADD-HF06, ADD-HF07, ADD-HP09, ADD-IN10, ADD-PF01, ADD-RP05, ADD-RP06, ADD-SE06, ADD-SE08, POS047, POS050, POS061, POS078)과 과잉 보류 5문항(ADD-PF08, ADD-PF09, POS045, POS057, POS058, 모두 evid < 1) — 근거 구절이 청크 경계에서 잘리거나 옆 청크에 있다. **1200이 유리할 것으로 본다**
- Expected effect: 400은 용어집 문항(base_positive)의 page_hit·evid@5를 올리고 additional의 evid@5를 낮출 수 있다. 1200은 evid@5를 전반적으로 올리지만 문맥 길이가 약 1.5배가 된다. 어느 쪽도 위 두 실패군을 동시에 줄이지는 못할 것으로 예상한다(그 경우 002 구조 단위 청킹이 답이 될 수 있다)

## 2. Measurement

- Baseline run (reused, not rerun): `dev_000_baseline` (`results/dev_000_baseline/metrics.jsonl`, grades.jsonl)
- Proxy metric (step 4): **evid@5** — 정답 점수와 Pearson r 0.50–0.61, 세 채점에서 가장 안정적(PROCESS.md 5절). 정답 페이지가 있는 dev 74문항에서 계산
- 함께 보고: 문맥 글자 수 `chars`(큰 청크일수록 evid@5가 쉽게 오르므로, 5절 주의), page_hit@5, MRR, 세트별(base_positive / additional / life_guide) evid@5, 위 1절 대상 문항별 변화
- 진단용(결정에 쓰지 않음): 문맥 길이를 비슷하게 맞춘 비교 — 작은 청크(300·400)는 evid@10, 큰 청크(1000·1200)는 evid@3을 기준 evid@5와 비교. "청크가 커서 좋아졌나, 경계가 좋아서 좋아졌나"를 가르기 위한 것이다. k 자체를 바꾸는 결정은 카드 005에서 한다
- Split: dev
- Noise (step 3): (a) 14 / 90, (b) 3 / 90

## 3. Go/no-go criteria (written before results)

변형 5개(300, 400, 600, 1000, 1200) 각각을 기준(800)과 비교한 뒤, 아래 규칙으로 하나를 고른다.

- Cost cap: 평균 문맥 글자 수 ≤ 기준의 1.5배(≤ 4,596자). 넘는 변형은 후보에서 빼고 비용 대비 결과로만 보고한다
- 선택 규칙("가장 좋은 수치"): cost cap 안의 변형 중 evid@5 순증(오른 문항 수 − 내린 문항 수, dev 74문항)이 가장 큰 것. 순증 차이가 3문항 이내면 문맥이 짧은 쪽을 고른다
- LLM-free gate: 고른 변형의 evid@5 순증 > 14 (잡음 (a))
- Headroom gate: 고른 변형에서 `evalkit/headroom.py --metric evid@5 --noise 14`의 upside − risk > 14
- 여러 후보 중 최고를 고르면 우연히 좋게 나온 값을 고를 수 있다(선택 편향). 그래서 답변 실행은 고른 1개만 하고, 채택은 그 답변 실행으로 판단한다
- Adopt if (answer run): 짝비교에서 변형 우세 − 기준 우세 > 0이고 바뀐 문항 수 > 14, 95% CI가 0을 포함하지 않음. 잡음 측정(4절)에서 같은 설정끼리도 CI가 0을 벗어났으므로 CI만으로는 채택하지 않는다
- 게이트를 통과하지 못하면 답변 실행 없이 기준 800/100을 유지하고, LLM 없는 지표로 비교 결과를 보고한다(PLAN 3.2, 2026-10-20 결정)

## 4. LLM budget

- LLM-free 단계: 답변·채점 호출 0. 임베딩만 — 변형마다 인덱스 1회(범위 A·B, 기준 인덱스 약 0.14 USD, 5변형 약 0.7 USD) + 질의 90개
- Planned calls if the gates pass: 고른 1변형만 answers 90 + judge 90
- Calls so far in the project: submission/PROCESS.md 장부 참고


## 5. LLM-free results

dev, `--retrieval-only`, 정답 페이지가 있는 74문항(evid@5 계산 가능). 실험 이름 `dev_001_chunk<size>_retrieval`, 결과 `results/<실험>/`. 순증은 evid@5가 오른 문항 수 − 내린 문항 수.

| Config | evid@5 (dev 74) | Net vs baseline (+/−) | page_hit@5 | gold@5 | Context chars (평균) / 문맥 상한 4,596 |
|---|---|---|---|---|---|
| baseline 800/100 | 0.697 | – | 0.878 | 1.92 | 3,064 |
| 300/40 | 0.671 | −15 (10 / 25) | 0.932 | 2.55 | 1,277 |
| 400/50 | 0.675 | −10 (9 / 19) | 0.905 | 2.49 | 1,670 |
| 600/75 | 0.705 | −6 (11 / 17) | 0.946 | 2.14 | 2,373 |
| **1000/125** | **0.764** | **+10 (17 / 7)** | 0.932 | 2.00 | 3,705 |
| 1200/150 | 0.748 | +10 (18 / 8) | 0.905 | 1.80 | 4,166 |

- 선택 규칙 적용: 문맥 상한 안에 5개 모두 들어간다(1200이 4,166자로 가장 길다). 순증이 가장 큰 것은 1000과 1200(둘 다 +10)이고 차이가 3문항 이내라서 문맥이 짧은 **1000**을 골랐다
- LLM-free gate: 1000의 순증 +10은 잡음 14보다 크지 않다 → **불통과**. 평균 차이는 +0.066, 95% CI [+0.024, +0.118]이지만 4절의 잡음 측정에서 같은 설정끼리도 CI가 0을 벗어났으므로 CI로 판단하지 않는다는 기준을 그대로 따랐다
- Headroom (`evalkit/headroom.py --metric evid@5 --noise 14`, 기준 `grades.jsonl`):
  - 1000: upside 11 (ADD-HP09 ADD-IN10 ADD-PF08 ADD-RP05 POS001 POS021 POS047 POS050 POS057 POS058 POS061), 이미 정답인데 오른 문항 6, risk 6 (ADD-HF07 ADD-IN08 ADD-PF01 ADD-SE08 POS045 POS074). upside − risk = 5 < 14
  - 참고로 1200: upside 12, risk 7, upside − risk = 5. 같은 결론이다
- Gates passed? **no** — 6절은 비워 두고 7절에서 결정한다

**세트별 evid@5** (n은 evid 계산 가능 문항)

| 세트 (n) | 800 | 300 | 400 | 600 | 1000 | 1200 |
|---|---|---|---|---|---|---|
| base_positive (30) | 0.717 | 0.728 | 0.683 | 0.766 | 0.836 | 0.823 |
| additional (30) | 0.612 | 0.546 | 0.604 | 0.600 | 0.641 | 0.666 |
| life_guide (10) | 0.773 | 0.745 | 0.785 | 0.724 | 0.820 | 0.766 |
| base_negative (4) | 1.000 | 1.000 | 0.875 | 1.000 | 1.000 | 0.750 |

**1절 대상 문항의 변화** (PROCESS.md 6절 분류, 평균 evid@5 / 근거가 모두 들어온 문항 수)

| 실패군 | 800 | 300 | 400 | 600 | 1000 | 1200 |
|---|---|---|---|---|---|---|
| 용어집 정의 4 (POS001·006·013·021) 페이지 적중 | 0/4 | 0/4 | 0/4 | 2/4 | 2/4 | 2/4 |
| 검색 실패 7: 평균 evid@5 | 0.004 | 0.287 | 0.186 | 0.432 | 0.289 | 0.326 |
| 근거 일부 누락 13: 평균 evid@5 (근거 완전 포함) | 0.593 (0) | 0.523 (0) | 0.503 (0) | 0.490 (0) | 0.685 (3) | 0.652 (4) |
| 과잉 보류 5: 평균 evid@5 (근거 완전 포함) | 0.474 (0) | 0.329 (0) | 0.419 (0) | 0.385 (0) | 0.621 (1) | 0.668 (1) |

- 진단(evid@3 대 기준 evid@5, 큰 청크): 1000 0.685, 1200 0.692, 기준 0.697. 문맥을 3개로 줄이면(길이는 약 3/5, 이것은 비율로 어림한 값이고 문항별로 재지 않았다) 기준 evid@5와 거의 같다. 큰 청크의 이득 중 상당 부분이 문맥이 길어진 효과일 수 있다. 다만 문맥 길이를 맞춘 비교는 아니라서 결론은 아니다
- 진단(evid@10, 작은 청크): 하지 않았다. 저장된 검색이 k=5까지라 evid@10이 evid@5와 같은 값이다. k=10 재검색이 필요한데 진단용이고 게이트가 이미 불통과여서 생략했다

## 6. Answer run (only if the gates passed)

게이트 불통과로 실행하지 않았다.

## 7. Decision and notes

- Decision: **reject** — 기준 800/100을 유지한다. 답변 실행 없음(답변·채점 LLM 호출 0)
- Why, with question IDs:
  - 고른 1000의 evid@5 순증 +10, upside − risk 5로 둘 다 잡음 14보다 작다. 1200도 같다. 5개 변형 중 선택된 하나를 답변 실행하면 잡음 안의 차이를 읽게 된다
  - 1절의 두 예측은 절반만 맞았다. (1) "400이 용어집 정의 4문항에 유리"는 틀렸다: 300·400은 4문항 모두 놓쳤고(0/4), 600 이상에서 POS001·POS021만 잡혔다. POS006·POS013은 어떤 크기에서도 정답 페이지를 놓쳤다. 작은 청크는 page_hit@5를 올렸지만(300 0.932, 400 0.905, 기준 0.878) 근거 구절 포함률(evid@5)은 오히려 내려갔다. (2) "1200이 근거 일부 누락 13문항과 과잉 보류 5문항에 유리"는 방향은 맞았다: 근거가 모두 들어온 문항이 0 → 3(1000)·4(1200)가 됐다. 그러나 13문항 중 대부분은 여전히 근거가 일부 빠져 있고 크기만으로는 줄지 않았다
  - 크기를 바꾸면 얻는 문항(1000: ADD-HP09 ADD-IN10 POS001 POS021 등 17)과 잃는 문항(ADD-HF07 ADD-IN08 ADD-PF01 ADD-SE08 POS045 POS074 등 7)이 같이 생겨 합이 작다
- What the criteria missed, if anything:
  - 평균 차이의 CI가 0을 벗어난 1000(+0.066, [+0.024, +0.118])을 순증 기준이 막았다. 4절 결과로 CI를 믿지 않기로 한 기준이 맞았는지는 알 수 없다. 어느 쪽이든 문항 수 기준은 일관되게 적용했다
  - 5개를 비교했으므로 가장 좋은 값을 고르는 편향이 있고, 그래서 1000의 +10도 과대일 수 있다(추측)
  - 문맥 길이를 맞춘 진단(evid@10)은 저장된 검색이 k=5라 하지 못했다
- 다음: 002 구조 단위 청킹(용어집 정의 POS006·POS013처럼 크기로 안 잡히는 문항), 005 검색량(k)에서 문맥 길이와 근거 포함의 관계를 본다
