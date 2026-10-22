# 금융 문서 기반 RAG Agent

금융 PDF 23개(금융용어집, 표준약관, 금융생활 가이드, 추가 자료)를 검색해 파일명·페이지 근거와 함께 한국어로 답하는 RAG Agent와 그 평가 루프.

- 과제 설명: [docs/assignment.md](docs/assignment.md)
- 제출물 목록: [submission/README.md](submission/README.md)
- 실험 계획: [submission/PLAN.md](submission/PLAN.md)
- 진행 절차와 규칙: [docs/WORKFLOW.md](docs/WORKFLOW.md), [CLAUDE.md](CLAUDE.md)

## 폴더 구조

```
├── submission/          # 제출 문서: 계획, Agent 구조도, 진행 기록, 평가 결과
├── docs/                # 과제 원문, 진행 절차
├── 01_data/             # 원문 PDF (수정 금지)
├── 02_questions/        # 제공 질문 (수정 금지)
├── 03_answers/          # 제공 기준 답안 (수정 금지)
├── corpus/              # 페이지 추출 결과 pages.jsonl (git에 올림, 모두 같은 텍스트로 시작)
├── golden/              # 평가용 골든셋: 변환한 제공 세트 + 직접 만든 세트, 검수 기록
├── experiments/         # 실험 카드 (판단 기준을 결과보다 먼저 작성)
├── configs/             # baseline.yaml, 변형 설정, pricing.yaml (단가는 여기에만)
├── prompts/             # 답변·채점 프롬프트 (버전별 파일)
├── src/rag/             # 파이프라인 코드: 공통 기반(구현됨) + 문서 처리·청킹·검색·RAG·Agent·채점(구현할 부분)
├── scripts/             # 실행 진입점: build_index, run, grade, evaluate, compare, report
├── tests/               # 공통 기반 테스트 (python -m pytest)
├── evalkit/             # 실행 기록·지표·비교 도구 (표준 라이브러리만)
├── results/             # 실험별 결과와 SUMMARY.md (git에 올림, 형식: results/README.md)
├── out/                 # 인덱스, 로컬 실행 기록 runs.db, report.html (git 제외)
└── scratch/             # 일회성 분석 (git 제외)
```

## 설치

Python 3.13.13(`.python-version`)과 pip를 쓴다. 의존성 버전은 `requirements.txt`에 고정되어 있고, 바꿀 때는 팀 전체가 함께 바꾼다.

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env             # macOS/Linux: cp .env.example .env — 각자 자기 GOOGLE_API_KEY를 넣는다
python -m pytest                   # 공통 기반 테스트 (LLM 호출 없음)
```

- LangSmith 추적은 꺼진 상태로 고정된다: `.env.example`, `.claude/settings.json`, 스크립트 시작 시 `rag.env.setup()` 세 곳에서 끈다.
- API 키는 각자 쓴다. 비용은 실행 기록의 토큰으로 계산되므로 누가 돌렸든 같은 방식으로 집계된다.

## 실행 방법

실험 하나는 "설정 파일 1개 + 실험 카드 1장"이다(`configs/README.md`). 모든 실행은 아래 스크립트로만 한다.

```bash
python scripts/build_index.py --config configs/baseline.yaml                 # 청킹·임베딩 → out/index/
python scripts/run.py --config configs/baseline.yaml --split dev             # 질문 실행 → out/runs.db (중단 후 재실행하면 이어서)
python scripts/grade.py --experiment dev_000_baseline                        # 채점 → out/grades/
python scripts/evaluate.py --experiment dev_000_baseline --with-runs         # 지표·비용 → results/dev_000_baseline/
python scripts/report.py                                                     # 비교표 → results/SUMMARY.md, out/report.html

# 최종 시스템 인덱스 구축
python scripts/build_index.py --config configs/013b-rerank-lite.yaml

# 변형 실험: LLM 없이 검색만 비교
python scripts/run.py --config configs/004-hybrid.yaml --split dev --retrieval-only
python scripts/evaluate.py --experiment dev_004_hybrid_retrieval
python scripts/compare.py dev_000_baseline dev_004_hybrid_retrieval --metric gold@5
```

- test split은 `--final` 없이는 실행·채점·평가되지 않는다(워크플로우 8단계에서만).
- 단계별 명령은 [docs/WORKFLOW.md](docs/WORKFLOW.md)의 "Commands per step".
- 현재 상태: 구현·평가 완료(2026-10-22). 최종 시스템 = 구조 단위 청킹 + Hybrid 검색 + LLM rerank + `gemini-3.5-flash-lite` + `answer_v4`(`configs/013b-rerank-lite.yaml`). 결과와 근거는 [submission/EVALUATION.md](submission/EVALUATION.md), 과정은 [submission/PROCESS.md](submission/PROCESS.md).
- 페이지 추출(완료, 고정): `python scripts/extract_pages.py --vlm` → `corpus/pages.jsonl`(텍스트 레이어 + 범위 B VLM 보충) + `corpus/extraction.json` + 진단표. 다시 돌릴 필요 없음(바꾸면 근거 구절 대조·인덱스를 전부 다시 해야 함)

## 화면으로 보기 (Streamlit)

```bash
streamlit run app/streamlit_app.py     # 요약, 전체 흐름, 점수가 오른 과정, 청킹, 질문 따라가기(실시간 API 호출), 최종 시험, 문항별 결과
```

의존성은 `requirements.txt`의 `streamlit`이다. 실시간 페이지는 인덱스(`out/index/`)와 `GOOGLE_API_KEY`가 있어야 하고, 나머지 페이지는 `results/`만 읽는다.

## 협업

- 작업 시작 전에 [submission/PROCESS.md](submission/PROCESS.md) 맨 위 "현재 상태" 표에 GitHub 사용자 이름으로 담당을 적고, 그 변경만 바로 `main`에 커밋·푸시해 다른 사람이 보게 한다.
- 작업은 `<GitHub 사용자 이름>/<작업>` 브랜치에서 하고 PR로 `main`에 합친다. 결과 폴더(`results/`)도 같은 PR에 넣는다.
- 실행 기록 `out/runs.db`는 로컬에만 두고, 공유할 결과는 `results/<experiment>/`로 내보낸다: [results/README.md](results/README.md)
- 에이전트(Claude Code) 작업 규칙: [CLAUDE.md](CLAUDE.md)
