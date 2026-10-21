<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 007: 답변 모델 비교 — gemini-3.1-flash-lite / gemini-3.5-flash-lite / gemini-3.8-flash (구조 청킹 + 벡터 위)

Status: decided — adopt gemini-3.8-flash (근거는 얇음, 7절)
Date: 2026-10-21

## 1. Hypothesis

- Change (one variable): `answer.model`만 바꾼다(PLAN H5). 검색·청킹은 채택된 구성(구조 청킹 + 벡터 k=5 + `gemini-embedding-2`, 카드 002·004·005·006·009·010), 답변 프롬프트(`prompts/answer_v1.md`), `temperature: 0`, `thinking_level: low`, 채점 모델·프롬프트는 그대로다. 변형 2개(`configs/007-lite31.yaml`, `configs/007-flash38.yaml`)
  - `gemini-3.1-flash-lite`: 가장 싼 안정 모델(입력 0.25 / 출력 1.50 USD per 1M 토큰)
  - `gemini-3.8-flash`: 최신 flash(0.75 / 3.75). 2027-01-01부터 2배
  - 기준: `gemini-3.5-flash-lite`(0.30 / 2.50)
  - **모델마다 thinking 양이 다르다**(`thinking_level: low`에서 3.8-flash 0, 3.5-flash-lite 0, 3.1-flash-lite 약 159 토큰; PLAN 4.3절). 품질 차이를 "모델"과 "thinking"으로 나누지 않는다. 둘이 함께 바뀐다
  - **temperature 적용 여부가 다르다:** 3.5-flash-lite는 temperature를 무시하지만 3.1-flash-lite와 3.8-flash는 적용한다. 그래서 후보의 재실행 잡음은 기준(14 / 90)과 같다고 가정할 수 없다. 후보의 재실행 잡음은 측정하지 않는다(아래 4절)
- Failure it targets: PROCESS.md 6절의 답변 쪽 실패(근거는 다 있는데 불완전한 답 7문항, negative 대응 불일치 4문항 등)와, 같은 구성에서 문맥에 근거가 있는데도 오답인 문항. 구조 청킹 이후 정답 점수 0.761, 완전 정답 55 / 90
- Expected effect (PLAN H5): 최저가 모델은 기초 문항에서 flash 등급과 차이가 작고, 고급·negative 문항에서 차이가 난다. 즉 `gemini-3.8-flash`가 advanced 문항과 negative 문항에서 기준보다 높고, `gemini-3.1-flash-lite`는 basic에서 기준과 비슷하며 advanced에서 낮을 것으로 예상한다. 크기는 모른다

## 2. Measurement

- Baseline run (reused, not rerun): `dev_002_structure_all` — 구조 청킹 + 벡터 k=5 + `gemini-3.5-flash-lite`, dev 90문항 전체의 답변과 채점. (이 실행은 카드 010 8.3절에 적은 사고로 일부 문항이 두 번 실행되었고, 문항마다 가장 최근 기록 한 건을 쓴다.) 검색 결과는 후보 실행과 같으므로(검색 구성이 같다) 후보와의 차이는 답변 단계에서만 생긴다
- Metric: 채점 정답 점수(0/1/2, 90문항). 함께 보고: 완전 정답 수, status_ok(기대 대응 일치), 인용이 정답 페이지(`citation_on_target`), 깨진 출력 건수(`scripts/garble_scan.py`), 문항당 토큰·thinking 토큰·USD(답변), p50/p90 응답 시간, 세트별(base_positive / base_negative / life_guide / additional)과 난이도별(basic 19 / intermediate 39 / advanced 29 / adversarial 3) 정답 점수와 짝비교
- 응답 시간은 그 실행 시점에 다른 배치가 돌고 있지 않을 때만 의미가 있다. 두 후보는 한 번에 하나씩 순서대로 실행하고, 다른 배치를 동시에 돌리지 않는다
- Split: dev
- Noise (step 3): 기준 모델의 같은 설정 재실행 (a) 14 / 90, 채점 재채점 (b) 3 / 90. 후보 모델의 재실행 잡음은 측정하지 않았다

