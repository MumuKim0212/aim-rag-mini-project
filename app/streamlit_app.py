"""Streamlit viewer for the whole project, written for people who have never seen it.

    streamlit run app/streamlit_app.py

Pages: overview, agent select, flow, score history, chunking, a live question run step by step, final test
(with the branch-agent comparison), per-question results, glossary. The live page calls the Gemini API (needs .env) and uses the indexes in
out/index (scripts/build_index.py). It runs dev questions or free text, never the test split.

Agent select (scripts/branch_agents.py): every app start looks up the newest agent committed on each origin
branch; checked agents run on the same dev questions with their own branch's code (a detached checkout under
out/agent_runs/). The final test page compares the finished runs and says in one line which agent leads.
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

CFG_LITE = "configs/013b-rerank-lite.yaml"      # final system (T4): gemini-3.5-flash-lite + prompt v4 + rerank
CFG_FLASH = "configs/013-rerank-flash36.yaml"   # T2: gemini-3.6-flash
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


# final comparison: provided test 90 + self-written set 41 = 131 questions (the first 20-question draft is dropped)
FINAL = {"T1": ["test_000_baseline", "test_000_baseline_self2"], "T2": ["test_013_rerank_flash36", "test_013_rerank_flash36_self2"],
         "T3": ["test_008b_agent950", "test_008b_agent950_self2"], "T4": ["test_013b_rerank_lite"]}


@st.cache_data
def final_rows(system: str) -> list[dict]:
    keep = {i["qid"] for i in load_golden() if i["set"] != "self"}
    rows = {}
    for exp in FINAL[system]:
        for m in jsonl(str(RESULTS / exp / "metrics.jsonl")):
            if m["qid"] in keep:
                rows[m["qid"]] = m
    return list(rows.values())


def final_stats(system: str) -> dict:
    r = final_rows(system)
    if not r:
        return {}
    lat = sorted(m["latency_s"] for m in r)
    return {"n": len(r), "score": sum(m["correctness"] for m in r) / len(r) / 2, "full": sum(m["correctness"] == 2 for m in r) / len(r),
            "usd": sum(m["usd"] for m in r) / len(r), "p90": lat[int(0.9 * (len(lat) - 1))]}


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
    f = {k: final_stats(k) for k in FINAL}
    m1, m2, m3, m4 = st.columns(4)
    if all(f.values()):
        m1.metric("처음 시스템 점수", f'{f["T1"]["score"]:.2f}', help="최종 시험(131문항) 정답 점수, 0~1")
        m2.metric("큰 모델 개선판 점수", f'{f["T2"]["score"]:.2f}', f'+{f["T2"]["score"] - f["T1"]["score"]:.2f}')
        m3.metric("★ 최종 시스템(작은 모델) 점수", f'{f["T4"]["score"]:.2f}', f'{f["T4"]["score"] - f["T2"]["score"]:+.2f} (큰 모델 대비)', delta_color="off")
        m4.metric("최종 시스템의 문항당 비용", f'{f["T4"]["usd"]:.4f}달러', f'큰 모델은 {f["T2"]["usd"]:.4f}달러', delta_color="off", help="최종 시험 131문항 평균")
    st.markdown('<div class="note"><b>읽는 법</b> 점수는 정답 0점·부분 1점·정답 2점을 평균해 0~1로 만든 값입니다. '
                '같은 설정을 다시 돌리면 90문항 중 약 14문항의 답이 달라지므로 0.02 정도의 차이는 의미가 없습니다.</div>',
                unsafe_allow_html=True)
    st.write("")
    st.info("왼쪽 메뉴에서 ‘질문 따라가기’를 열면 질문 하나가 위 5단계를 지나는 모습을 직접 볼 수 있습니다.")
    runs = view_runs()
    if not runs.empty:
        st.divider()
        st.subheader("🤖 실행한 agent 한눈에 비교")
        st.caption("🤖 에이전트 선택에서 실행한 agent마다 가장 최근 실행입니다. 번호는 사이드바 '볼 agent' 목록과 같습니다.")
        metrics, grades, common = side_by_side(runs)
        if metrics and len(metrics) >= 2:
            st.markdown(f'<div class="hero"><p><b>{verdict(metrics, grades, common)}</b></p></div>', unsafe_allow_html=True)


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
    a = current_agent()
    if a is not None:
        st.subheader(f"선택한 agent의 흐름: {a.name}")
        st.caption(f"브랜치 {a['branch']}(커밋 {a['commit']})의 코드로 LangGraph 그래프를 만들어 그린 그림입니다. 노드 이름만 한글로 바꿨습니다.")
        show_graph(a, width=520)
        st.divider()
        st.subheader("팀 최종 시스템의 전체 흐름")
    st.caption("글자 그대로 따라가면 됩니다. 점선 위쪽은 미리 한 번 해 두는 일, 아래쪽은 질문이 올 때마다 하는 일입니다.")
    st.graphviz_chart(PIPELINE, width="stretch")
    st.subheader("단계별로 자세히")
    steps = [
        ("글자 뽑기", "PDF에서 글자를 쪽마다 뽑습니다. 표·그래프는 그림이라 글자로 안 나오므로, AI가 그림을 읽고 글로 풀어 뒤에 붙입니다(한 번만, 약 1달러).", "PyMuPDF + gemini-3.8-flash"),
        ("조각으로 자르기", "용어집은 용어 하나, 약관은 조 하나를 한 조각으로 둡니다. 정의 하나가 반으로 잘리면 검색에서 놓치기 때문입니다. 가이드북과 보고서는 950자씩 자르고 앞뒤 119자를 겹칩니다. AI를 쓰지 않는 규칙입니다.", "구조 단위 + Recursive 950/119"),
        ("후보 15개 찾기", "‘뜻이 비슷한’ 조각(벡터 검색)과 ‘같은 단어가 있는’ 조각(BM25)을 절반씩 섞어 15개를 꺼냅니다. 한쪽만 쓰면 놓치는 것이 달랐기 때문입니다.", "gemini-embedding-2 + BM25"),
        ("AI가 5개 고르기 (rerank)", "15개를 AI가 읽고 질문에 답하는 데 필요한 5개만 고릅니다. 이 단계가 점수를 가장 크게 올렸습니다(근거를 찾는 비율 0.86 → 0.94).", "답변 모델이 직접 고름"),
        ("답하기", "고른 5개만 근거로 답합니다. 근거가 없으면 보류, 질문이 모호하면 되묻기, 해서는 안 되는 요청이면 거절합니다. 출처 번호는 코드가 파일·쪽으로 바꿔 붙입니다.", "gemini-3.5-flash-lite (최종) + 프롬프트 v4"),
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
            ("+ rerank (최종)", "dev_013b_rerank_lite_fix")]
    cols = st.columns(4)
    for col, (n, e) in zip(cols, lite):
        col.metric(n, f"{score(e):.3f}" if score(e) else "-")
    st.caption("큰 모델(3.6 flash) + rerank는 0.928, 작은 모델 + rerank는 0.894입니다. 답변 비용은 작은 모델이 약 40% 수준입니다(문항당 0.0035달러 대 0.0086달러).")
    runs = view_runs()
    if not runs.empty:
        st.subheader("실행한 agent의 점수 (dev)")
        a = current_agent()
        import altair as alt
        chart = runs.assign(선택=[a is not None and n == a.name for n in runs["이름"]])
        st.altair_chart(alt.Chart(chart).mark_bar().encode(
            x=alt.X("correctness:Q", title="정답 점수", scale=alt.Scale(domain=[0, 1])),
            y=alt.Y("이름:N", title=None, sort=None),
            color=alt.condition("datum.선택", alt.value("#f59e0b"), alt.value("#94a3b8")),
            tooltip=["이름", "correctness", "n", "usd_per_question", "p90"]), width="stretch")
        st.caption("주황색 = 사이드바에서 고른 agent. 실행마다 문항 수가 다를 수 있으니 정확한 비교는 🏁 최종 시험 결과의 비교표(공통 문항 기준)를 보세요. "
                   f"위의 단계별 점수는 팀 최종 체인의 dev 90문항 결과입니다.")
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
    a = current_agent()
    if a is not None:
        s = json.loads((Path(a["path"]) / "summary.json").read_text(encoding="utf-8"))
        ch, rt = s["config"]["chunking"], s["config"]["retrieval"]
        used = {}
        for r in jsonl(str(Path(a["path"]) / "runs.jsonl")):
            for u in r.get("context") or []:
                used[u["chunk_id"]] = u
        lens = [len(u["content"]) for u in used.values()]
        st.subheader(f"선택한 agent의 자르기·검색 설정: {a.name}")
        c = st.columns(4)
        c[0].metric("자르는 방식", ch.get("method", "-"))
        c[1].metric("조각 크기 / 겹침", f"{ch.get('chunk_size')} / {ch.get('chunk_overlap')}")
        c[2].metric("검색", f"{rt.get('method')} · k={rt.get('k')}", f"rerank 후보 {rt['rerank_pool']}" if rt.get("rerank_pool") else None,
                    delta_color="off")
        c[3].metric("답에 쓴 조각", f"{len(used)}개", f"평균 {sum(lens) // max(len(lens), 1)}자" if lens else None, delta_color="off")
        with st.expander("이 agent가 답에 실제로 쓴 조각 보기"):
            for u in list(used.values())[:30]:
                st.markdown(chunk_html(u) + f'<div class="sub">{u["source"]}</div>', unsafe_allow_html=True)
        st.divider()
        st.subheader("팀 최종 시스템의 자르기")
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
    a = current_agent()
    if a is not None:
        follow_agent(a)
        st.divider()
        st.subheader("팀 최종 시스템으로 실시간 실행")
    st.caption("실제로 AI를 호출합니다. 질문 하나에 5~15원 정도 듭니다(작은 모델 약 5원). 시험(test)용 질문은 쓰지 않습니다.")
    dev = {i["qid"]: i for i in load_golden(split="dev")}
    ex = {f"{q} · {dev[q]['question'][:46]}": q for q in EXAMPLES if q in dev}
    c1, c2 = st.columns([3, 2])
    with c1:
        pick = st.selectbox("예시 질문", ["(직접 입력)"] + list(ex))
    with c2:
        mode = st.radio("시스템", ["최종: 작은 모델 + rerank", "큰 모델 3.6 flash + rerank", "Agent 구조"], horizontal=False)
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
        system = system_of(CFG_LITE if mode.startswith("최종") else CFG_FLASH)
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
    st.write("시험 문항 90개(제공) + 직접 만든 41개 = **131문항**을 네 시스템에 한 번씩 풀게 했습니다. 시험 문제로 시스템을 고치지 않았습니다. 자세한 해석은 `submission/EVALUATION.md`에 있습니다.")
    systems = [("처음 시스템 (T1)", "T1", "고정 800자 · 벡터 검색 · 작은 모델"),
               ("큰 모델 개선판 (T2)", "T2", "구조 단위 · Hybrid · rerank · 큰 모델 3.6 flash"),
               ("Agent 구조 (T3)", "T3", "T2 + 스스로 점검하는 단계"),
               ("★ 최종 시스템 (T4)", "T4", "T2와 같은 구조 · 작은 모델 3.5 flash lite")]
    cols = st.columns(4)
    for col, (name, key, what) in zip(cols, systems):
        s = final_stats(key)
        with col:
            if not s:
                st.warning(f"{key} 결과 없음")
                continue
            st.markdown(f"#### {name}")
            st.markdown(f'<div class="big">{s["score"]:.3f}</div><div class="sub">정답 점수 (0~1)</div>', unsafe_allow_html=True)
            st.write("")
            st.progress(s["full"], text=f"완전 정답 {s['full'] * 100:.0f}%")
            st.caption(what)
            st.write(f"문항당 비용 **{s['usd']:.4f}달러** · 느린 쪽 10% 응답시간 **{s['p90']:.1f}초**")
    st.divider()
    st.subheader("문제 종류별 점수")
    gold = {i["qid"]: i["set"] for i in load_golden()}
    names = {"base_positive": "용어·약관 질문", "base_negative": "답하면 안 되는 질문", "life_guide": "생활 금융 가이드", "additional": "보고서·정책 자료", "self2": "직접 만든 문항"}
    rows = []
    for name, key, _ in systems:
        by = {}
        for m in final_rows(key):
            by.setdefault(gold[m["qid"]], []).append(m["correctness"] / 2)
        for k, v in by.items():
            rows.append({"종류": f"{names.get(k, k)} ({len(v)})", "시스템": name, "점수": sum(v) / len(v)})
    if rows:
        pivot = pd.DataFrame(rows).pivot(index="종류", columns="시스템", values="점수")
        st.bar_chart(pivot, height=340)
    st.markdown("""
    <div class="note"><b>해석</b><br>
    • 처음 → 개선(T2): +0.17로 확실한 개선입니다(오차 범위 밖).<br>
    • 개선 → Agent(T3): +0.03으로 오차 범위 안이라 효과가 있다고 말할 수 없고, 비용은 1.5배·느린 쪽 응답시간은 2.4배입니다.<br>
    • 큰 모델 → 작은 모델(T4): 점수는 0.03 낮지만(오차 범위 안) 비용은 0.4배, 응답은 2배 빠릅니다. 가격 때문에 T4를 최종으로 골랐습니다.<br>
    • T4는 최종 시험을 두 번째로 쓴 것입니다(처음엔 T1~T3만 돌림). 선택 이유는 가격이고 시험 점수가 아닙니다.</div>
    """, unsafe_allow_html=True)
    st.divider()
    agent_comparison()


# ---------------------------------------------------------------- 6. per-question
def page_results():
    st.title("🧾 문항별 결과")
    dirs = {p.name: p for p in RESULTS.iterdir() if (p / "runs.jsonl").exists() and (p / "grades.jsonl").exists()}
    agents = view_runs()
    for _, o in agents.iterrows():  # runs made on the agent select page, listed first under their numbered names
        dirs[o["이름"]] = Path(o["path"])
    exps = agents["이름"].tolist() + sorted(k for k in dirs if k not in set(agents.get("이름", [])))
    picked_agent = current_agent()
    names = {"test_013b_rerank_lite": "★ 최종 시험 T4 (최종 시스템)", "dev_013b_rerank_lite_fix": "최종 시스템(개발용 90문항)", "dev_013_rerank_flash36_fix": "큰 모델 + rerank(개발용)",
             "test_013_rerank_flash36": "최종 시험 T2", "test_000_baseline": "최종 시험 T1", "test_008b_agent950": "최종 시험 T3",
             "test_013_rerank_flash36_self2": "최종 시험 T2 (직접 만든 41문항)", "test_000_baseline_self2": "최종 시험 T1 (직접 만든 41문항)", "test_008b_agent950_self2": "최종 시험 T3 (직접 만든 41문항)"}
    default = picked_agent.name if picked_agent is not None else "test_013b_rerank_lite"
    exp = st.selectbox("어느 실행을 볼까요?", exps, index=exps.index(default) if default in exps else 0,
                       format_func=lambda e: names.get(e, e))
    runs = {r["qid"]: r for r in jsonl(str(dirs[exp] / "runs.jsonl"))}
    grades = {g["qid"]: g for g in jsonl(str(dirs[exp] / "grades.jsonl"))}
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
    with st.expander(f"답변에 넘긴 조각 {len(r['context'])}개 보기"):
        show_chunks(r["context"], {c["chunk_id"] for c in r.get("citations", [])})
    others = []
    for _, o in agents.iterrows():
        orun, ogr, _ = run_rows(o)
        if qid in orun:
            others.append({"agent": o["이름"], "점수": ogr.get(qid, {}).get("correctness"),
                           "응답": STATUS.get(orun[qid]["status"], (orun[qid]["status"],))[0], "답변": orun[qid]["answer"][:300]})
    if others:
        st.markdown("**같은 문항, 실행한 agent별 점수와 답**")
        st.dataframe(pd.DataFrame(others), hide_index=True, width="stretch")


# ---------------------------------------------------------------- 7. glossary
# ---------------------------------------------------------------- agent select + comparison (branch agents)
sys.path.insert(0, str(ROOT / "scripts"))
import importlib  # noqa: E402

import branch_agents as BA  # noqa: E402


def fresh(module):
    """Streamlit reruns this script but keeps imported modules: reload one whose file has changed, so an edit
    (or a git pull) takes effect without restarting the server."""
    mtime = Path(module.__file__).stat().st_mtime
    if getattr(module, "_loaded_mtime", None) != mtime:
        module = importlib.reload(module)
        module._loaded_mtime = mtime
    return module


BA = fresh(BA)

EST_USD = {"gemini-3.6-flash": 0.011, "gemini-3.8-flash": 0.011, "gemini-3.5-flash-lite": 0.004,
           "gemini-3.1-flash-lite": 0.004}  # agent USD per question on dev (results of cards 008/014), + judge ~0.0015


def refresh_agents(force: bool = False) -> list[dict]:
    """The newest agent committed on each origin branch, looked up once per browser session (each app start or
    new tab) and on demand. Falls back to the last fetched refs when GitHub cannot be reached."""
    if force or "branch_agents" not in st.session_state:
        with st.sidebar, st.spinner("GitHub 브랜치의 agent 조회 중…"):
            try:
                found, note = BA.scan(fetch=True), ""
            except Exception as e:
                found, note = BA.scan(fetch=False), f"GitHub에 연결하지 못해 마지막으로 받아 둔 브랜치 정보로 보여 줍니다 ({type(e).__name__})."
            st.session_state.branch_agents = BA.latest_per_branch(found)
            st.session_state.branch_agents_note = note
            st.session_state.branch_agents_at = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    return st.session_state.branch_agents


def page_agent_select():
    st.title("🤖 에이전트 선택")
    hero("브랜치마다 가장 최근에 올라온 agent를 같은 문항으로 돌려 비교합니다",
         "앱을 열 때마다 GitHub 저장소의 모든 브랜치를 조회해 목록을 최신으로 바꿉니다. 비교할 agent를 체크하고 실행하면 "
         "같은 dev 문항으로 답(QA 데이터)을 만들고 채점해서, 🏁 최종 시험 결과 페이지 아래쪽에 비교와 한 줄 요약이 나옵니다.")
    c1, c2 = st.columns([4, 1])
    if c2.button("🔄 목록 새로고침", width="stretch"):
        refresh_agents(force=True)
    agents = refresh_agents()
    c1.caption(f"마지막 조회: {st.session_state.get('branch_agents_at')} · 브랜치 {len(agents)}개, 브랜치마다 가장 최근 agent 1개")
    if st.session_state.get("branch_agents_note"):
        st.warning(st.session_state.branch_agents_note)

    same = pd.Series([a["same_code_id"] for a in agents]).value_counts()
    table = pd.DataFrame([{
        "선택": False, "agent": a["label"], "설정": a["config"].removesuffix(".yaml"), "올라온 시각": a["added_at"],
        "커밋": a["commit"], "작성자": a["author"], "종류": a["system"], "답변 모델": a["answer_model"],
        "같은 코드": f"{a['same_code_id']} ({same[a['same_code_id']]}개 같음)" if same[a["same_code_id"]] > 1 else a["same_code_id"],
        "설명": a["description"],
    } for a in agents])
    edited = st.data_editor(table, hide_index=True, width="stretch", key="agent_pick",
                            disabled=[c for c in table.columns if c != "선택"],
                            column_config={"선택": st.column_config.CheckboxColumn("선택", help="실행할 agent를 체크하세요 (여러 개 가능)")})
    st.caption("'올라온 시각'은 그 agent 설정이 브랜치에 마지막으로 커밋된 시각입니다. '같은 코드'가 같은 agent는 코드와 설정이 완전히 같아 "
               "점수 차이가 나도 잡음입니다.")

    chosen = [a for a, pick in zip(agents, edited["선택"]) if pick]
    c1, c2 = st.columns(2)
    limit = c1.select_slider("dev 문항 수 (앞에서부터, 모든 agent가 같은 문항)", [5, 10, 20, 30, 45, 90], value=10)
    sets = c2.multiselect("세트만 고르기 (비우면 전체)", ["base_positive", "base_negative", "life_guide", "additional"])
    est = sum((EST_USD.get(a["answer_model"], 0.011) + 0.0015) * limit for a in chosen)
    st.markdown(f'<div class="note">선택 <b>{len(chosen)}개</b> · 예상 비용 약 <b>{est:.2f} USD</b> (채점 포함) · '
                f'agent 하나에 {limit}문항이면 약 {max(1, limit // 8)}~{max(2, limit // 4)}분, 여러 개는 동시에 실행됩니다. '
                "test 문항은 쓰지 않습니다. 검색 인덱스가 이 PC에 없는 설정이면 처음 한 번 인덱스를 만듭니다(약 0.15 USD).</div>",
                unsafe_allow_html=True)
    if st.button(f"▶ 체크한 agent {len(chosen)}개 실행", type="primary", disabled=not chosen):
        for a in chosen:
            exp = BA.start(a, limit, ",".join(sets) or None)
            st.toast(f"시작: {a['label']} → {exp}")

    @st.fragment(run_every="5s")
    def job_status():
        jobs = BA.jobs()
        if not jobs:
            st.caption("아직 실행한 작업이 없습니다.")
            return
        st.subheader("실행 상태")
        steps = {"queued": "대기", "checkout": "브랜치 코드 준비", "index": "인덱스 확인", "run": "답변 생성",
                 "grade": "채점", "evaluate": "지표 계산", "done": "완료"}
        st.dataframe(pd.DataFrame([{
            "agent": (j.get("entry") or {}).get("label"),
            "상태": {"running": "⏳ 실행 중", "queued": "⏳ 대기 (동시 실행 3개까지)", "done": "✅ 완료", "failed": "❌ 실패",
                   "stopped": "⏹ 중단됨"}.get(j.get("status"), j.get("status")),
            "단계": steps.get(j.get("step"), j.get("step")),
            "진행": f"{j.get('done_questions', '')}/{j.get('limit') or 90}" if j.get("status") == "running" else "",
            "시작": j.get("started"), "실험": j["experiment"], "오류": j.get("error", ""),
        } for j in jobs[:20]]), width="stretch", hide_index=True)
        st.caption("5초마다 자동으로 갱신됩니다. 실행 로그: out/agent_runs/jobs/<실험>.log · 끝나면 🏁 최종 시험 결과 페이지에서 비교합니다.")

    job_status()


def agent_runs() -> pd.DataFrame:
    """Finished runs from the agent select page, newest first."""
    runs = [r for r in BA.read_log() if r["status"] == "done"]
    if not runs:
        return pd.DataFrame()
    df = pd.DataFrame(runs).sort_values("started", ascending=False)
    df["path"] = [str(BA.RESULTS / e) for e in df["experiment"]]
    df["표시"] = df["branch"] + " agent (" + df["config"].str.removesuffix(".yaml") + ") · " + df["started"].str[5:16]
    return df.reset_index(drop=True)


def verdict(metrics: dict, grades: dict, common: list) -> str:
    """One line: which agent leads, by how much, and whether the lead is beyond noise."""
    from evalkit.paired import compare
    order = sorted(metrics, key=lambda k: (-metrics[k]["정답 점수"], -metrics[k]["완전 정답률"], metrics[k]["USD/문항"]))
    lead, second = order[0], order[1]
    r = compare({q: grades[second][q] for q in common}, {q: grades[lead][q] for q in common}, max_score=2.0)
    net = len(r["b_better"]) - len(r["a_better"])
    if metrics[lead]["정답 점수"] == metrics[second]["정답 점수"] and net == 0:
        cheaper = min(metrics, key=lambda k: metrics[k]["USD/문항"])
        return (f"🤝 정답 점수 동률 ({metrics[lead]['정답 점수']:.3f}, {len(common)}문항) — 점수로는 우열이 없고, "
                f"비용이 가장 낮은 것은 {cheaper} ({metrics[cheaper]['USD/문항']:.4f} USD/문항)입니다.")
    changed = len(r["b_better"]) + len(r["a_better"])
    sure = r["ci95"][0] > 0 and changed > 14 * len(common) / 90
    tail = "차이가 잡음보다 커서 우세가 확실합니다." if sure else "다만 차이가 잡음 범위 안이라 확실한 우세는 아닙니다."
    return (f"🏆 {lead} 우세 — 정답 점수 {metrics[lead]['정답 점수']:.3f} vs 2위 {second} {metrics[second]['정답 점수']:.3f} "
            f"({len(common)}문항, 순증 {net:+d}, 95% 신뢰구간 [{r['ci95'][0]:+.3f}, {r['ci95'][1]:+.3f}]). {tail}")


def agent_comparison():
    st.subheader("🤖 브랜치 agent 비교 (dev 문항)")
    df = agent_runs()
    if df.empty:
        st.info("아직 비교할 agent 실행이 없습니다. 🤖 에이전트 선택 페이지에서 agent를 체크하고 실행하세요.")
        return
    newest = df.drop_duplicates(["branch", "config"])  # latest run of each branch agent
    picked = st.multiselect("비교할 실행 (기본: agent마다 가장 최근 실행)", df["표시"].tolist(), default=newest["표시"].tolist())
    if len(picked) < 2:
        st.info("두 개 이상 고르면 비교와 한 줄 요약이 나옵니다.")
        return
    sel = df.set_index("표시").loc[picked]
    grades = {k: {g["qid"]: g["correctness"] for g in jsonl(str(Path(sel.loc[k, "path"]) / "grades.jsonl"))} for k in picked}
    common = sorted(set.intersection(*(set(g) for g in grades.values())))
    if not common:
        st.warning("고른 실행들이 함께 푼 문항이 없습니다. 같은 문항 수로 실행한 것끼리 고르세요.")
        return
    metrics = {}
    for k in picked:
        m = {x["qid"]: x for x in jsonl(str(Path(sel.loc[k, "path"]) / "metrics.jsonl")) if x["qid"] in common}
        g, lat = grades[k], sorted(m[q]["latency_s"] for q in common)
        metrics[k] = {"정답 점수": sum(g[q] for q in common) / len(common) / 2,
                      "완전 정답률": sum(g[q] == 2 for q in common) / len(common),
                      "대응 일치율": sum(m[q].get("status_ok") or 0 for q in common) / len(common),
                      "출처 일치율": pd.Series([m[q].get("citation_on_target") for q in common]).mean(),
                      "USD/문항": sum(m[q]["usd"] for q in common) / len(common),
                      "LLM 호출/문항": sum(m[q]["n_llm_calls"] or 0 for q in common) / len(common),
                      "검색/문항": sum(m[q].get("n_searches") or 0 for q in common) / len(common),
                      "p90 초": lat[int(0.9 * (len(lat) - 1))]}

    st.markdown(f'<div class="hero"><p><b>{verdict(metrics, grades, common)}</b></p></div>', unsafe_allow_html=True)

    cmp_ = pd.DataFrame(metrics)
    best = {"정답 점수": max, "완전 정답률": max, "대응 일치율": max, "출처 일치율": max, "USD/문항": min, "LLM 호출/문항": min,
            "검색/문항": min, "p90 초": min}

    def mark(row):
        b = best[row.name](row)
        return ["background-color:#dcfce7; color:#14532d; font-weight:700" if v == b else "" for v in row]
    st.dataframe(cmp_.style.apply(mark, axis=1).format("{:.3f}"), width="stretch")
    st.caption(f"고른 실행들이 함께 푼 dev 문항 {len(common)}개로 계산했습니다. 초록색 = 그 지표에서 가장 좋은 값 "
               "(점수는 높을수록, 비용·호출·시간은 낮을수록). 위의 T1~T4 test 결과와 달리 dev 문항입니다.")

    from evalkit.paired import compare
    order = sorted(metrics, key=lambda k: -metrics[k]["정답 점수"])
    pair = []
    for k in order[1:]:
        r = compare({q: grades[k][q] for q in common}, {q: grades[order[0]][q] for q in common}, max_score=2.0)
        pair.append({"비교": f"{order[0]}  vs  {k}", "점수 차이": r["diff"], "1위 우세 / 열세 / 같음":
                     f"{len(r['b_better'])} / {len(r['a_better'])} / {r['same']}", "순증": len(r["b_better"]) - len(r["a_better"]),
                     "95% 신뢰구간": f"[{r['ci95'][0]:+.3f}, {r['ci95'][1]:+.3f}]",
                     "판정": "차이 있음" if r["ci95"][0] > 0 else "구별 안 됨"})
    st.markdown("**1위와 나머지 짝비교**")
    st.dataframe(pd.DataFrame(pair).style.format({"점수 차이": "{:+.3f}"}), width="stretch", hide_index=True)

    by_set = pd.DataFrame({k: sel.loc[k, "by_set"] or {} for k in picked})
    if len(by_set):
        st.markdown("**세트별 정답 점수** (각 실행 전체 문항 기준)")
        st.dataframe(by_set.style.format("{:.3f}", na_rep="–"), width="stretch")
    with st.expander("문항별 점수 (0~2)"):
        golden = {i["qid"]: i for i in load_golden()}
        grid = pd.DataFrame({k: {q: grades[k][q] for q in common} for k in picked})
        if st.checkbox("점수가 갈린 문항만", value=True):
            grid = grid[grid.nunique(axis=1) > 1]
        grid.insert(0, "질문", [golden.get(q, {}).get("question", "")[:50] for q in grid.index])
        st.dataframe(grid.style.background_gradient(cmap="RdYlGn", vmin=0, vmax=2, subset=picked), width="stretch")


# ---------------------------------------------------------------- the agent being viewed (sidebar, every page)
import agent as A  # noqa: E402  (repo root agent.py: Korean names for graph nodes, path of a run)

A = fresh(A)

VIEW_DEFAULT = "(팀 최종 결과 T1~T4)"


def view_runs() -> pd.DataFrame:
    """Latest finished run of each branch agent, numbered 1..N (the numbers stay the same on every page)."""
    df = agent_runs()
    if df.empty:
        return df
    df = df.drop_duplicates(["branch", "config"]).sort_values(["branch", "config"]).reset_index(drop=True)
    df["번호"] = range(1, len(df) + 1)
    df["이름"] = [f"{n}. {b} agent ({c.removesuffix('.yaml')})" for n, b, c in zip(df["번호"], df["branch"], df["config"])]
    return df


def current_agent():
    """The run picked in the sidebar, or None for the team's T1~T4 results."""
    df = view_runs()
    name = st.session_state.get("view_agent")
    if df.empty or name in (None, VIEW_DEFAULT) or name not in set(df["이름"]):
        return None
    return df.set_index("이름").loc[name]


