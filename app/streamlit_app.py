"""Streamlit viewer for the whole project, written for people who have never seen it.

    streamlit run app/streamlit_app.py

Pages: overview, flow, score history, chunking, a live question run step by step, final test, per-question
results, glossary. The live page calls the Gemini API (needs .env) and uses the indexes in out/index
(scripts/build_index.py). It runs dev questions or free text, never the test split.
"""

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from rag import env  # noqa: E402
from rag.config import load_config  # noqa: E402
from rag.cost import call_usd, load_prices  # noqa: E402
from rag.golden import load_golden  # noqa: E402
from rag.retrieval import index_dir  # noqa: E402

CFG_LITE = "configs/013b-rerank-lite.yaml"      # recommended: gemini-3.5-flash-lite + prompt v4 + rerank
CFG_FLASH = "configs/013-rerank-flash36.yaml"   # measured on the test split (T2): gemini-3.6-flash
CFG_AGENT = "configs/008b-agent-950.yaml"
CFG_BASE = "configs/baseline.yaml"
RESULTS = ROOT / "results"

st.set_page_config(page_title="금융 문서 질의응답 시스템", page_icon="📚", layout="wide")

st.markdown("""
<style>
.block-container {max-width: 1180px; padding-top: 2rem;}
h1 {font-weight: 800; letter-spacing: -0.5px;}
.hero {background: linear-gradient(135deg,#eef2ff 0%,#e0f2fe 100%); border-radius: 18px; padding: 28px 32px; margin-bottom: 18px; color:#0f172a;}
.hero h2 {margin: 0 0 6px 0; font-size: 1.6rem; color:#0f172a;}
.hero p {margin: 0; font-size: 1.05rem; color: #334155;}
.card {border: 1px solid #cbd5e1; border-radius: 14px; padding: 16px 18px; background: #f8fafc; height: 100%; color:#0f172a;}
.card h4 {margin: 0 0 6px 0; color:#0f172a;}
.card p {margin: 0; color: #475569; font-size: 0.95rem;}
.step {display:inline-block; width: 28px; height: 28px; line-height: 28px; text-align:center; border-radius: 50%;
       background:#4f46e5; color:#fff; font-weight:700; margin-right:8px;}
.pill {display:inline-block; padding: 3px 12px; border-radius: 999px; font-weight:700; font-size:0.9rem;}
.p-ok {background:#dcfce7; color:#166534;} .p-hold {background:#fef3c7; color:#92400e;}
.p-ask {background:#dbeafe; color:#1e40af;} .p-no {background:#fee2e2; color:#991b1b;}
.chunk {border-left: 5px solid #94a3b8; background:#f1f5f9; border-radius: 8px; padding: 8px 12px; margin: 6px 0; font-size: 0.9rem; color:#0f172a;}
.chunk.picked {border-left-color:#16a34a; background:#dcfce7; color:#0f172a;}
.chunk .tag {font-size:0.78rem; color:#475569;}
.big {font-size: 2.1rem; font-weight: 800; line-height: 1.1;}
.sub {color:#64748b; font-size:0.9rem;}
.note {background:#fffbeb; border:1px solid #fde68a; border-radius:10px; padding:10px 14px; color:#78350f;}
.note b {color:#78350f;}
</style>
""", unsafe_allow_html=True)

STATUS = {"answered": ("✅ 답했어요", "p-ok"), "abstained": ("⏸ 근거가 없어 보류", "p-hold"),
          "clarify": ("❓ 되물었어요", "p-ask"), "refused": ("⛔ 해서는 안 되는 요청이라 거절", "p-no")}


def pill(status: str) -> str:
    text, css = STATUS.get(status, (status, "p-hold"))
    return f'<span class="pill {css}">{text}</span>'


def card(title: str, body: str):
    st.markdown(f'<div class="card"><h4>{title}</h4><p>{body}</p></div>', unsafe_allow_html=True)


def hero(title: str, text: str):
    st.markdown(f'<div class="hero"><h2>{title}</h2><p>{text}</p></div>', unsafe_allow_html=True)


# ---------------------------------------------------------------- loaders
@st.cache_data
def cfg_of(path: str) -> dict:
    return load_config(ROOT / path)


