<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 010: 조합 청킹 — 구조 청킹 + 나머지 문서 Recursive 1000/125 (검색 구성 고정)

Status: decided — 최종 청킹 = 구조 청킹(STRUCT) (예외 승인 답변 실행 완료, 8절)
Date: 2026-10-21

## 1. Hypothesis

- Change (one variable): 구조 청킹(카드 002)의 `chunking.chunk_size` 800 → 1000, `chunk_overlap` 100 → 125 (`configs/010-struct1000.yaml`, `base: 002-structure.yaml`). 검색 구성은 카드 004~006 기각 결과로 고정(벡터 k=5, `gemini-embedding-2`)이고 답변 프롬프트·모델도 같다
  - **`chunk_size` 하나가 두 곳에 작용한다**(결과를 보기 전에 청크를 만들어 확인함): (1) 구조 단위가 아닌 문서(가이드·추가 자료 7개 문서)는 Recursive 800/100 → 1000/125로 바뀐다. (2) 용어집·약관의 구조 단위는 그대로지만 "조가 `chunk_size`보다 길면 페이지별로 Recursive로 자른다"는 한도가 800 → 1000자로 완화되어, 약관 14개 문서의 조 분할이 달라진다(범위 A 청크 702 → 670개, 범위 B 청크 1,605 → 1,434개). 용어집 용어는 최대 484자라 영향이 없다. 두 작용을 분리한 변형은 만들지 않는다
- Failure it targets: 카드 009에서 구조 청킹(STRUCT)은 용어집·약관(base_positive evid@5 0.943)에서, Recursive 1000/125(R1000)는 가이드·추가 자료(life_guide 0.820, additional 0.641)에서 낫고 서로 다른 문항을 풀었다. 이 조합이 두 영역의 이점을 합치는지 본다
- Expected effect: 범위 B의 가이드류 질문(life_guide, additional)은 R1000에 가까워지고(근거가 일부만 들어온 문항이 줄어든다), 용어집·약관 질문은 STRUCT에 가깝게 유지된다고 예상한다. 즉 세트별로 두 부모 중 높은 값 근처다. 두 부모를 넘을 것으로는 기대하지 않는다. 약관 조의 한도 완화가 base_positive에 주는 영향은 모른다. 위험: 가이드 문맥이 길어져(R1000은 R800의 1.21배) 전체 문맥 길이는 STRUCT(2,331자)보다 늘어난다

## 2. Measurement

- 비교 기준(재사용, 재실행 안 함): R800 `dev_000_baseline`, R1000 `dev_001_chunk1000_retrieval`, STRUCT `dev_002_structure_all_retrieval`. 모두 같은 검색 구성의 dev 90문항 실행이다
- Proxy metric: **evid@5**, 정답 페이지가 있는 dev 74문항. 함께 보고: page_hit@5, MRR, gold@5, 문맥 글자 수, 세트별 evid@5와 STRUCT·R1000 대비 오른/내린 문항, 일회성 인덱스 구축 비용
- Split: dev
- Noise (step 3): (a) 14 / 90, (b) 3 / 90 — 모든 dev 질문이 달라질 수 있어 전체 기준을 쓴다

## 3. Go/no-go criteria (written before results)

최종 청킹 후보는 R800(기준), R1000, STRUCT, 조합(COMBO) 4개다. 선택은 다음 순서로 한다.

- Cost cap: COMBO의 평균 문맥 글자 수 ≤ R800의 1.5배(3,064자 → 4,596자). 넘으면 후보에서 뺀다
- LLM-free gate: COMBO − R800의 evid@5 순증 > 14 **그리고** `evalkit/headroom.py --metric evid@5 --noise 14`의 upside − risk > 14. 둘 다 통과해야 답변 실행을 요청할 수 있다(카드 009에서 R1000과 STRUCT는 모두 통과하지 못한 같은 기준)
- 후보 간 순위: R800 대비 evid@5 순증(오른 − 내린 문항, 74문항)이 큰 순으로 R1000(+10), STRUCT(+9), COMBO를 순위 매긴다. 순증 차이가 3문항 이내이면 문맥이 짧은 쪽을 위로 둔다. COMBO가 1위가 되려면 STRUCT보다 순증이 4문항 넘게 커야 한다
- 해석 규칙(미리 정함): 잡음 14보다 작은 차이는 후보를 구분하지 못한다. COMBO − STRUCT, COMBO − R1000의 순증이 14 이하이면 "구분하지 못함"으로 적고, 순위는 위 규칙(순증 3문항 이내이면 문맥이 짧은 쪽)으로 정한다
- 답변 실행은 이 카드에서 하지 않는다. 게이트를 통과해도 사용자의 승인과 새 기준이 필요하다(전체 dev 90문항의 답변 점수를 비교하는 실행은 프로젝트 규칙상 게이트 통과가 전제다)