## 3. Go/no-go criteria (written before results)

이 카드는 대리 지표가 없는 답변 단계 비교라 게이트 없이 항상 실행한다(PLAN 3.2, 2026-10-20 결정).

- 후보 X가 기준보다 낫다 ⇔ 짝비교에서 X 우세 − 기준 우세 > 0이고 바뀐 문항 수 > 14(잡음). 95% CI는 함께 보고하되 CI만으로 판정하지 않는다. 후보가 기준보다 나쁘다는 것도 같은 규칙으로 판정한다
- 채택 규칙:
  1. 어느 후보도 기준보다 낫지 않으면 기준 `gemini-3.5-flash-lite`를 유지한다. 후보가 더 싸더라도(3.1-flash-lite) 바꾸지 않는다. 비용 상한을 고정하지 않으므로(PROCESS.md 0절) 비용은 보고만 한다
  2. 후보 하나만 낫다면 그 후보를 채택한다
  3. 둘 다 낫다면 두 후보를 직접 짝비교해 같은 규칙을 적용하고, 구분되지 않으면 문항당 비용이 낮은 쪽을 고른다
- 비용은 기준 대비 문항당 USD(답변)를 보고하고, 채택하면 "정답 1점당 비용"도 적는다. `gemini-3.8-flash`의 단가는 2027-01-01에 2배가 된다는 점을 함께 적는다
- 깨진 출력은 점수 비교에서 빼지 않고 건수만 보고한다(PROCESS.md 6절 결정)
- 난이도·세트별 결과는 H5 확인용 보고이고 채택 판정에 쓰지 않는다

## 4. LLM budget

- Planned calls: `gemini-3.1-flash-lite` answers 90 + judge 90, `gemini-3.8-flash` answers 90 + judge 90 = answers 180 + judge 180. 비용 추정: 3.1-flash-lite 답변 약 0.08 USD, 3.8-flash 답변 약 0.2 USD(문항당 입력 약 2,400 토큰 가정), 채점 후보당 약 0.12 USD, 합계 약 0.5 USD
- 한 번에 하나씩 순서대로 실행하고 실행 뒤 `runs.db`의 문항별 기록 수가 90인지 확인해 중복 실행이 없음을 확인한다(카드 010 8.3절 사고의 재발 방지)
- Calls so far in the project: submission/PROCESS.md 장부 참고

## 5. LLM-free results

해당 없음(대리 지표가 없다).

## 6. Answer run

실험 이름 `dev_007_lite31`, `dev_007_flash38`(결과 `results/<실험>/`, runs.jsonl 포함). 기준은 `dev_002_structure_all`. 세 실행 모두 입력 토큰 합계가 201,974로 같아 같은 문맥을 받았다. 문항별 기록은 각 90건, 중복·오류 없음. 깨진 출력 0/90 (`garble_scan.py`; 아래 참고).

| Model | 정답 점수 | 완전 정답 | status_ok | 인용이 정답 페이지 | 문항당 토큰 (thinking) | 문항당 USD (답변) | p50 / p90 s |
|---|---|---|---|---|---|---|---|
| gemini-3.5-flash-lite (기준) | 0.761 | 55 | 82 | 0.919 | 2,378 (0) | 0.00100 | 1.75 / 4.45 (※) |
| gemini-3.1-flash-lite | 0.800 | 61 | 85 | 0.932 | 2,723 (약 308) | 0.00128 (1.28배) | 2.34 / 4.91 |
| **gemini-3.8-flash** | **0.828** | **64** | 83 | **0.959** | 2,422 (0) | **0.00231 (2.31배)** | 4.53 / 5.99 |

※ 기준의 p90 4.45초는 카드 010 8.3절의 사고(두 배치 동시 실행) 때 값이라 후보와 비교할 수 없다. 같은 모델이 혼자 돌았을 때(`dev_000_baseline`, Recursive 청킹)는 p50 1.58 / p90 2.07초였다. 두 후보는 단독 순차 실행이다.