@st.cache_data
def summary_of(exp: str):
    p = RESULTS / exp / "summary.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


@st.cache_data
def jsonl(path: str) -> list[dict]:
    p = Path(path)
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


@st.cache_resource
def system_of(cfg_path: str):
    from rag.systems import build_system
    return build_system(load_config(ROOT / cfg_path))


def score(exp: str, key: str = "correctness_mean"):
    s = summary_of(exp)
    return s["scores"].get(key) if s else None


# ---------------------------------------------------------------- 0. overview
def page_overview():
    st.title("📚 금융 문서 질의응답 시스템")
    hero("금융 PDF 23개를 읽고, 근거를 붙여 답하는 AI 도우미",
         "질문하면 문서에서 관련 부분을 찾아 그것만 근거로 답하고, 어느 문서 몇 쪽인지 출처를 붙입니다. "
         "근거가 없으면 지어내지 않고 ‘모르겠다’고 말합니다.")
    st.subheader("쉽게 비유하면: 도서관 사서")
    cols = st.columns(5)
    items = [("1. 책 정리", "PDF를 쪽마다 글자로 바꾸고, 표·그래프는 AI가 글로 풀어 적습니다."),
             ("2. 카드 만들기", "글을 검색하기 좋은 작은 조각으로 자릅니다. (용어는 용어 하나, 약관은 조 하나)"),
             ("3. 후보 찾기", "질문과 뜻이 비슷한 조각과 단어가 겹치는 조각 15개를 꺼냅니다."),
             ("4. 사서가 고르기", "AI가 15개를 읽고 정말 필요한 5개만 고릅니다. (rerank)"),
             ("5. 답하기", "고른 5개만 보고 답을 쓰고, 출처를 붙입니다.")]
    for col, (t, b) in zip(cols, items):
        with col:
            card(t, b)
    st.divider()
    st.subheader("결과 한눈에 보기")
    t1, t2, t3 = score("test_000_baseline"), score("test_013_rerank_flash36"), score("test_008b_agent950")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("처음 시스템 점수", f"{t1:.2f}" if t1 else "-", help="최종 시험(110문항) 정답 점수, 0~1")
    m2.metric("개선한 시스템 점수", f"{t2:.2f}" if t2 else "-", f"+{t2 - t1:.2f}" if t1 and t2 else None)
    m3.metric("Agent 구조 점수", f"{t3:.2f}" if t3 else "-", f"+{t3 - t2:.2f} (오차 범위)" if t2 and t3 else None, delta_color="off")
    m4.metric("권장 설정의 문항당 비용", "약 0.0035달러", help="gemini-3.5-flash-lite + 프롬프트 v4 + rerank, 개발용 90문항 기준")
    st.markdown('<div class="note"><b>읽는 법</b> 점수는 정답 0점·부분 1점·정답 2점을 평균해 0~1로 만든 값입니다. '
                '같은 설정을 다시 돌리면 90문항 중 약 14문항의 답이 달라지므로 0.02 정도의 차이는 의미가 없습니다.</div>',
                unsafe_allow_html=True)
    st.write("")
    st.info("왼쪽 메뉴에서 ‘질문 따라가기’를 열면 질문 하나가 위 5단계를 지나는 모습을 직접 볼 수 있습니다.")


