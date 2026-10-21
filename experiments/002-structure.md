<!--
GUIDE: One card per experiment. Copy to experiments/NNN-slug.md (NNN = 001, 002, ...).
Fill sections 1–4 BEFORE computing anything the experiment is judged by. Do not edit sections 1–4
after results are seen; if the criteria turn out to be wrong, say so in section 7 instead. That is
what makes the decision trustworthy.
Fill sections 5–7 as results arrive. Section 6 stays empty if the gates in section 5 fail.
Keep guide comment in place after filling in.
-->

# 002: 구조 단위 청킹 (용어집 용어 / 약관 조)

Status: decided — adopt (범위 A 한정 검증)
Date: 2026-10-21

## 1. Hypothesis

- Change (one variable): `chunking.method: recursive` → `structure` (`configs/002-structure.yaml`, 기준 800/100 위에 이것만 바꾼다)
  - 용어집(`financial_glossary_readable.pdf`): 용어 하나 + 정의 = 청크 하나. 용어 줄은 PDF 글꼴 크기(11pt, 정의는 10pt)로 구분한다. 페이지를 넘어가는 정의는 이어 붙인다
  - 표준약관 15개: `제N조(제목)` 머리글마다 청크 하나. 페이지를 넘어가는 조는 이어 붙인다
  - 조·용어가 `chunk_size`(800)보다 길면 페이지별로 기준과 같은 Recursive 800/100으로 자른다(청크는 자기 글이 있는 페이지를 유지). 용어집·약관이 아닌 문서(가이드 등)는 기준과 같은 Recursive 800/100 그대로다. 약관·용어집의 페이지 번호 줄과 용어집 제목 줄 "금융용어 모음"은 청크에 넣지 않는다
  - 구현 확인(결과 지표를 보기 전, 검색 없이): 범위 A 4,181줄 중 청크에 없는 줄은 제목 줄 1개뿐이고, 용어 청크 228개는 PDF의 용어 줄 228개와 같다. dev 근거 구절 171개 중 정답 페이지 청크 하나에 통째로 들어 있는 수는 기준 164 → 구조 165(POS038이 온전해짐, 새로 잘린 문항 없음)였다. 이 숫자는 이 카드의 판정에 쓰지 않는다
- 범위 A 문서만 청크가 바뀐다. 가이드(범위 B)의 구조 단위(제목 단위)는 이 카드에서 하지 않는다: 제목 위치를 신뢰성 있게 얻는 방법이 없고(PDF 글꼴이 문서마다 다르다), 기준과 같은 Recursive를 유지해 한 번에 한 요소만 바꾼다
- Failure it targets (PROCESS.md 6절, `dev_000_baseline`):
  - 용어집 정의 검색 실패 4문항 POS001, POS006, POS013, POS021 — 800자 청크 하나에 용어 약 8개가 섞여 정의 하나의 임베딩이 묻힌다(1.3절). 001에서 청크 크기만으로는 POS006·POS013을 어떤 크기에서도 잡지 못했다
  - 약관 근거가 청크 경계에서 잘리거나 옆 청크에 있는 문항(POS047, POS050, POS052, POS061 등, 6절 분류)
- Expected effect: 용어 하나가 청크 하나라서 용어 질문의 evid@5와 page_hit@5가 오를 것으로 본다. 반대로 위험도 있다: 용어집 청크가 평균 약 100자로 아주 짧아서 비슷한 용어 청크 여러 개가 상위 5개를 채우면 문맥이 짧아지고, 여러 조가 필요한 문항에서 근거가 줄 수 있다. 문맥 글자 수는 기준(평균 3,064자)보다 줄 것으로 예상한다. 어느 쪽이 클지는 모른다

## 2. Measurement

- Baseline run (reused, not rerun): `dev_000_baseline` (`results/dev_000_baseline/metrics.jsonl`, `grades.jsonl`)
- 달라질 수 있는 문항: 이 변경은 범위 A(용어집 + 약관)의 청크만 바꾸고, 범위 B 문서는 청크가 기준과 같다. dev에서 범위 A로 가는 세트는 base_positive·base_negative 50문항(정답 페이지가 있어 evid@5를 계산하는 문항 34 = positive 30 + negative 4)이다. 나머지 40문항(life_guide·additional)은 검색 결과가 기준과 같으므로 실행하지 않는다(인덱스는 범위 A만 새로 만든다)
- Proxy metric (step 4): **evid@5** — 정답 점수와 Pearson r 0.50–0.61(PROCESS.md 5절). 위 34문항에서 계산
- 함께 보고: 문맥 글자 수 `chars`(짧은 청크는 evid@5가 쉽게 내린다), page_hit@5, MRR, gold@5, 위 1절 대상 문항별 변화(POS001·006·013·021, POS047·050·052·061), 용어집 문항과 약관 문항으로 나눈 evid@5
- Split: dev
- Noise (step 3): 전체 (a) 14 / 90, (b) 3 / 90. 이 카드는 **범위 A 50문항만의 잡음**을 쓴다: (a)에서 바뀐 14문항 중 범위 A는 5문항(POS001, POS045, NEG013, NEG020, NEG039) — `results/dev_000_baseline{,_r2}/grades.jsonl`에서 이 카드를 쓰기 전에 계산했다

