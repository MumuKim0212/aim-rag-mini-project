<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 005: 검색량 k와 MMR (구조 청킹 + 벡터 검색 위)

Status: rejected (게이트 불통과, 답변 실행 없음)
Date: 2026-10-21

## 1. Hypothesis

- Change (one variable per variant): 기준은 구조 청킹 + 벡터 검색 k=5(카드 002 채택, 카드 004는 기각이라 검색 방식은 벡터 그대로)이고, 변형 3개는 각각 한 가지만 바꾼다
  - `configs/005-k3.yaml`: `retrieval.k: 3`
  - `configs/005-k8.yaml`: `retrieval.k: 8`
  - `configs/005-mmr.yaml`: `retrieval.mmr: true` — k=5는 그대로, 가장 가까운 20개(`max(4k, 20)`) 중에서 `0.5 × 질의와의 유사도 − 0.5 × 이미 고른 청크와의 최대 유사도`가 큰 순서로 5개를 고른다(`mmr_lambda` 0.5, 결과를 보기 전에 고정하고 조정하지 않는다)
- Failure it targets: PROCESS.md 6절 병목 "근거 부족" — 기준(구조 청킹)에서 근거가 일부만 들어온 문항은 74문항 중 33개다. k를 늘리면 더 많은 근거가 들어올 수 있고, MMR은 같은 내용의 청크가 상위를 채우는 것을 줄여 다른 근거가 들어오게 한다
- Expected effect: k=8은 evid가 오르지만 문맥이 약 1.6배가 된다(k=5의 평균 2,331자 × 8/5). k=3은 evid가 내리고 문맥은 약 0.6배다. MMR은 문맥 길이가 비슷하고 evid가 약간 오를 수 있으나 크게는 기대하지 않는다. 문맥이 길어지면 답변이 흐려질 수도 있어 evid가 오르는 것이 답 개선을 뜻하지는 않는다

## 2. Measurement

- Baseline run (reused, not rerun): `dev_002_structure_all_retrieval` (구조 청킹, 벡터, k=5, dev 90문항)
- Proxy metric: k가 달라지므로 `evid@5`(상위 5개 안의 근거 구절 포함률)는 쓰지 않고, 답변 단계에 실제로 넘어간 문맥의 근거 포함률 **`evid`**를 쓴다(PROCESS.md 5절: k=5에서는 `evid@5`와 같다). 정답 페이지가 있는 dev 74문항. 함께 보고: page_hit(문맥에 정답 페이지가 있는 비율), gold@k, 문맥 글자 수 `chars`, 문맥의 서로 다른 페이지 수(`scripts/context_diversity.py`), 세트별 evid
- 문맥 길이가 늘어나면 evid가 쉽게 오르므로 `chars`를 함께 보고, 아래 비용 상한으로 막는다
- Split: dev
- Noise (step 3): (a) 14 / 90, (b) 3 / 90 — 모든 dev 질문의 검색이 바뀔 수 있어 전체 기준을 쓴다

## 3. Go/no-go criteria (written before results)

- Cost cap: 평균 문맥 글자 수 ≤ 기준의 1.5배(2,331자 → 3,496자). 넘는 변형은 후보에서 빼고 결과만 보고한다. k=8은 위 예상대로라면 1.6배 안팎이라 이 상한에 걸릴 수 있다. 상한은 다른 카드와 같은 값(카드 001과 004)이고, 이 변형만 달리 정하지 않는다
- 선택 규칙: 상한 안의 변형 중 evid 순증(오른 문항 − 내린 문항, 74문항)이 가장 큰 것. 차이가 3문항 이내이면 문맥이 짧은 쪽
- **k=3은 채택 후보가 아니다.** 비용을 줄이는 변형이지만 프로젝트는 비용 상한을 고정하지 않고 품질과 비용을 함께 기록한다(PROCESS.md 0절). k=3은 evid와 비용의 관계를 보여 주려고 실행하며, 위 게이트를 통과해야만 후보가 된다(근거를 줄이는 변경이라 통과하지 못할 것으로 본다)
- LLM-free gate: 고른 변형의 evid 순증 > 14
- Headroom gate: `evalkit/headroom.py --metric evid --noise 14`로 upside − risk > 14. 기준 점수는 카드 004와 같이 `scripts/merge_grades.py`로 합친 채점(범위 A는 `dev_002_structure`, 범위 B는 `dev_000_baseline`)을 쓴다
- 선택 편향: 변형이 셋이라 고른 하나만 답변 실행한다
- Adopt if (answer run): 구조 청킹 위 기준 답변 실행 `dev_002_structure_all`(90문항)과 고른 변형을 짝비교해 변형 우세 − 기준 우세 > 0이고 바뀐 문항 수 > 14. 95% CI는 함께 보고하되 CI만으로 채택하지 않는다. 문맥 길이와 문항당 토큰·비용을 함께 보고한다
- 게이트를 통과하지 못하면 답변 실행 없이 k=5, MMR 없음을 유지하고 LLM 없는 지표로 비교 결과를 보고한다

## 4. LLM budget

- LLM-free 단계: 답변·채점 호출 0. 인덱스는 구조 청킹 인덱스를 재사용하고 질의 임베딩 90개 × 3변형만 든다
- Planned calls if the gates pass: 구조 청킹 기준 답변 실행 `dev_002_structure_all` answers 90 + judge 90(이 실행은 카드 004에서도 필요했으나 004는 게이트 불통과로 실행하지 않았다) + 고른 변형 answers 90 + judge 90 = answers 180 + judge 180
- Calls so far in the project: submission/PROCESS.md 장부 참고

