<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 007: 답변 모델 비교 — gemini-3.1-flash-lite / gemini-3.5-flash-lite / gemini-3.8-flash (구조 청킹 + 벡터 위)

Status: planned
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

| Model | 정답 점수 | 완전 정답 | status_ok | 문항당 토큰 | 문항당 USD (답변) | p50 / p90 s |
|---|---|---|---|---|---|---|
| gemini-3.5-flash-lite (기준) | | | | | | |
| gemini-3.1-flash-lite | | | | | | |
| gemini-3.8-flash | | | | | | |

- Experiment names: _..._
- Paired vs baseline: _B better N / A better N / same N, diff ±0.000, 95% CI [_, _]_
- Garble scan: _..._
- LLM calls used: _answers __ + judge ___

## 7. Decision and notes

- Decision: _adopt / reject / inconclusive_
- Why, with question IDs: _..._
- What the criteria missed, if anything: _..._