## 3. Go/no-go criteria (written before results)

전체 기준 14(PROCESS.md 4절)를 그대로 쓰면 달라질 수 있는 문항이 34개뿐인데 순증 15 이상이 필요해 구조상 통과할 수 없다. 잡음은 비교하는 문항 집단에서 재야 하므로, 이 카드는 같은 집단(범위 A)의 잡음 5를 쓴다. 이 기준 변경은 결과를 보기 전에 이 카드에 쓰며, PROCESS.md 0절에 날짜와 이유를 적는다. 비교 변형은 하나뿐이라 변형 선택 편향은 없다.

- LLM-free gate: 범위 A의 evid@5 순증(오른 문항 수 − 내린 문항 수, 34문항) > 5
- Headroom gate: `evalkit/headroom.py --metric evid@5 --noise 5`를 범위 A 문항만으로 계산한 upside − risk > 5
- Cost cap: 평균 문맥 글자 수(범위 A 34문항) ≤ 기준의 1.5배. 구조 청킹은 문맥이 줄어들 것으로 예상하므로, 줄어드는 것은 상한과 무관하게 결과에 적는다
- Adopt if (answer run): 범위 A 50문항(base_positive·base_negative)에서 짝비교(`dev_000_baseline`의 같은 문항)로 변형 우세 − 기준 우세 > 0이고 바뀐 문항 수 > 5. 95% CI가 0을 벗어나는지는 함께 보고하되, 4절 잡음 측정에서 같은 설정끼리도 CI가 0을 벗어났으므로 CI만으로는 채택하지 않는다. negative 문항의 대응 일치(status_ok)가 내리면 따로 적는다
- 게이트를 통과하지 못하면 답변 실행 없이 기준을 유지하고, LLM 없는 지표로 비교 결과를 보고한다(PLAN 3.2, 2026-10-20 결정)

## 4. LLM budget

- LLM-free 단계: 답변·채점 호출 0. 임베딩만 — 범위 A 인덱스 1회(약 700청크)와 질의 50개. 실제 비용은 구축 후 5절에 적는다
- Planned calls if the gates pass: answers 50 + judge 50 (`--sets base_positive,base_negative`)
- Calls so far in the project: submission/PROCESS.md 장부 참고

## 5. LLM-free results

dev 범위 A 질문(`--sets base_positive,base_negative` 50문항, 이 중 정답 페이지가 있어 evid@5를 계산하는 34문항). 실험 이름 `dev_002_structure_retrieval`, 범위 A 인덱스 702청크(기준 309청크), 인덱스 구축 0.030 USD. 순증은 evid@5가 오른 문항 수 − 내린 문항 수.

| Config | evid@5 (dev 34) | Net vs baseline (+/−) | page_hit@5 | MRR | Context chars (34문항 평균) |
|---|---|---|---|---|---|
| baseline 800/100 | 0.750 | – | 0.824 | 0.765 | 3,400 |
| structure | 0.950 | **+9** (10 / 1), diff +0.200, 95% CI [+0.076, +0.341] | 1.000 | 0.985 | 1,795 (0.53배) |

- 오른 10문항: POS001 POS006 POS013 POS017 POS021 POS044 POS050 POS052 POS057 POS058. 내린 1문항: POS026
- 1절 대상 문항(evid@5 / page_hit@5): 용어집 정의 POS001·POS006·POS013·POS021은 모두 0 → 1.0, 0 → 1로 정답 페이지와 근거가 모두 들어왔다. 001에서 어떤 청크 크기로도 못 잡던 POS006·POS013도 포함된다. 약관: POS052 0 → 1.0, POS050 0.62 → 0.88, POS047은 0.58 그대로(문맥 3,567 → 3,214자), POS061은 범위 B 문항이라 이 카드에서 바뀌지 않는다
- 문맥은 평균 절반으로 줄었다(용어집 문항은 약 3,000자 → 1,200~1,800자). 용어 청크가 짧아서 같은 5개로도 필요한 정의만 들어온다
- Headroom (`evalkit/headroom.py --metric evid@5 --noise 5`, 범위 A 34문항): upside 8 (POS001 POS006 POS013 POS021 POS050 POS052 POS057 POS058), 이미 정답인데 오른 문항 2, risk 1 (POS026). upside − risk = **7** > 5
- Cost cap: 문맥 0.53배로 상한(1.5배) 아래
- Gates passed? **yes** (순증 +9 > 5, upside − risk 7 > 5, cost cap 통과)

## 6. Answer run (only if the gates passed)