def agent_picker():
    df = view_runs()
    st.sidebar.divider()
    st.sidebar.markdown("**🔎 볼 agent**")
    if df.empty:
        st.sidebar.caption("실행한 agent가 없습니다. 🤖 에이전트 선택에서 실행하면 여기서 골라 페이지마다 볼 수 있습니다.")
        return
    st.sidebar.selectbox("볼 agent", [VIEW_DEFAULT] + df["이름"].tolist(), key="view_agent", label_visibility="collapsed")
    a = current_agent()
    if a is not None:
        st.sidebar.markdown(f"정답 점수 **{a['correctness']:.3f}** · 완전 정답 {a['fully_correct']:.0%}<br>"
                            f"대응 일치 {a['status_ok']:.0%} · {a['n']:.0f}문항<br>"
                            f"{a['usd_per_question']:.4f} USD/문항 · p90 {a['p90']:.1f}초", unsafe_allow_html=True)
        st.sidebar.caption("페이지를 옮겨도 이 agent의 결과가 계속 표시됩니다.")


def agent_banner():
    a = current_agent()
    if a is None:
        if not view_runs().empty:
            st.caption("👈 사이드바 '볼 agent'에서 실행한 agent를 고르면 이 페이지에 그 agent의 결과가 함께 나옵니다.")
        return
    st.markdown(f'<div class="note">지금 보는 agent: <b>{a.name}</b> · 커밋 {a["commit"]} · 정답 점수 <b>{a["correctness"]:.3f}</b> '
                f'({a["n"]:.0f}문항, dev) · {a["usd_per_question"]:.4f} USD/문항 · 실행 {a["started"][5:16]}</div>',
                unsafe_allow_html=True)