## 4. LLM budget

- LLM-free 단계: 답변·채점 호출 0. 임베딩만 — COMBO 인덱스를 범위 A(670청크)·B(1,434청크)로 새로 만든다. 기준 인덱스가 약 0.14 USD(R800, R1000, STRUCT 모두)였으므로 같은 규모를 예상한다. 질의 임베딩 90개
- Planned calls if the gates pass: 이 카드에서는 없음(위)
- Calls so far in the project: submission/PROCESS.md 장부 참고

## 5. LLM-free results

dev 90문항(evid@5 계산 74문항), `--retrieval-only`. 실험 이름 `dev_010_struct1000_retrieval`. 인덱스 범위 A 670청크, 범위 B 1,434청크, 구축 0.138 USD(R800 0.140, R1000 0.139, STRUCT 0.140과 같은 규모). 순증은 evid@5가 오른 문항 − 내린 문항.

| Config | evid@5 | Net vs R800 (+/−) | page_hit@5 | MRR | gold@5 | Context chars (74문항 평균) |
|---|---|---|---|---|---|---|
| R800 | 0.697 | – | 0.878 | 0.800 | 1.92 | 3,064 |
| R1000 | 0.764 | +10 (17 / 7) | 0.932 | 0.812 | 2.00 | 3,705 |
| STRUCT | 0.789 | +9 (10 / 1) | 0.959 | 0.894 | 2.07 | 2,331 |
| **COMBO** | **0.805** | **+14** (20 / 6), diff +0.108, 95% CI [+0.045, +0.177] | **0.986** | **0.908** | **2.16** | 2,683 (R800의 0.88배) |

세트별 evid@5:

| 세트 (n) | R800 | R1000 | STRUCT | COMBO |
|---|---|---|---|---|
| base_positive (30) | 0.717 | 0.836 | **0.943** | 0.937 |
| life_guide (10) | 0.773 | 0.820 | 0.773 | **0.826** |
| additional (30) | 0.612 | 0.641 | 0.612 | **0.641** |

부모와의 직접 비교 (evid@5, 74문항, 잡음 14):

| 비교 | 평균 차이 (95% CI) | 오른 / 내린 | 순증 |
|---|---|---|---|
| COMBO − STRUCT | +0.016 [−0.007, +0.041] | 10 / 6 | +4 |
| COMBO − R1000 | +0.042 [−0.009, +0.102] | 6 / 3 | +3 |

- COMBO − STRUCT: COMBO가 나은 문항은 모두 범위 B 질문(life_guide POS061 POS070, additional ADD-HP09 ADD-HP10 ADD-IN01 ADD-IN10 ADD-PF06 ADD-PF08 ADD-RP05 ADD-SE03)이고, 나쁜 문항은 additional 5개(ADD-HF06 ADD-HF07 ADD-IN08 ADD-PF01 ADD-SE08)와 base_positive POS050이다. base_positive는 오른 문항이 없다(0.943 → 0.937)
- COMBO − R1000: COMBO가 나은 문항은 base_positive POS006 POS013 POS017 POS045 POS052와 life_guide POS074이고, 나쁜 문항은 POS026 POS047 POS050이다. additional은 두 후보가 같다(0.641)
- 세트별로 두 부모 중 높은 값 근처다: base_positive는 STRUCT에 가깝고(0.937 대 0.943), life_guide와 additional은 R1000 이상이다(0.826, 0.641). 1절의 예상과 맞는다. life_guide는 R1000(0.820)을 0.006 넘지만 문항 10개 평균이라 의미 있는 차이가 아니다
- Cost cap: 문맥 0.88배로 상한(1.5배) 안
- LLM-free gate (COMBO − R800): 순증 **+14는 기준(> 14)에 1문항 못 미친다** → 불통과
- Headroom (`evalkit/headroom.py --metric evid@5 --noise 14`, 기준 채점 `dev_000_baseline`): upside 13 (ADD-HP09 ADD-IN10 ADD-PF08 ADD-RP05 POS001 POS006 POS013 POS021 POS050 POS052 POS057 POS058 POS061), 이미 정답인데 오른 문항 7, risk 5 (ADD-HF07 ADD-IN08 ADD-PF01 ADD-SE08 POS026). upside − risk = **8** ≤ 14 → 불통과
- Gates passed? **no**
- 후보 순위 (3절 규칙: R800 대비 순증이 큰 순, 차이 3문항 이내는 문맥이 짧은 쪽): COMBO(+14) > STRUCT(+9, R1000 +10과 1문항 차이여서 문맥이 짧은 쪽이 위) > R1000(+10) > R800. COMBO − STRUCT의 순증 차이는 5문항으로 3문항을 넘어 COMBO가 1위다