# ---------------------------------------------------------------- 1. flow
PIPELINE = """
digraph G {
  graph [rankdir=LR, fontname="Helvetica", fontsize=16, fontcolor="#64748b", nodesep=0.35, ranksep=0.5, pad=0.3];
  node [shape=box, style="rounded,filled", fontname="Helvetica", fontcolor="#0f172a", fontsize=15, margin="0.2,0.12", color="#94a3b8"];
  edge [color="#94a3b8", penwidth=1.6, arrowsize=0.9];
  subgraph cluster_prep { label="① 준비 (한 번만 합니다)"; style="rounded,dashed"; color="#94a3b8"; fontcolor="#94a3b8"; fontsize=17;
    pdf [label="PDF 23개", fillcolor="#e0e7ff"];
    ext [label="쪽별 글자 추출\\n표·그래프는 AI가 글로 풀이", fillcolor="#e0e7ff"];
    chunk [label="조각으로 자르기\\n용어집=용어 하나\\n약관=조 하나\\n나머지=950자", fillcolor="#e0e7ff"];
    emb [label="뜻을 숫자로 바꾸기\\n(임베딩)", fillcolor="#e0e7ff"];
    store [label="저장소\\n벡터 + 단어 색인", fillcolor="#fde68a"];
    pdf -> ext -> chunk -> emb -> store; }
  subgraph cluster_ask { label="② 질문이 들어오면"; style="rounded,dashed"; color="#94a3b8"; fontcolor="#94a3b8"; fontsize=17;
    q [label="질문", shape=oval, fillcolor="#bbf7d0"];
    hy [label="후보 15개 찾기\\n(뜻 비슷 + 단어 일치)", fillcolor="#bfdbfe"];
    rr [label="AI가 5개 고르기\\n(rerank)", fillcolor="#fcd34d"];
    ans [label="근거만 보고 답하기\\n+ 출처 붙이기", fillcolor="#bfdbfe"];
    out [label="답변\\n(답함·보류·되묻기·거절)", shape=oval, fillcolor="#bbf7d0"];
    q -> hy -> rr -> ans -> out; }
  store -> hy [style=dashed];
}
"""

AGENT = """
digraph A {
  graph [rankdir=TB, fontname="Helvetica", pad=0.3, nodesep=0.4, ranksep=0.45];
  node [shape=box, style="rounded,filled", fontname="Helvetica", fontcolor="#0f172a", fontsize=15, margin="0.2,0.12", color="#94a3b8", fillcolor="#e0e7ff"];
  edge [color="#94a3b8", penwidth=1.5, fontname="Helvetica", fontsize=13, fontcolor="#94a3b8"];
  s [label="질문", shape=oval, fillcolor="#bbf7d0"]; e [label="끝", shape=oval, fillcolor="#bbf7d0"];
  classify [label="질문 종류 판단\\n(문서 질문? 되물어야? 부적절?)"];
  retrieve [label="찾기 (rerank 포함)"]; grade [label="찾은 근거로 답할 수 있나?", fillcolor="#fde68a"];
  rewrite [label="검색어 다시 쓰기 (최대 2번)"]; generate [label="답하기"]; cite [label="출처 번호가 맞는지 확인", fillcolor="#fde68a"];
  s -> classify -> retrieve -> grade;
  grade -> rewrite [label="부족"]; rewrite -> retrieve;
  grade -> generate [label="충분"];
  generate -> cite; cite -> generate [label="틀림(1번 재시도)"]; cite -> e [label="통과"];
}
"""


def page_flow():
    st.title("🧭 전체 흐름")
    st.caption("글자 그대로 따라가면 됩니다. 점선 위쪽은 미리 한 번 해 두는 일, 아래쪽은 질문이 올 때마다 하는 일입니다.")
    st.graphviz_chart(PIPELINE, width="stretch")
    st.subheader("단계별로 자세히")
    steps = [
        ("글자 뽑기", "PDF에서 글자를 쪽마다 뽑습니다. 표·그래프는 그림이라 글자로 안 나오므로, AI가 그림을 읽고 글로 풀어 뒤에 붙입니다(한 번만, 약 1달러).", "PyMuPDF + gemini-3.8-flash"),
        ("조각으로 자르기", "용어집은 용어 하나, 약관은 조 하나를 한 조각으로 둡니다. 정의 하나가 반으로 잘리면 검색에서 놓치기 때문입니다. 가이드북과 보고서는 950자씩 자르고 앞뒤 119자를 겹칩니다. AI를 쓰지 않는 규칙입니다.", "구조 단위 + Recursive 950/119"),
        ("후보 15개 찾기", "‘뜻이 비슷한’ 조각(벡터 검색)과 ‘같은 단어가 있는’ 조각(BM25)을 절반씩 섞어 15개를 꺼냅니다. 한쪽만 쓰면 놓치는 것이 달랐기 때문입니다.", "gemini-embedding-2 + BM25"),
        ("AI가 5개 고르기 (rerank)", "15개를 AI가 읽고 질문에 답하는 데 필요한 5개만 고릅니다. 이 단계가 점수를 가장 크게 올렸습니다(근거를 찾는 비율 0.86 → 0.94).", "답변 모델이 직접 고름"),
        ("답하기", "고른 5개만 근거로 답합니다. 근거가 없으면 보류, 질문이 모호하면 되묻기, 해서는 안 되는 요청이면 거절합니다. 출처 번호는 코드가 파일·쪽으로 바꿔 붙입니다.", "gemini-3.5-flash-lite (권장) + 프롬프트 v4"),
    ]
    for i, (t, body, tech) in enumerate(steps, 1):
        with st.expander(f"{i}. {t}", expanded=(i == 4)):
            st.write(body)
            st.caption(f"실제로 쓴 것: {tech}")
    st.divider()
    st.subheader("비교용: Agent 구조")
    st.write("같은 검색·답변에 ‘스스로 점검하는 단계’를 더한 버전입니다. 근거가 부족하면 검색어를 고쳐 다시 찾습니다. 점수는 조금 올랐지만 오차 범위였고 비용이 1.4배라 최종 시스템으로 쓰지 않았습니다.")
    st.graphviz_chart(AGENT, width="stretch")