- 정답 1점(완전 정답 1개)당 답변 비용: 기준 0.00164 USD, 3.1-flash-lite 0.00188, 3.8-flash 0.00325. 채점은 모델과 무관하게 90문항당 약 0.124~0.128 USD

짝비교 (정답 점수 0~2를 2로 나눈 값, 잡음 14):

| 비교 | 차이 (95% CI) | 우세 / 열세 / 같음 | 순증 | 바뀐 | 사전 규칙(순증 > 0, 바뀐 > 14) |
|---|---|---|---|---|---|
| 3.1-flash-lite − 기준 | +0.039 [−0.006, +0.089] | 11 / 4 / 75 | +7 | 15 | 충족 (기준 초과가 1문항) |
| 3.8-flash − 기준 | +0.067 [+0.022, +0.117] | 13 / 3 / 74 | +10 | 16 | 충족 |
| 3.8-flash − 3.1-flash-lite | +0.028 [−0.022, +0.078] | 9 / 6 / 75 | +3 | 15 | 충족 (기준 초과가 1문항) |

- 3.1-flash-lite 우세: ADD-HF07 ADD-HF10 ADD-HP06 ADD-HP10 ADD-IN01 ADD-RP05 ADD-RP06 NEG022 POS018 POS058 POS061, 열세: NEG009 NEG011 POS044 POS045
- 3.8-flash 우세: ADD-HF07 ADD-HF10 ADD-HP10 ADD-IN01 ADD-RP06 NEG014 NEG023 NEG025 NEG037 POS018 POS057 POS058 POS059, 열세: POS022 POS044 POS051
- 3.8-flash − 3.1-flash-lite 우세: NEG009 NEG011 NEG014 NEG023 NEG025 NEG037 POS045 POS057 POS059, 열세: ADD-HP06 ADD-RP05 NEG022 POS022 POS051 POS061

세트별·난이도별 정답 점수 (H5 확인용 보고, 판정에는 쓰지 않음):

| 구분 (n) | 3.5-flash-lite | 3.1-flash-lite | 3.8-flash |
|---|---|---|---|
| base_positive (30) | 0.850 | 0.850 | 0.867 |
| base_negative (20) | 0.800 | 0.750 | **0.925** |
| life_guide (10) | 0.750 | 0.800 | 0.750 |
| additional (30) | 0.650 | **0.783** | 0.750 |
| basic (19) | 0.842 | **0.947** | 0.921 |
| intermediate (39) | 0.821 | 0.808 | **0.872** |
| advanced (29) | 0.603 | 0.672 | **0.690** |
| 답변 가능 (74) | 0.764 | **0.824** | 0.811 |
| 답변 불가 (16) | 0.750 | 0.688 | **0.906** |

- 기준 대비 우세 / 열세, 답변 불가 16문항: 3.8-flash 4 / 0, 3.1-flash-lite 1 / 2. advanced 29문항: 3.8-flash 7 / 2, 3.1-flash-lite 6 / 2. basic 19문항: 3.8-flash 2 / 0, 3.1-flash-lite 3 / 0
- **깨진 출력 점검의 오탐:** `garble_scan.py`가 처음에 3.1-flash-lite를 29/90건 깨짐으로 표시했다. 출력 토큰에 thinking 토큰이 포함되는데 3.1-flash-lite는 문항당 약 308 thinking 토큰을 쓰기 때문이다. 가나 글자는 세 모델 모두 0건이고, thinking 토큰을 뺀 출력 토큰/글자 비율은 중앙값 0.54로 정상이었다. 스크립트가 thinking 토큰을 빼도록 고쳤다. 고친 뒤 결과: 3.1-flash-lite 0/90, 3.8-flash 0/90, 기준 0/90, `dev_000_baseline` 1/90(POS054, 이전과 같음)

## 7. Decision and notes