## 6. Answer run (only if the gates passed)

게이트 불통과로 실행하지 않았다. LLM 호출 0.

## 7. Decision and notes

- Decision: **검색 지표 기준 후보 순위 1위는 COMBO다. 그러나 후보 간 차이는 구분되지 않았고 게이트를 통과하지 못했으며 답변 수준의 증거가 없다.** 채택이라고 부르지 않는다. 답변 수준 비교는 실행하지 않았다
- Why, with question IDs:
  - COMBO는 evid@5(0.805), page_hit@5(0.986), MRR(0.908), gold@5(2.16)가 4개 후보 중 모두 가장 높고, 문맥은 R800보다 짧다(2,683자). 두 부모의 장점을 합쳤다: 용어집·약관 문항은 STRUCT 수준을 유지하고, 가이드·추가 자료 문항은 R1000 수준이다
  - 그러나 R800 대비 순증 +14는 게이트 기준에 1문항 모자라고 headroom은 8이다. COMBO − STRUCT 순증 +4, COMBO − R1000 순증 +3은 잡음 14보다 훨씬 작다. 후보 순위는 통계적으로 구분된 것이 아니라 사전 규칙(3절)을 적용한 결과다
- What the criteria missed, if anything:
  - **후보 선택 편향:** COMBO는 STRUCT와 R1000의 결과를 본 뒤에 추가한 후보다. 두 부모의 장점이 합쳐질 것이라는 가설은 카드 009에서 나왔고 이 카드는 그것을 사전 등록했지만, 4개 중 가장 좋아 보이는 후보가 우연히 높게 나왔을 가능성이 있다
  - **`chunk_size`의 두 작용을 분리하지 않았다**(1절). 가이드류의 1000/125와 약관 조 한도의 완화 중 무엇이 이득을 냈는지 모른다. COMBO가 STRUCT보다 나은 10문항은 모두 범위 B 질문이어서 가이드류 쪽 효과로 보이지만, 약관 조 한도의 영향(base_positive POS050이 내림)은 따로 확인하지 않았다(추측)
  - 3절의 순위 규칙은 R800 대비 순증을 쓰는데, 순증은 오른/내린 문항 수만 보고 크기를 보지 않는다. 평균 근거 포함률 순서(COMBO 0.805 > STRUCT 0.789 > R1000 0.764 > R800 0.697)와 순위가 같아 결론은 바뀌지 않는다
  - 답변 수준의 증거는 STRUCT의 범위 A 50문항(카드 002)뿐이다. 전체 dev 90문항에서 COMBO·STRUCT·R800의 답변 점수를 비교하려면 게이트 예외 승인이 필요하다

## 8. Answer-level comparison (예외 승인, 기준은 실행 전에 작성)

**2026-10-21 사용자가 게이트 미통과 답변 실행을 예외로 승인했다**(PROCESS.md 0절). 이유는 최종 청킹을 정하려면 답변 수준의 직접 비교가 필요한데 위 5절의 후보 순위는 통계적으로 구분되지 않기 때문이다. 이 절은 실행 전에 쓴다. 6절은 게이트 통과 시의 자리이므로 비워 둔다.