# ---------------------------------------------------------------- 2. history
MILESTONES = [
    ("처음 시스템", "고정 800자 · 벡터 검색 · 작은 모델", "dev_000_baseline"),
    ("용어·조항 단위로 자르기", "용어집은 용어, 약관은 조 단위", "dev_002b_structure900"),
    ("단어 검색 섞기", "벡터 + BM25 Hybrid", "dev_004_hybrid"),
    ("더 큰 모델", "gemini-3.6-flash", "dev_007_flash36"),
    ("조각 크기 950자", "900 → 950", "dev_001e_chunk950chain"),
    ("답변 규칙 다듬기 v2", "빠뜨림·과잉 보류 줄이기", "dev_010_answerv2"),
    ("답변 규칙 v4", "항목별 답변, 거절 규칙 정리", "dev_012_flash36_v4"),
    ("AI가 5개 고르기", "rerank (후보 15 → 5)", "dev_013_rerank_flash36_fix"),
]


def page_history():
    st.title("📈 점수가 어떻게 올랐나")
    st.caption("개발용 90문항으로 측정한 값입니다. 막대가 높을수록 정답에 가깝습니다.")
    rows, prev = [], None
    for name, what, exp in MILESTONES:
        v = score(exp)
        if v is not None:
            rows.append({"단계": name, "점수": v, "변화": None if prev is None else v - prev, "바꾼 것": what, "실험": exp})
            prev = v
    df = pd.DataFrame(rows)
    st.bar_chart(df.set_index("단계")["점수"], height=320)
    cols = st.columns(4)
    for i, r in df.iterrows():
        with cols[i % 4]:
            delta = None if r["변화"] is None else f"{r['변화']:+.3f}"
            st.metric(f"{i + 1}. {r['단계']}", f"{r['점수']:.3f}", delta)
            st.caption(r["바꾼 것"])
    st.markdown('<div class="note">변화가 ±0.02 안쪽이면 운에 따른 흔들림과 구별되지 않습니다. '
                '그 흔들림을 확실히 이긴 개선은 <b>‘AI가 5개 고르기(rerank)’</b> 하나였습니다.</div>', unsafe_allow_html=True)
    st.subheader("작은 모델(3.5 flash lite)로 낮췄을 때")
    lite = [("작은 모델 + 규칙 v2", "dev_011_lite_v2"), ("+ 규칙 v3", "dev_011b_lite_v3"), ("+ 규칙 v4", "dev_011c_lite_v4"),
            ("+ rerank (권장)", "dev_013b_rerank_lite_fix")]
    cols = st.columns(4)
    for col, (n, e) in zip(cols, lite):
        col.metric(n, f"{score(e):.3f}" if score(e) else "-")
    st.caption("큰 모델(3.6 flash) + rerank는 0.928, 작은 모델 + rerank는 0.894입니다. 답변 비용은 작은 모델이 약 40% 수준입니다(문항당 0.0035달러 대 0.0086달러).")
    with st.expander("실험 번호와 카드 보기 (자세히 알고 싶을 때)"):
        st.dataframe(df[["단계", "실험", "점수", "변화"]], hide_index=True, width="stretch")
        cards = sorted((ROOT / "experiments").glob("0*.md"))
        pick = st.selectbox("실험 카드", cards, format_func=lambda p: p.stem)
        st.markdown(pick.read_text(encoding="utf-8").split("-->", 1)[-1])


