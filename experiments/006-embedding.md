<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 006: 임베딩 모델 — gemini-embedding-2 대 gemini-embedding-001 (구조 청킹 + 벡터 검색 위)

Status: rejected (게이트 불통과, 답변 실행 없음)
Date: 2026-10-21

## 1. Hypothesis

- Change (one variable): 임베딩 모델을 `gemini-embedding-2`(기준)에서 `gemini-embedding-001`로 바꾼다(`configs/006-embedding001.yaml`). 모델마다 문서화된 사용 방식이 다르므로 모델과 그 사용 방식을 한 묶음으로 바꾼다:
  - 기준 `gemini-embedding-2`: 질의에 `task: question answering | query: …`, 문서에 `title: <문서명> | text: …` 접두어를 붙인다(`text_format: gemini2_qa`). 이 모델에는 `task_type`이 없다
  - 변형 `gemini-embedding-001`: 접두어 없이 원문을 임베딩하고 `task_type: retrieval`(질의는 `RETRIEVAL_QUERY`, 문서는 `RETRIEVAL_DOCUMENT`)을 쓴다. 차원은 3072로 같다
  - 청킹(구조), 검색(벡터, k=5, MMR 없음), 답변 프롬프트·모델은 그대로다. 접두어 유무(문서명이 임베딩에 들어가는지)는 모델과 분리하지 않는다. 분리하려면 카드를 따로 만들어야 한다
- Failure it targets: PROCESS.md 6절 병목 "근거 부족" — 기준에서 근거가 일부만 들어온 문항은 74문항 중 33개(additional 21, life_guide 6, base_positive 6)다. 임베딩이 질문과 근거를 더 잘 연결하면 줄어들 수 있다
- Expected effect: 모름. `gemini-embedding-2`가 더 새 모델이라 기준이 같거나 낫다고 예상하지만 근거는 없다. `gemini-embedding-001`은 접두어 없이 문서명이 임베딩에 들어가지 않아, 같은 이름의 약관 조항이 여러 문서에 있는 base_positive에서 불리할 수 있다(추측)

## 2. Measurement

- Baseline run (reused, not rerun): `dev_002_structure_all_retrieval`(구조 청킹, 벡터 k=5, `gemini-embedding-2`, dev 90문항)
- Proxy metric (step 4): **evid@5**, 정답 페이지가 있는 dev 74문항. 함께 보고: page_hit@5, MRR, gold@5, 문맥 글자 수, 세트별 evid@5와 순증, 인덱스 구축 비용과 토큰
- Split: dev
- Noise (step 3): (a) 14 / 90, (b) 3 / 90 — 모든 dev 질문의 검색이 바뀔 수 있어 전체 기준을 쓴다

## 3. Go/no-go criteria (written before results)

- Cost cap: 평균 문맥 글자 수 ≤ 기준의 1.5배(2,331자 → 3,496자). 인덱스 구축 비용은 일회성이라 상한이 아니라 보고 항목이다. 변형이 하나뿐이라 선택 규칙과 선택 편향은 없다
- LLM-free gate: evid@5 순증(오른 문항 − 내린 문항, 74문항) > 14
- Headroom gate: `evalkit/headroom.py --metric evid@5 --noise 14`로 upside − risk > 14. 기준 점수는 카드 004·005와 같이 `scripts/merge_grades.py`로 합친 채점(범위 A는 `dev_002_structure`, 범위 B는 `dev_000_baseline`)을 쓴다
- Adopt if (answer run): 구조 청킹 위 기준 답변 실행 `dev_002_structure_all`(90문항)과 변형을 짝비교해 변형 우세 − 기준 우세 > 0이고 바뀐 문항 수 > 14. 95% CI는 함께 보고하되 CI만으로 채택하지 않는다. 임베딩을 바꾸면 인덱스 구축 비용이 다시 드는 점과 질의 임베딩 단가 차이를 함께 보고한다
- 게이트를 통과하지 못하면 답변 실행 없이 `gemini-embedding-2`를 유지하고 LLM 없는 지표로 비교 결과를 보고한다

## 4. LLM budget

- LLM-free 단계: 답변·채점 호출 0. 임베딩만 — 구조 청킹 인덱스를 `gemini-embedding-001`로 범위 A·B 각각 새로 만든다(청크 702개와 1,605개). 기준 인덱스 구축은 범위 A 0.030 USD + 범위 B 0.110 USD(`gemini-embedding-2`, 단가 0.20 USD/1M 토큰)였고, 같은 토큰이면 단가 0.15 USD/1M 토큰으로 약 0.1 USD로 예상한다. **`gemini-embedding-001`의 단가 0.15는 `configs/pricing.yaml`에 "공식 페이지에 없고 제3자 목록 기준, 카드 006 전에 확인"이라고 적힌 값이며 확인하지 못했다.** 비용 수치는 이 단가가 맞을 때만 맞다
- Planned calls if the gates pass: 기준 답변 실행 `dev_002_structure_all` answers 90 + judge 90, 변형 answers 90 + judge 90 = answers 180 + judge 180
- Calls so far in the project: submission/PROCESS.md 장부 참고