- 실행: COMBO `dev_010_struct1000`(`configs/010-struct1000.yaml`), STRUCT 전체 `dev_002_structure_all`(`configs/002-structure.yaml`, `--name dev_002_structure_all`; 카드 004~006이 구조 청킹 위 기준으로 가리키던 이름). 둘 다 dev 90문항 전체의 답변과 채점. 기준 R800은 기존 `dev_000_baseline`을 재사용한다. R1000은 승인 범위 밖이라 답변을 실행하지 않는다
- 비교 3개 (`scripts/compare.py`, 정답 점수 0~2): STRUCT − R800, COMBO − R800, COMBO − STRUCT
- 판정 규칙 (카드 004~006의 채택 규칙과 같다): 후보 X가 Y보다 낫다 ⇔ 우세 − 열세 > 0이고 바뀐 문항 수 > 14. 95% CI는 함께 보고하되 CI만으로 판정하지 않는다. 조건을 채우지 못하면 "구분하지 못함"이다
- 참고용 잡음(미리 계산해 둔 값): 같은 설정을 다시 실행했을 때 `dev_000_baseline` → `_r2`는 열세 11 / 우세 3 / 같음 76(순증 −8, 바뀐 14)이다. 이 크기의 순증은 잡음만으로 나올 수 있다
- 추가 보고(판정에는 쓰지 않음): 범위 A 50문항과 범위 B 40문항으로 나눈 비교. 범위 B에서 STRUCT는 R800과 문맥이 같으므로(ADD-RP04 하나 제외) STRUCT − R800의 범위 B 차이는 순수한 답변·채점 변동이다
- 최종 청킹 결정 규칙:
  1. COMBO가 R800과 STRUCT를 모두 이기면(위 규칙) COMBO
  2. COMBO와 STRUCT가 R800을 이기지만 서로 구분되지 않으면, 문항당 토큰(답변 비용)이 적은 쪽
  3. 한 후보만 R800을 이기면 그 후보
  4. 어느 후보도 R800을 이기지 못하면 R800 유지가 아니라 "구분하지 못함"으로 보고하고, 카드 002의 범위 A 결과(STRUCT 채택)를 유지할지는 사용자와 정한다
- 함께 보고: 깨진 출력 건수(`scripts/garble_scan.py`), 완전 정답 수, status_ok, 문항당 토큰·비용, p50/p90 응답 시간
- 예산: STRUCT 전체 answers 90 + judge 90, COMBO answers 90 + judge 90 = answers 180 + judge 180, 약 0.5 USD(기준 실행의 문항당 비용 0.00116 + 채점 약 0.0014 × 180)

### 8.1 결과 (dev 90문항, 정답 점수 0~2를 2로 나눈 값)

실험 이름 `dev_002_structure_all`(STRUCT), `dev_010_struct1000`(COMBO), 기준 `dev_000_baseline`(R800). 결과 `results/<실험>/`(runs.jsonl 포함). 깨진 출력: STRUCT 0/90, COMBO 0/90 (참고: R800 1/90, POS054).

| 후보 | 정답 점수 | 완전 정답 | status_ok | 문항당 토큰 | 문항당 비용(답변) |
|---|---|---|---|---|---|
| R800 | 0.722 | 51 | 74 | 2,916 | 0.00116 USD |
| STRUCT | 0.761 | 55 | 82 | 2,378 | 0.00100 USD |
| COMBO | 0.756 | 55 | 82 | 2,602 | 0.00107 USD |

짝비교 (우세 / 열세 / 같음, 순증, 바뀐 문항 수):

| 비교 | 정답 점수 차이 (95% CI) | 우세 / 열세 / 같음 | 순증 | 바뀐 | 사전 규칙(순증 > 0, 바뀐 > 14) |
|---|---|---|---|---|---|
| STRUCT − R800 | +0.039 [−0.028, +0.111] | 11 / 6 / 73 | +5 | 17 | 충족 |
| COMBO − R800 | +0.033 [−0.044, +0.111] | 14 / 10 / 66 | +4 | 24 | 충족 |
| COMBO − STRUCT | −0.006 [−0.050, +0.039] | 6 / 7 / 77 | −1 | 13 | 구분하지 못함 |

- STRUCT − R800 우세: ADD-HF06 ADD-IN10 NEG025 NEG039 POS001 POS006 POS013 POS021 POS045 POS052 POS058, 열세: ADD-HP06 ADD-HP10 ADD-IN01 ADD-SE06 NEG013 POS018
- COMBO − R800 우세: ADD-HF06 ADD-IN10 NEG025 NEG039 POS001 POS006 POS013 POS021 POS037 POS045 POS052 POS057 POS058 POS061, 열세: ADD-HF05 ADD-HP06 ADD-HP10 ADD-IN08 NEG003 NEG013 NEG037 POS047 POS051 POS064
- COMBO − STRUCT 우세: ADD-IN01 ADD-SE06 POS018 POS037 POS057 POS061, 열세: ADD-HF05 ADD-IN08 NEG003 NEG037 POS047 POS051 POS064

범위별 분해 (추가 보고, 판정에는 쓰지 않음):