# ---------------------------------------------------------------- 3. chunks
def chunk_html(c: dict) -> str:
    text = c["content"].replace("<", "&lt;").replace(">", "&gt;").replace("\n", " ")
    return f'<div class="chunk"><span class="tag">{len(c["content"])}자 · p.{c["page"]}</span><br>{text[:420]}{"…" if len(text) > 420 else ""}</div>'


def page_chunks():
    st.title("✂️ 글을 어떻게 잘랐나")
    st.write("검색은 ‘조각’ 단위로 합니다. 조각이 너무 크면 엉뚱한 내용이 섞이고, 너무 작으면 설명이 잘려 나갑니다. "
             "그래서 용어집과 약관은 **의미 단위**(용어 하나, 조 하나)로 자르고, 나머지는 **950자**로 잘랐습니다.")
    base = jsonl(str(index_dir(cfg_of(CFG_BASE), "B") / "chunks.jsonl"))
    final = jsonl(str(index_dir(cfg_of(CFG_LITE), "B") / "chunks.jsonl"))
    if not base or not final:
        st.warning("인덱스가 없습니다. scripts/build_index.py 를 먼저 실행하세요.")
        return
    m1, m2 = st.columns(2)
    m1.metric("처음 방식: 조각 수", f"{len(base):,}", help="고정 800자")
    m2.metric("최종 방식: 조각 수", f"{len(final):,}", help="용어·조 단위 + 950자")
    docs = sorted({c["source"] for c in final})
    default = docs.index("financial_glossary_readable.pdf") if "financial_glossary_readable.pdf" in docs else 0
    doc = st.selectbox("문서 고르기", docs, index=default)
    pages = sorted({c["page"] for c in final if c["source"] == doc})
    page = st.select_slider("쪽", options=pages, value=pages[min(2, len(pages) - 1)])
    left, right = st.columns(2)
    with left:
        st.markdown("#### 처음: 800자씩 기계적으로")
        for c in [c for c in base if c["source"] == doc and c["page"] == page]:
            st.markdown(chunk_html(c), unsafe_allow_html=True)
    with right:
        st.markdown("#### 최종: 의미 단위 / 950자")
        for c in [c for c in final if c["source"] == doc and c["page"] == page]:
            st.markdown(chunk_html(c), unsafe_allow_html=True)
    st.caption("용어집 6쪽을 열어 보세요. 처음 방식은 여러 용어가 한 조각에 섞이고, 최종 방식은 용어마다 한 조각입니다.")


# ---------------------------------------------------------------- 4. live
def show_chunks(units, picked_ids=None, limit=None):
    for i, u in enumerate(units[:limit] if limit else units, 1):
        picked = picked_ids is not None and u["chunk_id"] in picked_ids
        text = u["content"].replace("<", "&lt;").replace(">", "&gt;").replace("\n", " ")
        badge = "✅ 선택됨 · " if picked else ""
        st.markdown(f'<div class="chunk {"picked" if picked else ""}"><span class="tag">{badge}후보 {i} · {u["source"]} p.{u["page"]}</span><br>{text[:300]}{"…" if len(text) > 300 else ""}</div>',
                    unsafe_allow_html=True)


def cost_row(steps: dict):
    prices = load_prices()
    calls = steps.get("calls", [])
    usd = sum(call_usd(c, prices) for c in calls)
    sec = sum(c["seconds"] for c in calls)
    a, b, c = st.columns(3)
    a.metric("AI 호출 횟수", f"{sum(1 for x in calls if x['kind'] == 'llm')}번")
    b.metric("걸린 시간", f"{sec:.1f}초")
    c.metric("이 질문의 비용", f"{usd:.4f}달러")
    with st.expander("호출 내역 자세히"):
        st.dataframe(pd.DataFrame([{"단계": x["node"], "모델": x["model"], "입력 토큰": x["input_tokens"], "출력 토큰": x["output_tokens"], "초": x["seconds"]} for x in calls]),
                     hide_index=True, width="stretch")