- Experiment name: `dev_002_structure` (결과 `results/dev_002_structure/`, `runs.jsonl` 포함). 범위 A 50문항(base_positive 30 + base_negative 20), 기준은 `dev_000_baseline`의 같은 50문항
- Paired vs baseline: 변형 우세 9 / 기준 우세 2 / 같음 39, 정답 점수 0.730 → 0.830 (diff +0.100, 95% CI [−0.010, +0.210]), 순증 +7, 바뀐 문항 11 > 잡음 5. 완전 정답 31 → 37, status_ok 38/50 → 43/50
  - 변형 우세: POS001 1→2, POS006 0→2, POS013 0→2, POS021 0→2, POS037 1→2, POS045 1→2, POS052 0→2, POS058 0→2, NEG025 0→1
  - 기준 우세: POS044 2→0, NEG013 2→0
  - 세트별 정답 점수: base_positive(30) 0.683 → 0.867 (완전 정답 17 → 24), base_negative(20) 0.800 → 0.775 (14 → 13), status_ok base_positive 21 → 27, base_negative 17 → 16
- Tokens / latency vs baseline: 문항당 토큰 2,916 → 1,931 (0.66배), 비용 0.00116 → 0.00083 USD (0.71배), p90 응답 2.07 → 2.23 s (거의 같음, 검색 후 답변 1회로 구조 동일)
- 깨진 출력: `garble_scan.py dev_002_structure` 0 / 50
- LLM calls used: answers 50 + judge 50 (답변 0.041 USD, 채점 0.060 USD)

## 7. Decision and notes

- Decision: **adopt** — 사전 등록한 채택 기준(변형 우세 − 기준 우세 +7 > 0, 바뀐 문항 11 > 5)을 충족한다. 단, 범위 A(용어집·약관) 질문에서만 검증했고, 95% CI가 0을 약간 포함한다([−0.010, +0.210]). CI만으로 채택하지 않는다는 기준이므로 판정은 바뀌지 않지만, 확정적인 근거는 아니다
- Why, with question IDs:
  - 기준의 검색 실패였던 용어집 4문항 POS001·POS006·POS013·POS021이 검색에서 모두 해결됐고 답도 모두 2점이 됐다(0·1점 → 2점). 청크 크기 변경(카드 001)이 못 푼 POS006·POS013까지 풀렸으므로 원인이 "한 청크에 여러 용어가 섞임"이라는 6절 설명과 맞는다
  - 약관 쪽: POS052(0 → 2점, 두 조가 필요한 문항), POS058(0 → 2점), POS037, POS045(1 → 2점)도 올랐다
  - 구조 청킹의 비용이 아니라 이득이다: 문맥이 절반으로 줄어 문항당 토큰 0.66배, 비용 0.71배
- 점수가 내린 문항과 잡음:
  - POS044(2 → 0): 구조 청킹에서 근거는 오히려 더 들어왔는데(evid@5 0.78 → 1.0) 답변이 clarify로 갔다. 검색이 아니라 답변 단계의 변동으로 보인다(추측)
  - NEG013(2 → 0): 근거 지표가 없는 negative 문항이고, 기준 재실행(4절 (a))에서도 점수가 바뀐 문항이다. 같은 질문에서 기준은 되묻기를 하고 구조는 단정해서 답했다(되묻기 기대 대응 위반)
  - 11개 중 POS001·POS045·NEG013은 기준 재실행에서 이미 점수가 흔들렸던 문항(사후 확인용이며 판정 기준은 아니다). 이 셋을 빼도 7 / 1로 순증 +6, 바뀐 문항 8로 기준을 넘는다
  - base_negative는 0.800 → 0.775로 약간 내렸다(NEG025 올랐고 NEG013 내림). 이 문항은 검색이 아니라 대응 방식에 달려 있어서 이 카드가 겨냥한 것이 아니다
- What the criteria missed, if anything:
  - 범위 B(가이드) 문항 40개는 검색 결과가 기준과 같아 실행하지 않았다. 전체 dev 90문항의 정답 점수 비교가 아니라 범위 A 50문항의 비교다. 최종 시스템에 구조 청킹을 쓸 때 전체 점수는 범위 B가 기준과 같으므로 범위 A의 변화만큼만 움직인다
  - 가이드의 제목 단위 청킹은 하지 않았다(1절). 범위 B에서 구조 단위가 도움이 되는지는 모른다
  - 범위 A 한정 잡음(5/50)을 쓴 것은 결과 전에 이 카드에 적은 기준 변경이다. 전체 잡음 14와 전체 74문항 기준으로는 순증 +9 ≤ 14라 통과하지 못한다
  - 짧은 청크(용어집 평균 99자)가 상위 5개를 채우는 위험은 나타나지 않았다(용어집 4문항 모두 개선, 내린 문항은 POS026 1개). 용어집 문항이 더 많은 test에서도 같은지는 8단계에서 본다(test는 지금 보지 않는다)
- 다음: 003 문맥 보존(문서명·상위 제목 머리말)이 구조 청킹 위에서 도움이 되는지 본다. 채택한 구조 청킹을 기준으로 삼으려면 `configs/002-structure.yaml`을 `base:`로 쓴다