## 5. LLM-free results

dev 90문항 전체(evid 계산 74문항), `--retrieval-only`, 인덱스 재사용. 실험 이름 `dev_005_{k3,k8,mmr}_retrieval`. 지표는 `evid`(문맥의 근거 구절 포함률). 순증은 evid가 오른 문항 − 내린 문항.

| Config | evid (dev 74) | Net vs baseline (+/−) | Context chars (문맥이 있는 74문항 평균) | 서로 다른 페이지 수 / 문서 수 |
|---|---|---|---|---|
| baseline k=5 | 0.789 | – | 2,331 | 3.77 / 1.78 |
| k=3 | 0.718 | −16 (0 / 16), diff −0.071, 95% CI [−0.109, −0.036] | 1,413 (0.61배) | 2.44 / 1.40 |
| k=8 | 0.862 | **+16** (16 / 0), diff +0.073, 95% CI [+0.039, +0.113] | **3,733 (1.60배, 상한 3,496자 초과)** | 5.62 / 2.31 |
| mmr (k=5, λ0.5) | 0.665 | −22 (5 / 27), diff −0.124, 95% CI [−0.189, −0.059] | 2,085 (0.89배) | 4.69 / 2.62 |

세트별 evid (기준 → 변형):

| 세트 (n) | k=3 | k=8 | mmr |
|---|---|---|---|
| base_positive (30) | 0.943 → 0.911 | 0.943 → 0.980 | 0.943 → 0.907 |
| life_guide (10) | 0.773 → 0.658 | 0.773 → 0.908 | 0.773 → 0.451 |
| additional (30) | 0.612 → 0.508 | 0.612 → 0.711 | 0.612 → 0.449 |

- 선택 규칙 적용: k=8은 문맥이 상한을 넘어(1.60배) 후보에서 빠졌다. 남은 mmr(−22)과 k=3(−16, 애초에 채택 후보가 아님)은 순증이 음수다. 선택된 변형이 없다
- k=8만 놓고 보면: LLM-free 순증 +16은 잡음 14를 넘는다. 그러나 **headroom**(`evalkit/headroom.py --metric evid --noise 14`, 기준 점수는 `scripts/merge_grades.py`로 합친 채점)은 upside 8 (ADD-HF10 ADD-IN10 ADD-PF01 ADD-PF09 ADD-SE06 ADD-SE08 POS047 POS061), 이미 정답인데 오른 문항 8, risk 0 → upside − risk = **8** ≤ 14라 상한과 관계없이 통과하지 못한다. 오른 16문항 중 8문항은 기준에서 이미 완전 정답이었다
- mmr: upside 5 (ADD-HF10 ADD-IN10 ADD-PF09 ADD-SE04 POS047), risk 26 → −21
- k=3: upside 0, risk 15 → −15
- Gates passed? **no** (선택된 변형 없음. k=8도 cost cap과 headroom을 모두 통과하지 못한다)

## 6. Answer run (only if the gates passed)

게이트 불통과로 실행하지 않았다. LLM 호출 0.

## 7. Decision and notes

- Decision: **reject** — k=5, MMR 없음을 유지한다. 답변 실행 없음
- Why, with question IDs:
  - k를 늘리면 근거가 더 들어온다(k=8에서 evid 0.789 → 0.862, 내린 문항 0). 그러나 문맥이 1.6배로 늘어 비용 상한을 넘고, 오른 16문항 중 8문항은 이미 정답이어서 점수를 올릴 여지가 8문항뿐이다. k를 줄이면(k=3) 16문항이 내려가고 오른 문항은 없다. 근거 포함률은 k에 단조롭게 움직이고 문맥 길이와 맞바꾸는 관계다
  - MMR은 evid를 가장 크게 낮췄다(−22). 서로 다른 페이지 수는 3.77 → 4.69로 늘어 의도대로 다양해졌지만, 근거가 들어 있는 비슷한 청크를 버리면서 근거 포함률이 떨어졌다. 특히 life_guide 0.773 → 0.451(문항 10개)이다. 이 데이터에서 근거는 한 페이지 안에 모여 있는 경우가 많아 중복 제거가 불리한 것으로 보인다(추측)
  - 정답 페이지가 문맥에 있는 비율(page_hit)은 k=3에서 additional이 0.900 → 0.833으로 내렸고, mmr에서는 life_guide가 1.000 → 0.900으로 내렸다
- What the criteria missed, if anything:
  - 문맥이 길어지면 evid가 오르지만 답변이 좋아지는지는 답변 실행 없이는 모른다. k=8 답변 실행은 헤드룸 게이트가 막았다
  - MMR의 λ(0.5)와 후보 수(20)는 조정하지 않았다. λ가 더 크면 결과가 다를 수 있다(모른다)
  - k=4, 6, 7처럼 중간 값은 보지 않았다. 상한(3,496자)에 맞는 k가 있을 수 있으나(k=7이면 약 3,260자로 추정) 사전 등록한 후보가 아니라서 하지 않았다
- 다음: 006 임베딩 모델(`gemini-embedding-001`). 기준은 구조 청킹 + 벡터 k=5다