EXAMPLES = ["POS001", "POS013", "NEG011", "NEG004", "ADD-IN08"]


def page_live():
    st.title("🔎 질문 하나를 따라가기")
    st.caption("실제로 AI를 호출합니다. 질문 하나에 5~15원 정도 듭니다(작은 모델 약 5원). 시험(test)용 질문은 쓰지 않습니다.")
    dev = {i["qid"]: i for i in load_golden(split="dev")}
    ex = {f"{q} · {dev[q]['question'][:46]}": q for q in EXAMPLES if q in dev}
    c1, c2 = st.columns([3, 2])
    with c1:
        pick = st.selectbox("예시 질문", ["(직접 입력)"] + list(ex))
    with c2:
        mode = st.radio("시스템", ["권장: 작은 모델 + rerank", "큰 모델 3.6 flash + rerank", "Agent 구조"], horizontal=False)
    item = dev[ex[pick]] if pick in ex else None
    question = st.text_input("질문", value=item["question"] if item else "", placeholder="예: 휴면성 증권계좌는 어떤 계좌인가요?")
    if not st.button("▶ 이 질문으로 실행", type="primary") or not question.strip():
        return
    env.setup()
    scope = "B"
    if mode.startswith("Agent"):
        res = system_of(CFG_AGENT).run(question, scope)
        st.markdown(f'### 결과 {pill(res["status"])}', unsafe_allow_html=True)
        st.write(res["answer"])
        st.subheader("Agent가 거친 판단")
        for d in res["steps"].get("decisions", []):
            st.write("•", {k: v for k, v in d.items()})
        st.write("사용한 검색어:", [s["query"] for s in res["searches"]])
        show_chunks(res["context"], {c["chunk_id"] for c in res["citations"]})
        cost_row(res["steps"])
    else:
        from rag.rag import format_answer, generate_answer, map_citations
        from rag.rerank import rerank
        system = system_of(CFG_LITE if mode.startswith("권장") else CFG_FLASH)
        cfg, steps = system.cfg, {"calls": []}
        st.markdown(f"모델: `{cfg['answer']['model']}`")
        with st.container(border=True):
            st.markdown('<span class="step">1</span><b>후보 15개 찾기</b> — 뜻이 비슷하고 단어가 겹치는 조각을 합쳐 점수순으로 꺼냈어요.', unsafe_allow_html=True)
            pool = system._retriever(scope).search(question, steps, k=cfg["retrieval"]["rerank_pool"])
            with st.expander("15개 후보 보기"):
                show_chunks(pool)
        with st.container(border=True):
            st.markdown('<span class="step">2</span><b>AI가 5개 고르기</b> — 15개를 읽고 답에 꼭 필요한 5개를 골랐어요.', unsafe_allow_html=True)
            picked = rerank(question, pool, cfg["retrieval"]["k"], cfg["answer"]["model"], cfg, steps)
            ids = {u["chunk_id"] for u in picked}
            moved = [i + 1 for i, u in enumerate(pool) if u["chunk_id"] in ids]
            st.write(f"고른 후보 번호: **{moved}**  (그냥 위에서 5개를 썼다면 [1, 2, 3, 4, 5])")
            show_chunks(pool, ids)
        with st.container(border=True):
            st.markdown('<span class="step">3</span><b>답하기</b> — 고른 5개만 보고 답을 썼어요.', unsafe_allow_html=True)
            out = generate_answer(question, picked, cfg, steps)
            citations, _ = map_citations(out.citations, picked)
            st.markdown(pill(out.status), unsafe_allow_html=True)
            st.write(format_answer(out.answer, citations))
        cost_row(steps)
    if item:
        with st.expander("정답과 비교해 보기"):
            st.write("**기준 답안**", item["target_answer"])
            st.write("**반드시 들어가야 할 말**", ", ".join(item["must_include"]))
            st.write("**정답이 있는 쪽**", [f"{t['file']} p.{t['page']}" for t in item["targets"]] or "문서에 없는 질문 (보류·되묻기·거절이 정답)")