- Decision: **`gemini-3.8-flash`를 최종 답변 모델로 채택한다.** 사전 규칙 3번: 3.1-flash-lite와 3.8-flash가 모두 기준보다 낫고, 직접 비교에서 3.8-flash가 규칙을 충족한다
- Why, with question IDs:
  - 기준 대비 3.8-flash는 세 비교 중 증거가 가장 강하다: 순증 +10, 95% CI [+0.022, +0.117]가 0을 벗어난다. 완전 정답 55 → 64
  - H5의 일부가 확인되었다. 3.8-flash는 답변 불가(negative) 문항에서 크게 올랐다(0.750 → 0.906, NEG014 NEG023 NEG025 NEG037이 우세, 열세 없음)이고 advanced도 0.603 → 0.690이다. 3.1-flash-lite는 basic에서 기준 이상이고(0.947) 3.8-flash와 차이가 작았지만(0.921), negative에서는 0.688로 낮았다
  - 3.1-flash-lite도 기준보다 나았다(순증 +7, 완전 정답 61). 특히 additional에서 0.650 → 0.783으로 올라 3.8-flash(0.750)보다 높다. 그러나 답변 불가 문항에서는 오히려 내렸다(0.750 → 0.688)
- **근거가 얇은 이유 (결론의 한계):**
  - 3.8-flash − 3.1-flash-lite는 순증 +3, 95% CI [−0.022, +0.078]로 구분되지 않는다. 사전 규칙은 "바뀐 문항 > 14"인데 15라서 기준을 1문항 넘겼을 뿐이다. 서로 다른 두 모델이 90문항에서 14문항 넘게 달라지는 것은 거의 항상 일어나서 이 조건은 구분력이 거의 없다
  - 3.1-flash-lite − 기준도 바뀐 문항 15로 기준을 1문항 넘었을 뿐, CI가 0을 포함한다
  - 각 모델을 한 번씩만 실행했다. 3.5-flash-lite의 같은 설정 재실행은 순증 −8까지 흔들렸다(PROCESS.md 4절). 3.1-flash-lite와 3.8-flash는 temperature가 적용되어 잡음이 다를 수 있으나 측정하지 않았다
  - 채점 모델 `gemini-3.6-flash`는 flash 계열이다. 같은 계열의 `gemini-3.8-flash` 답변을 더 후하게 채점했을 가능성을 배제하지 못했다(추측, 측정하지 않음). 8단계에서 사람이 채점 10건을 검수하는 계획(PLAN 4.3절)이 이 위험을 일부 확인한다
- **비용과 시간:** 3.8-flash는 기준의 2.31배 비용(문항당 답변 0.00231 USD), 응답 p50 4.53초로 기준의 2배 이상이다(기준 단독 실행 p50 1.58초). 정답 1점당 비용은 기준의 약 2배다. 단가가 2027-01-01에 2배가 되므로 그 뒤에 실행하면 `configs/pricing.yaml` 확인일을 갱신해야 한다. 비용 상한을 고정하지 않았으므로(PROCESS.md 0절) 사전 규칙대로 채택했다. 비용을 우선한다면 3.1-flash-lite가 기준보다 나으면서 3.8-flash의 약 55% 비용(0.00128 대 0.00231 USD)이다
- What the criteria missed, if anything:
  - 위 구분력 문제. 후보 간 차이를 가르려면 "바뀐 문항 > 14"가 아니라 순증과 CI를 함께 봐야 했다. 이 카드의 판정은 규칙대로 했으나 3.8-flash − 3.1-flash-lite는 사실상 구분하지 못한 것이다
  - thinking 양이 모델마다 달라(3.1-flash-lite 약 308 토큰, 나머지 0) 품질 차이를 모델과 thinking으로 나눌 수 없다(1절에서 미리 밝힘)
- 다음 설정 체인: 구조 청킹 + 벡터 k=5 + `gemini-embedding-2` + `gemini-3.8-flash` = `configs/007-flash38.yaml`. 이것이 T2(개선된 RAG)의 후보 구성이다. PROCESS.md 9절의 최종 test 표는 Agent(008)와 자작 골든셋이 정해진 뒤 채운다