def side_by_side(df: pd.DataFrame):
    """All viewed runs as numbered columns on their common questions, the best value per metric in green."""
    grades = {n: {g["qid"]: g["correctness"] for g in jsonl(str(Path(p) / "grades.jsonl"))} for n, p in zip(df["이름"], df["path"])}
    common = sorted(set.intersection(*(set(g) for g in grades.values())))
    if not common:
        st.warning("실행들이 함께 푼 문항이 없습니다. 같은 문항 수로 실행한 것끼리 비교하세요.")
        return None, grades, common
    metrics = {}
    for n, p in zip(df["이름"], df["path"]):
        m = {x["qid"]: x for x in jsonl(str(Path(p) / "metrics.jsonl")) if x["qid"] in common}
        g, lat = grades[n], sorted(m[q]["latency_s"] for q in common)
        metrics[n] = {"정답 점수": sum(g[q] for q in common) / len(common) / 2,
                      "완전 정답률": sum(g[q] == 2 for q in common) / len(common),
                      "대응 일치율": sum(m[q].get("status_ok") or 0 for q in common) / len(common),
                      "출처 일치율": pd.Series([m[q].get("citation_on_target") for q in common]).mean(),
                      "USD/문항": sum(m[q]["usd"] for q in common) / len(common),
                      "LLM 호출/문항": sum(m[q]["n_llm_calls"] or 0 for q in common) / len(common),
                      "검색/문항": sum(m[q].get("n_searches") or 0 for q in common) / len(common),
                      "p90 초": lat[int(0.9 * (len(lat) - 1))]}
    best = {"정답 점수": max, "완전 정답률": max, "대응 일치율": max, "출처 일치율": max, "USD/문항": min, "LLM 호출/문항": min,
            "검색/문항": min, "p90 초": min}

    def mark(row):
        b = best[row.name](row)
        return ["background-color:#dcfce7; color:#14532d; font-weight:700" if v == b else "" for v in row]
    st.dataframe(pd.DataFrame(metrics).style.apply(mark, axis=1).format("{:.3f}"), width="stretch")
    st.caption(f"함께 푼 dev 문항 {len(common)}개 기준 · 초록색 = 그 지표에서 가장 좋은 값 (점수는 높을수록, 비용·호출·시간은 낮을수록)")
    return metrics, grades, common