| 범위 | 비교 | 우세 / 열세 / 같음 | 순증 | 정답 점수 |
|---|---|---|---|---|
| 범위 A 50문항 | STRUCT − R800 | 9 / 2 / 39 | +7 | 0.730 → 0.830 |
| | COMBO − R800 | 11 / 5 / 34 | +6 | 0.730 → 0.820 |
| | COMBO − STRUCT | 3 / 4 / 43 | −1 | 0.830 → 0.820 |
| 범위 B 40문항 | STRUCT − R800 | 2 / 4 / 34 | −2 | 0.713 → 0.675 |
| | COMBO − R800 | 3 / 5 / 32 | −2 | 0.713 → 0.675 |
| | COMBO − STRUCT | 3 / 3 / 34 | 0 | 0.675 → 0.675 |

### 8.2 판정과 해석

- **결정 (8절 규칙 2): 최종 청킹은 STRUCT(구조 청킹, 나머지 문서 Recursive 800/100)다.** STRUCT와 COMBO가 모두 R800에 대해 사전 규칙을 충족하고, 둘은 서로 구분되지 않으며(바뀐 13 ≤ 14, 순증 −1), 문항당 토큰이 적은 쪽(STRUCT 2,378 대 COMBO 2,602)을 고른다
- **이 판정의 근거는 약하다:**
  - R800 대비 순증 +5, +4는 같은 설정을 다시 실행했을 때의 잡음(순증 −8, 바뀐 14)과 같은 크기다. 95% CI도 0을 포함한다. 사전 규칙(순증 > 0이고 바뀐 문항 > 14)은 충족하지만 규칙 자체가 약하다
  - 이득은 전부 범위 A(용어집·약관)에서 나왔다. STRUCT − R800의 범위 A 순증은 +7이고, 카드 002의 별도 실행(`dev_002_structure`)에서도 +7이었다. 두 실행은 50문항 중 5문항의 점수와 49문항의 답변 문장이 달라서 독립된 실행이고, 같은 방향으로 재현되었다. 범위 B에서 STRUCT는 R800과 문맥이 같으므로(ADD-RP04 하나 제외) STRUCT − R800의 범위 B 차이는 순수한 변동이다: 40문항 중 6문항이 바뀌었고 순증 −2
  - 검색 지표에서는 COMBO가 범위 B 질문의 근거 포함률을 올렸지만(life_guide 0.826, additional 0.641) 답변 점수에서는 범위 B 순증이 −2로 STRUCT와 같아서(COMBO − STRUCT 0) 이득이 보이지 않는다. 근거 포함률이 오르는 것이 답을 개선하지 않았다
- 5절의 검색 지표 순위(COMBO가 1위)와 이 판정(STRUCT)이 다르다. 검색 지표의 차이(+4문항)는 잡음 안이었고 답변 수준에서도 구분되지 않았으며, 비용이 적은 STRUCT를 규칙대로 골랐다
- **지연 시간은 비교하지 않는다.** p90 응답 시간(R800 2.07 s, STRUCT 4.45 s, COMBO 3.05 s)은 아래 사고로 두 배치가 동시에 돌던 때의 값이라 후보의 차이로 읽으면 안 된다
- **Recursive 1000/125의 답변 점수는 측정하지 않았다**(승인 범위 밖). 카드 009의 세 후보 중 R1000은 답변 수준에서 비교되지 않았다

### 8.3 실행 사고 (비용과 기록)

- 처음 시작한 백그라운드 배치가 종료된 줄 알았으나 계속 돌았고, 다시 시작한 배치와 동시에 같은 두 실험을 실행했다. 결과: `dev_002_structure_all`의 답변 기록 163건(90문항, 73문항이 2회), `dev_010_struct1000` 171건(90문항, 81문항이 2회). 잔여 프로세스는 확인 뒤 종료했다
- 분석 도구는 문항마다 **가장 최근 기록 한 건**을 쓰므로(결과를 보고 고른 것이 아니다) 문항당 값은 하나로 정해진다. 채점도 그 90건씩만 했다. 쓰지 않은 중복 답변은 154회, 약 0.17 USD(`gemini-3.5-flash-lite` 단가 기준)다. 계획한 답변 180회 대신 334회를 호출했다
- 두 배치가 같은 설정을 쓴 독립 실행이고 문항별 기록 선택은 시간 순서라서 결과가 한쪽으로 치우쳤을 이유는 없다. 다만 하나의 실험이 두 프로세스의 결과를 섞고 있다는 점은 사실이다