## 5. LLM-free results

dev 90문항 전체(evid@5 계산 74문항), `--retrieval-only`. 실험 이름 `dev_006_embedding001_retrieval`. `gemini-embedding-001`로 구조 청킹 인덱스를 범위 A·B 모두 새로 만들었다(702 + 1,605청크). 순증은 evid@5가 오른 문항 − 내린 문항.

| Config | evid@5 (dev 74) | Net vs baseline (+/−) | page_hit@5 | MRR | gold@5 | Context chars (90문항 평균) |
|---|---|---|---|---|---|---|
| gemini-embedding-2 (baseline) | 0.789 | – | 0.960 | 0.894 | 2.07 | 2,331 |
| gemini-embedding-001 | 0.843 | **+5** (16 / 11), diff +0.053, 95% CI [−0.012, +0.125] | 0.973 | 0.890 | 2.16 | 2,408 (1.03배) |

세트별 evid@5 (기준 → 변형, 오른 / 내린 문항):

| 세트 (n) | gemini-embedding-001 |
|---|---|
| base_positive (30) | 0.943 → 0.912 (3 / 6) |
| life_guide (10) | 0.773 → 0.814 (2 / 1) |
| additional (30) | 0.612 → 0.762 (11 / 4) |

- 오른 16문항: ADD-HF01 ADD-HF05 ADD-HF07 ADD-HP10 ADD-IN01 ADD-IN10 ADD-PF06 ADD-SE03 ADD-SE04 ADD-SE06 ADD-SE08 POS026 POS047 POS054 POS061 POS074. 내린 11문항: ADD-HF06 ADD-HP04 ADD-RP04 ADD-RP07 POS044 POS045 POS050 POS052 POS058 POS059 POS070
- 비용: 인덱스 구축 0.099 USD(범위 A + B, `configs/pricing.yaml`의 단가 0.15 USD/1M 토큰 기준이며 이 단가는 확인하지 못했다). 기준 인덱스는 0.140 USD(0.030 + 0.110). 질의 임베딩은 90문항 합계 0.0007 USD
- Cost cap: 문맥 1.03배로 상한(1.5배) 안
- LLM-free gate: 순증 +5 ≤ 14 → **불통과**
- Headroom (`evalkit/headroom.py --metric evid@5 --noise 14`): upside 8 (ADD-HF07 ADD-IN10 ADD-SE04 ADD-SE06 ADD-SE08 POS047 POS054 POS061), 이미 정답인데 오른 문항 8, risk 9 (ADD-HP04 ADD-RP04 ADD-RP07 POS045 POS050 POS052 POS058 POS059 POS070). upside − risk = **−1** ≤ 14
- Gates passed? **no** — 6절은 비운다

## 6. Answer run (only if the gates passed)

게이트 불통과로 실행하지 않았다. LLM 호출 0.

## 7. Decision and notes

- Decision: **reject** — `gemini-embedding-2`를 유지한다. 답변 실행 없음
- Why, with question IDs:
  - 평균 evid@5는 올랐지만(0.789 → 0.843) 오른 문항과 내린 문항이 뒤섞여 순증이 +5로 잡음 14 안이고, 95% CI도 0을 포함한다. 정답을 못 맞히던 문항 중 오른 것은 8개(upside)이고, 정답을 맞히던 문항 중 내린 것이 9개(risk)여서 점수 개선을 기대할 수 없다
  - 세트별로 반대다: additional은 올랐고(11 / 4) base_positive는 내렸다(3 / 6: POS044 POS045 POS050 POS052 POS058 POS059). 카드 004의 BM25·Hybrid와 같은 패턴(additional 상승, 용어·약관 문항 하락)이다
  - 1절에서 "접두어(문서명)가 없어서 약관 문항에서 불리할 수 있다"고 추측했는데, base_positive에서 내린 문항이 더 많았다. 다만 접두어 유무를 모델과 분리하지 않았으므로 원인이 접두어인지 모델 자체인지는 모른다
- What the criteria missed, if anything:
  - 접두어(문서명)와 모델을 분리하지 못했다(1절). 접두어가 영향이라면 `gemini-embedding-2`에서 접두어를 끈 설정이나 `gemini-embedding-001`에 문서명을 붙인 설정을 따로 비교해야 알 수 있다
  - 단가 0.15 USD는 확인하지 못했다. 비용 비교는 이 값이 맞을 때만 의미가 있다. 이 결정은 품질 게이트에서 막혀 비용과 무관하다
- 004·005·006의 공통 결과: 검색 구성(방식, 검색량, 임베딩)을 바꾼 변형 중 어느 것도 게이트를 통과하지 못했다. 최종 검색 구성은 **구조 청킹 + 벡터 검색 k=5 + `gemini-embedding-2`** 로 유지한다
