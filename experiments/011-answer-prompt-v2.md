<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 011: 답변 프롬프트 v2 — gemini-3.1-flash-lite의 되묻기·거절·보류 대응 (3.1 모델에 한정)

Status: planned
Date: 2026-10-21

## 1. Hypothesis

- Change (one variable): 답변 프롬프트를 `prompts/answer_v1.md`에서 `prompts/answer_v2.md`로 바꾼다. 모델은 `gemini-3.1-flash-lite`로 고정하고, 검색·청킹(구조 청킹 + 벡터 k=5 + `gemini-embedding-2`), `temperature: 0`, `thinking_level: low`, 채점은 카드 007과 같다(`configs/011-lite31-prompt2.yaml`, `base: 007-lite31.yaml`)
  - v2의 변경: 규칙 5만 다시 썼다. (1) 확인 순서를 정한다: refused → clarify → abstained → answered. (2) 각 상태에서 답변 본문에 들어갈 요소를 명시한다. refused는 거절 이유 + 검색 결과에서 찾은 위험(손실 가능성, 비용·수수료, 담보·증거금 같은 조건) 경고 + 일반 정보, clarify는 답이 달라지는 기준 + 일반 원칙 + 필요한 정보를 묻는 문장(질문으로 끝냄), abstained는 이유 + 확인처 + 질문자가 알려 주면 이어갈 수 있는 정보 요청. (3) "되묻기를 남발하지 않는다": 질문만으로 검색 결과에서 답이 정해지면 answered로 답한다. 나머지 규칙, JSON 출력, 사용자 부분은 v1과 같다
  - 프롬프트는 기대 대응 유형 정의(`src/rag/golden.py`의 `BEHAVIORS`)에서 썼고 dev 질문 문구를 넣지 않았다(질문 문장 조각 8자 이상이 프롬프트에 없음을 확인함). **다만 카드 007 8절에서 3.1-flash-lite가 답변 불가 문항(되묻기·거절 처리)에서 점수를 잃는다는 것을 본 뒤에 썼다.** 그래서 dev 점수는 이 프롬프트가 보지 못한 질문에서 내는 효과의 깨끗한 추정치가 아니다
  - 프롬프트는 이번 실행으로 고정한다. 결과를 보고 다듬은 v3는 새 카드로 사전 등록해야 한다
- Failure it targets: 카드 007 8절 — 3.8-flash − 3.1-flash-lite의 정답 점수 차이 +0.044(두 번의 재실행 평균)가 답변 불가 16문항에 몰려 있다(+0.219, 답변 가능 74문항은 +0.007). 3.1-flash-lite는 되묻기가 기대 대응인 문항에서 되묻지 않고 일반론을 단정했고, 거절·경고 문항에서 필수 위험 항목을 빠뜨렸다
- Expected effect: 3.1-flash-lite의 답변 불가 문항 점수가 오르고 격차가 줄어든다. 비용은 거의 그대로다(시스템 프롬프트가 1,093자 → 1,507자로 늘어 입력 토큰이 문항당 약 +200~300개, 3.1-flash-lite 입력 단가 0.25 USD/1M 토큰으로 문항당 약 +0.00007 USD로 추정). 위험: 되묻기·거절을 강조하면 답변 가능 문항에서도 되묻거나 보류하는 과잉 반응이 생겨 점수가 떨어질 수 있다. 3.8-flash 수준까지 완전히 따라잡을 것으로는 기대하지 않는다

## 2. Measurement