# ---------------------------------------------------------------- 5. final test
def page_test():
    st.title("🏁 최종 시험 결과")
    st.write("시험 문항 90개(제공) + 직접 만든 20개 = **110문항**을 세 시스템에 한 번씩만 풀게 했습니다. 시험 문제로 시스템을 고치지 않았습니다.")
    systems = [("처음 시스템 (T1)", "test_000_baseline", "고정 800자 · 벡터 검색 · 작은 모델"),
               ("개선한 시스템 (T2)", "test_013_rerank_flash36", "구조 단위 · Hybrid · rerank · 큰 모델 3.6 flash"),
               ("Agent 구조 (T3)", "test_008b_agent950", "T2 + 스스로 점검하는 단계")]
    cols = st.columns(3)
    for col, (name, exp, what) in zip(cols, systems):
        s = summary_of(exp)
        with col:
            if not s:
                st.warning(f"{exp} 없음")
                continue
            st.markdown(f"#### {name}")
            st.markdown(f'<div class="big">{s["scores"]["correctness_mean"]:.3f}</div><div class="sub">정답 점수 (0~1)</div>', unsafe_allow_html=True)
            st.write("")
            st.progress(s["scores"]["fully_correct"], text=f"완전 정답 {s['scores']['fully_correct'] * 100:.0f}%")
            st.caption(what)
            st.write(f"문항당 비용 **{s['cost']['usd_per_question']:.4f}달러** · 느린 쪽 10% 응답시간 **{s['latency_s']['p90']:.1f}초**")
    st.divider()
    st.subheader("문제 종류별 점수")
    names = {"base_positive": "용어·약관 질문", "base_negative": "답하면 안 되는 질문", "life_guide": "생활 금융 가이드", "additional": "보고서·정책 자료", "self": "직접 만든 20문항"}
    rows = []
    for name, exp, _ in systems:
        s = summary_of(exp)
        if s:
            for k, v in s["by_set"].items():
                rows.append({"종류": f'{names.get(k, k)} ({v["n"]})', "시스템": name, "점수": v["correctness_mean"]})
    if rows:
        pivot = pd.DataFrame(rows).pivot(index="종류", columns="시스템", values="점수")
        st.bar_chart(pivot, height=340)
    st.markdown("""
    <div class="note"><b>해석</b><br>
    • 처음 → 개선: +0.17로 확실한 개선입니다(오차 범위 밖).<br>
    • 개선 → Agent: +0.01로 오차 범위 안이라 효과가 있다고 말할 수 없고, 비용만 1.4배입니다.<br>
    • 비용 때문에 권장 설정은 작은 모델(3.5 flash lite) + rerank입니다. 개발용 문항에서 0.894였고, <b>이 조합은 최종 시험에서 돌리지 않았습니다</b>(시험은 한 번뿐이라 이미 돌린 큰 모델 조합만 측정됨).<br>
    • 직접 만든 20문항은 전부 만점이라 변별력이 낮습니다. 너무 쉬웠다는 한계가 있습니다.</div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------- 6. per-question
def page_results():
    st.title("🧾 문항별 결과")
    exps = sorted(p.name for p in RESULTS.iterdir() if (p / "runs.jsonl").exists() and (p / "grades.jsonl").exists())
    names = {"dev_013b_rerank_lite_fix": "★ 권장 설정(개발용 90문항)", "dev_013_rerank_flash36_fix": "큰 모델 + rerank(개발용)",
             "test_013_rerank_flash36": "최종 시험 T2", "test_000_baseline": "최종 시험 T1", "test_008b_agent950": "최종 시험 T3"}
    exp = st.selectbox("어느 실행을 볼까요?", exps, index=exps.index("dev_013b_rerank_lite_fix") if "dev_013b_rerank_lite_fix" in exps else 0,
                       format_func=lambda e: names.get(e, e))
    runs = {r["qid"]: r for r in jsonl(str(RESULTS / exp / "runs.jsonl"))}
    grades = {g["qid"]: g for g in jsonl(str(RESULTS / exp / "grades.jsonl"))}
    gold = {i["qid"]: i for i in load_golden()}
    rows = [{"문항": q, "점수(0~2)": grades[q]["correctness"], "응답": STATUS.get(runs[q]["status"], (runs[q]["status"],))[0],
             "질문": runs[q]["question"][:70]} for q in grades if q in runs]
    df = pd.DataFrame(rows)
    only_bad = st.checkbox("만점이 아닌 문항만 보기", value=True)
    if only_bad:
        df = df[df["점수(0~2)"] < 2]
    st.write(f"{len(df)}문항 — 표에서 한 줄을 눌러 보세요.")
    sel = st.dataframe(df, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row")
    rws = sel.selection.rows
    qid = df.iloc[rws[0]]["문항"] if rws else (df.iloc[0]["문항"] if len(df) else None)
    if not qid:
        return
    r, g, i = runs[qid], grades[qid], gold.get(qid, {})
    st.divider()
    st.subheader(f"{qid}  {r['question']}")
    a, b = st.columns(2)
    with a:
        st.markdown(f"**시스템 답변** {pill(r['status'])}", unsafe_allow_html=True)
        st.write(r["answer"])
        st.markdown(f"**채점: {g['correctness']}점** — {g['reason']}")
    with b:
        st.markdown("**기준 답안**")
        st.write(i.get("target_answer", "-"))
        st.write("반드시 포함:", ", ".join(i.get("must_include") or []) or "-")
        st.write("정답 근거 쪽:", [f"{t['file']} p.{t['page']}" for t in i.get("targets", [])] or "문서에 없는 질문")
    with st.expander("답변에 넘긴 조각 5개 보기"):
        show_chunks(r["context"], {c["chunk_id"] for c in r.get("citations", [])})


# ---------------------------------------------------------------- 7. glossary
def page_glossary():
    st.title("📖 용어 설명")
    terms = {
        "RAG": "검색(Retrieval)으로 근거를 찾아 그것을 보고 답을 만드는(Generation) 방식. AI가 기억에 의존해 지어내는 것을 줄입니다.",
        "청킹": "긴 문서를 검색하기 좋은 작은 조각으로 자르는 일.",
        "임베딩": "문장의 뜻을 숫자 목록으로 바꾸는 일. 숫자가 가까우면 뜻이 비슷합니다.",
        "BM25": "질문과 같은 단어가 많이 들어 있는 조각을 높게 치는 전통적인 검색 방식.",
        "Hybrid 검색": "뜻 검색(임베딩)과 단어 검색(BM25)을 섞은 검색.",
        "rerank": "찾아 둔 후보를 AI가 다시 읽고 순서를 매겨 정말 필요한 것만 고르는 단계.",
        "Agent": "스스로 점검하고 다시 시도하는 단계를 더한 구조. 여기서는 근거가 부족하면 검색어를 고쳐 다시 찾습니다.",
        "dev / test": "dev는 설정을 고르는 데 쓴 개발용 문항, test는 마지막에 한 번만 푸는 시험 문항.",
        "정답 점수": "0점(틀림)·1점(일부)·2점(정답)을 평균해 0~1로 만든 값. 채점은 AI가 기준 답안과 비교해 합니다.",
        "노이즈": "같은 설정도 다시 돌리면 결과가 조금씩 달라지는 흔들림. 90문항 중 약 14문항의 답이 바뀝니다.",
        "답함 / 보류 / 되묻기 / 거절": "답할 근거가 있으면 답하고, 근거가 없으면 보류, 질문이 모호하면 되묻기, 해서는 안 되는 요청이면 거절합니다.",
    }
    for k, v in terms.items():
        with st.container(border=True):
            st.markdown(f"**{k}**")
            st.write(v)


PAGES = {"🏠 처음 보는 분을 위한 요약": page_overview, "🧭 전체 흐름": page_flow, "📈 점수가 오른 과정": page_history,
         "✂️ 글을 자른 방식": page_chunks, "🔎 질문 따라가기 (실시간)": page_live, "🏁 최종 시험 결과": page_test,
         "🧾 문항별 결과": page_results, "📖 용어 설명": page_glossary}
st.sidebar.title("📚 금융 문서 QA")
PAGES[st.sidebar.radio("메뉴", list(PAGES), label_visibility="collapsed")]()