@st.cache_data(show_spinner="그 브랜치 코드에서 LangGraph 흐름도를 꺼내는 중…")
def graph_text(sha: str, config: str) -> str:
    return BA.graph_of(sha, config)


@st.cache_data(show_spinner=False)
def mermaid_png(text: str):
    try:
        from langchain_core.runnables.graph_mermaid import draw_mermaid_png
        return draw_mermaid_png(text)
    except Exception:
        return None


def show_graph(a, path: list[str] | None = None, width: int | None = None):
    try:
        text = A.translate(graph_text(BA.sha_of(a), a["config"]), path)
    except Exception as e:
        st.warning(f"흐름도를 꺼내지 못했습니다: {e}")
        return
    png = mermaid_png(text)
    if png:
        st.image(png, width=width or "content")
    else:
        st.code(text, language="text")


def follow_agent(a):
    """Question-following page for the agent picked in the sidebar: its stored answer and path, every agent's
    answer to the same question, and a live run with that branch's code."""
    st.subheader(f"선택한 agent로 따라가기: {a.name}")
    runs, grades, metrics = run_rows(a)
    gold = {i["qid"]: i for i in load_golden()}
    qids = sorted(runs)
    qid = st.selectbox("이 agent가 푼 문항", qids, format_func=lambda q: f"{q} · {grades.get(q, {}).get('correctness', '-')}점 · {runs[q]['question'][:50]}")
    r, g, m, item = runs[qid], grades.get(qid, {}), metrics.get(qid, {}), gold.get(qid, {})
    left, right = st.columns([3, 2])
    with left:
        st.markdown(f"**질문** {r['question']}")
        st.markdown(f"**답변** {pill(r['status'])} · 채점 **{g.get('correctness', '-')}점**", unsafe_allow_html=True)
        st.write(r["answer"])
        st.caption(f"채점 이유: {g.get('reason', '-')}")
        st.markdown(f"LLM {r.get('n_llm_calls')}회 · 검색 {r.get('n_searches')}회 · {r.get('latency_s', 0):.1f}초 · "
                    f"{m.get('usd', 0):.4f} USD")
        st.markdown("**진행 과정**")
        st.text("\n".join(A.describe(r)) or "(판단 기록 없음)")
        with st.expander("기준 답안"):
            st.write(item.get("target_answer", "-"))
            st.write("정답 근거 쪽:", [f"{t['file']} p.{t['page']}" for t in item.get("targets", [])] or "문서에 없는 질문")
    with right:
        st.markdown("**지나간 노드 (노란색)**")
        show_graph(a, A.visited_path(r.get("steps") or {}), width=360)
    with st.expander("답변에 넘긴 조각 보기"):
        show_chunks(r["context"], {c["chunk_id"] for c in r.get("citations", [])})

    st.markdown("**같은 문항, agent별 답 한눈에 보기**")
    rows = []
    for _, o in view_runs().iterrows():
        orun, ogr, _ = run_rows(o)
        if qid in orun:
            rows.append({"agent": o["이름"], "점수": ogr.get(qid, {}).get("correctness"),
                         "응답": STATUS.get(orun[qid]["status"], (orun[qid]["status"],))[0],
                         "LLM 호출": orun[qid].get("n_llm_calls"), "검색": orun[qid].get("n_searches"),
                         "답변": orun[qid]["answer"][:300]})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    with st.expander("▶ 이 agent로 실시간 실행 (그 브랜치 코드로 API 호출, 약 0.01~0.02 USD)"):
        q = st.text_input("질문", value=r["question"], key="follow_q")
        scope = st.radio("검색 범위", ["B", "A"], horizontal=True, key="follow_scope",
                         format_func=lambda s: {"A": "A (용어집+약관)", "B": "B (전체 23개)"}[s])
        if st.button("실행", key="follow_run"):
            with st.spinner("그 브랜치 코드로 실행 중… (10~40초)"):
                try:
                    res = BA.live_run(BA.sha_of(a), a["config"], q, scope)
                except Exception as e:
                    st.error(f"실행 실패: {e}")
                    return
            st.markdown(f"{pill(res['status'])} · LLM {res.get('n_llm_calls')}회 · 검색 {res.get('n_searches')}회 · "
                        f"{res.get('latency_s')}초", unsafe_allow_html=True)
            st.write(res["answer"])
            st.text("\n".join(A.describe(res)))
            show_graph(a, A.visited_path(res.get("steps") or {}), width=360)


def run_rows(a) -> tuple[dict, dict, dict]:
    p = Path(a["path"])
    return ({r["qid"]: r for r in jsonl(str(p / "runs.jsonl"))}, {g["qid"]: g for g in jsonl(str(p / "grades.jsonl"))},
            {m["qid"]: m for m in jsonl(str(p / "metrics.jsonl"))})


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


PAGES = {"🏠 처음 보는 분을 위한 요약": page_overview, "🤖 에이전트 선택": page_agent_select, "🧭 전체 흐름": page_flow,
         "📈 점수가 오른 과정": page_history, "✂️ 글을 자른 방식": page_chunks, "🔎 질문 따라가기 (실시간)": page_live,
         "🏁 최종 시험 결과": page_test, "🧾 문항별 결과": page_results, "📖 용어 설명": page_glossary}
st.sidebar.title("📚 금융 문서 QA")
refresh_agents()  # every app start / new browser session looks up the agents committed on the branches
page = st.sidebar.radio("메뉴", list(PAGES), label_visibility="collapsed")
agent_picker()
if page not in ("🤖 에이전트 선택", "📖 용어 설명"):
    agent_banner()
PAGES[page]()