- 비교 기준 (재사용, 재실행 안 함): 같은 모델·검색에서 프롬프트 v1을 쓴 두 실행 `dev_007_lite31`, `dev_007_lite31_r2`. 참고 기준: 3.8-flash(프롬프트 v1) 두 실행 `dev_007_flash38`, `dev_007_flash38_r2`
- 실행: v2를 쓰는 3.1-flash-lite를 dev 90문항 전체에서 **두 번** 실행한다(`dev_011_lite31_prompt2`, `dev_011_lite31_prompt2_r2`). 기준도 두 번이므로 같은 번호 실행끼리 짝지어 비교한다(카드 007 8절의 `scripts/model_rerun_compare.py`)
- Metric: 정답 점수(0/1/2를 2로 나눈 90문항 평균). 함께 보고: 세트별·답변 가능/불가·난이도별 평균 차이, 문항별 변화(오른/내린 문항), status_ok, 완전 정답 수, 문항당 입력·출력·thinking 토큰과 USD(답변), 깨진 출력 건수, 되묻기·보류·거절 status를 고른 문항 수(v1 대비)
- Split: dev. test 분할은 보지 않는다
- Noise: 재실행 잡음은 두 번의 실행에서 측정한다(카드 007 8절: 3.1-flash-lite v1은 0.011, 바뀐 문항 4)

## 3. Go/no-go criteria (written before results)

판정은 `scripts/model_rerun_compare.py --a dev_011_lite31_prompt2 dev_011_lite31_prompt2_r2 --b dev_007_lite31 dev_007_lite31_r2`의 규칙을 그대로 쓴다: 평균 차이 Δ(v2 − v1)가 두 그룹의 재실행 잡음 중 큰 값보다 크고 두 쌍의 차이가 모두 양수여야 "v2가 더 높다".

- **격차를 줄이는가:** 위 규칙으로 "v2가 더 높다"이면 격차가 줄어든 것으로 본다. 줄어든 정도는 Δ를 기존 격차 0.044로 나눈 값으로 적는다
- **해로움 점검 (답변 가능 문항):** 답변 가능 74문항의 평균 차이 Δ가 −(재실행 잡음의 큰 값)보다 작으면 v2가 과잉 반응으로 해롭다고 본다. 이 경우 답변 불가 문항이 올랐더라도 v2를 채택하지 않는다
- **채택(3.1-flash-lite에 한정한 프롬프트 v2):** 격차를 줄이고 해롭지 않을 때. 어느 쪽이든 최종 답변 모델 결정(카드 007: 3.8-flash)은 자동으로 바뀌지 않는다
- **3.8-flash와의 비교:** `--a dev_007_flash38 dev_007_flash38_r2 --b dev_011_lite31_prompt2 dev_011_lite31_prompt2_r2`로 같은 규칙을 적용한다. 판정이 "구분하지 못함" 또는 "3.1이 더 높다"이면 격차가 잡음 안으로 들어온 것으로 적는다. 이 비교는 3.8-flash에 프롬프트 v2를 쓰지 않은 것과의 비교이므로 같은 조건의 비교가 아니다(v2가 3.8-flash에도 도움이 될 수 있다). 3.8-flash + v2는 실행하지 않는다(요청 범위 밖)
- "비용은 그대로"의 점검: 문항당 USD(답변)가 v1 대비 +10% 이내이면 그대로로 본다
- v2가 모든 기준에서 실패하면 그렇게 보고하고 v1을 유지한다. 결과를 보고 프롬프트를 고쳐 다시 실행하지 않는다

## 4. LLM budget

- Planned calls: v2 3.1-flash-lite 두 번 = answers 180 + judge 180. 비용 추정: 답변 약 0.23 USD(카드 007의 3.1-flash-lite 실행 0.115 USD × 2에 입력 증가분 약 0.01 USD), 채점 약 0.25 USD, 합계 약 0.49 USD
- 한 번에 하나씩 순서대로 실행하고 실행 뒤 문항별 기록이 90건인지 확인해 중복 실행이 없음을 확인한다
- Calls so far in the project: submission/PROCESS.md 장부 참고

## 5. LLM-free results

해당 없음(대리 지표가 없다).

## 6. Answer run

_..._

## 7. Decision and notes

- Decision: _adopt / reject / inconclusive_
- Why, with question IDs: _..._
- What the criteria missed, if anything: _..._
