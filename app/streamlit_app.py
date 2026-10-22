"""Streamlit viewer for the whole project, written for people who have never seen it.

    streamlit run app/streamlit_app.py

Pages: overview, how it works, try it yourself (live run with the node path drawn as it happens), score history,
chunking, final test, per-question results, lessons, glossary. The live page calls the Gemini API (needs .env) and
uses the indexes in out/index (scripts/build_index.py). It runs dev questions or free text, never the test split.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from rag import env  # noqa: E402
from rag.config import load_config  # noqa: E402
from rag.cost import call_usd, load_prices  # noqa: E402
from rag.golden import load_golden, scope_of  # noqa: E402
from rag.retrieval import index_dir  # noqa: E402

CFG_LITE = "configs/013b-rerank-lite.yaml"      # final system (T4): gemini-3.5-flash-lite + prompt v4 + rerank
CFG_FLASH = "configs/013-rerank-flash36.yaml"   # T2: gemini-3.6-flash
CFG_AGENT = "configs/008b-agent-950.yaml"       # T3
CFG_AGENT_V2 = "configs/014-agent-v2.yaml"      # card 014, not adopted
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
.step {display:inline-block; min-width: 28px; height: 28px; line-height: 28px; text-align:center; border-radius: 14px;
       background:#4f46e5; color:#fff; font-weight:700; margin-right:8px; padding: 0 6px;}
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
.legend span {display:inline-block; padding:2px 10px; border-radius:8px; margin-right:6px; font-size:0.85rem; color:#0f172a;}
</style>
""", unsafe_allow_html=True)

STATUS = {"answered": ("✅ 답했어요", "p-ok"), "abstained": ("⏸ 근거가 없어 보류했어요", "p-hold"),
          "clarify": ("❓ 정보를 더 물어봤어요", "p-ask"), "refused": ("⛔ 해서는 안 되는 요청이라 거절했어요", "p-no")}


def pill(status: str) -> str:
    text, css = STATUS.get(status, (status, "p-hold"))
    return f'<span class="pill {css}">{text}</span>'


def card(title: str, body: str):
    st.markdown(f'<div class="card"><h4>{title}</h4><p>{body}</p></div>', unsafe_allow_html=True)


def hero(title: str, text: str):
    st.markdown(f'<div class="hero"><h2>{title}</h2><p>{text}</p></div>', unsafe_allow_html=True)


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


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
         "질문하면 문서에서 관련 부분을 찾아 그것만 보고 답하고, 어느 문서 몇 쪽인지 출처를 붙입니다. "
         "근거가 없으면 지어내지 않고 ‘문서에 없어요’라고 말합니다.")
    st.subheader("쉽게 비유하면: 도서관 사서")
    cols = st.columns(5)
    items = [("1. 책 정리", "PDF를 쪽마다 글자로 바꿉니다. 표·그래프는 AI가 그림을 보고 글로 풀어 적습니다."),
             ("2. 카드 만들기", "글을 찾기 좋은 작은 조각으로 자릅니다. 용어집은 용어 하나, 약관은 조항 하나가 한 조각입니다."),
             ("3. 후보 찾기", "질문과 뜻이 비슷한 조각과 같은 단어가 들어 있는 조각을 합쳐 15개를 꺼냅니다."),
             ("4. 사서가 다시 고르기", "AI가 15개를 읽고 정말 필요한 5개만 고릅니다."),
             ("5. 답하기", "고른 5개만 보고 답을 쓰고, 출처(파일·쪽)를 붙입니다.")]
    for col, (t, b) in zip(cols, items):
        with col:
            card(t, b)
    st.divider()
    st.subheader("결과 한눈에 보기 (시험 문제 131개)")
    f = {k: final_stats(k) for k in FINAL}
    m1, m2, m3, m4 = st.columns(4)
    if all(f.values()):
        m1.metric("처음 만든 시스템", f'{f["T1"]["score"]:.2f}', help="정답 점수, 0~1. 1에 가까울수록 정답")
        m2.metric("개선한 시스템 (큰 AI)", f'{f["T2"]["score"]:.2f}', f'+{f["T2"]["score"] - f["T1"]["score"]:.2f}')
        m3.metric("스스로 점검하는 Agent (큰 AI)", f'{f["T3"]["score"]:.2f}', f'{f["T3"]["score"] - f["T2"]["score"]:+.2f} (개선판 대비)', delta_color="off")
        m4.metric("★ 최종 선택 (작은 AI)", f'{f["T4"]["score"]:.2f}', f'질문당 {f["T4"]["usd"]:.4f}달러 (큰 AI {f["T2"]["usd"]:.4f})', delta_color="off")
    st.markdown('<div class="note"><b>읽는 법</b> 점수는 틀림 0점·일부 맞음 1점·정답 2점을 평균해 0~1로 바꾼 값입니다. '
                '같은 설정을 다시 돌려도 90문항 중 약 14문항의 답이 달라지므로, 0.03 정도의 차이는 운에 따른 흔들림일 수 있습니다.</div>',
                unsafe_allow_html=True)
    st.write("")
    st.subheader("세 줄 요약")
    st.markdown("""
1. **점수를 올린 건 ‘찾는 방법’을 고친 일**이었습니다. 용어·조항 단위로 자르기, AI가 후보를 다시 고르기가 가장 컸습니다.
2. **스스로 점검하는 Agent는 조금 나았지만 운의 범위 안**이었고, 비용은 1.5배였습니다. 답을 검사해 고쳐 쓰게 한 개선판(v2)도 효과가 없었습니다.
3. **최종으로는 작은 AI를 골랐습니다.** 점수는 큰 AI보다 0.03 낮지만 비용은 40%, 속도는 2배입니다.
""")
    st.info("왼쪽 메뉴의 **‘💬 직접 검색해서 써보기’**에서 질문을 넣으면, 질문이 어떤 단계를 어떤 순서로 지나가는지 그림으로 볼 수 있습니다.")


# ---------------------------------------------------------------- flow drawing (shared by the flow and live pages)
def circled(i: int) -> str:
    return chr(0x2460 + i - 1) if 1 <= i <= 20 else f"({i})"


AGENT_NODES = [("classify", "질문 종류 판단\n(문서로 답할 질문? 정보가 더 필요? 부적절?)"),
               ("retrieve", "문서 찾기\n(후보 15개 → AI가 5개 고름)"),
               ("grade", "찾은 근거로\n답할 수 있나?"),
               ("rewrite", "검색어 바꿔서\n다시 찾기 (최대 2번)"),
               ("generate", "답 쓰기"),
               ("cite_check", "출처 번호가\n맞는지 확인")]
AGENT_EDGES = [("start", "classify", ""), ("classify", "retrieve", ""), ("retrieve", "grade", ""),
               ("grade", "rewrite", "부족해요"), ("rewrite", "retrieve", ""), ("grade", "generate", "충분해요\n(또는 3번 다 찾음)"),
               ("generate", "cite_check", ""), ("cite_check", "generate", "번호가 틀림\n(1번 다시)"), ("cite_check", "end", "통과")]
V2_NODES = [("check", "답 검사 (다른 AI)\n빠진 내용? 없는 숫자?")]
V2_EDGES = [("cite_check", "check", "통과 (첫 답)"), ("check", "generate", "고칠 점 있음\n(1번만 고쳐 쓰기)"), ("check", "end", "문제 없음")]
RAG_NODES = [("search", "후보 15개 찾기\n(뜻 비슷 + 단어 일치)"), ("rerank", "AI가 5개 고르기"), ("generate", "답 쓰기 + 출처 붙이기")]
RAG_EDGES = [("start", "search", ""), ("search", "rerank", ""), ("rerank", "generate", ""), ("generate", "end", "")]


def flow_dot(nodes, edges, path=None, current=None, rankdir="TB") -> str:
    """Graphviz DOT for a flow. `path` = node ids in the order visited (from "start"); taken edges get their step numbers."""
    path = path or []
    seen, taken = set(path), defaultdict(list)
    for i, pair in enumerate(zip(path, path[1:]), 1):
        taken[pair].append(i)
    out = [f'digraph F {{ graph [rankdir={rankdir}, pad=0.3, nodesep=0.45, ranksep=0.5, fontname="Helvetica"];',
           'node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=14, margin="0.2,0.1"];',
           'edge [fontname="Helvetica", fontsize=12];']
    for nid, label, shape in [("start", "질문", "oval"), ("end", "끝", "oval")] + [(n, l, "box") for n, l in nodes]:
        if nid == current:
            style = 'fillcolor="#fde68a", color="#d97706", penwidth=3, fontcolor="#0f172a"'
        elif nid in seen or (not path and nid in ("start", "end")):
            style = 'fillcolor="#bbf7d0", color="#16a34a", penwidth=2, fontcolor="#0f172a"'
        elif path:
            style = 'fillcolor="#f1f5f9", color="#cbd5e1", fontcolor="#94a3b8"'
        else:
            style = 'fillcolor="#e0e7ff", color="#94a3b8", fontcolor="#0f172a"'
        out.append(f'"{nid}" [label="{label}", shape={shape}, {style}];')
    for a, b, label in edges:
        steps = taken.get((a, b))
        if steps:
            text = (label + "\\n" if label else "") + " ".join(circled(i) for i in steps)
            out.append(f'"{a}" -> "{b}" [label="{text}", color="#16a34a", fontcolor="#166534", penwidth=3];')
        else:
            color = "#cbd5e1" if path else "#94a3b8"
            out.append(f'"{a}" -> "{b}" [label="{label}", color="{color}", fontcolor="#94a3b8", style={"dashed" if path else "solid"}];')
    out.append("}")
    return "\n".join(out)


def dot_text(s: str) -> str:
    return s.replace("\n", "\\n")


def flow_chart(nodes, edges, path=None, current=None, rankdir="TB") -> str:
    return flow_dot([(n, dot_text(l)) for n, l in nodes], [(a, b, dot_text(l)) for a, b, l in edges], path, current, rankdir)


LEGEND = ('<div class="legend"><span style="background:#bbf7d0">지나간 칸</span><span style="background:#fde68a">방금 지난 칸</span>'
          '<span style="background:#f1f5f9;color:#94a3b8">안 지난 칸</span> 초록 화살표의 ①②③은 지나간 순서입니다.</div>')


# ---------------------------------------------------------------- 1. how it works
PIPELINE = """
digraph G {
  graph [rankdir=LR, fontname="Helvetica", fontsize=16, fontcolor="#64748b", nodesep=0.35, ranksep=0.5, pad=0.3];
  node [shape=box, style="rounded,filled", fontname="Helvetica", fontcolor="#0f172a", fontsize=15, margin="0.2,0.12", color="#94a3b8"];
  edge [color="#94a3b8", penwidth=1.6, arrowsize=0.9];
  subgraph cluster_prep { label="① 준비 (한 번만 합니다)"; style="rounded,dashed"; color="#94a3b8"; fontcolor="#94a3b8"; fontsize=17;
    pdf [label="PDF 23개", fillcolor="#e0e7ff"];
    ext [label="쪽별 글자 뽑기\\n표·그래프는 AI가 글로 풀이", fillcolor="#e0e7ff"];
    chunk [label="조각으로 자르기\\n용어집=용어 하나\\n약관=조항 하나\\n나머지=950자", fillcolor="#e0e7ff"];
    emb [label="뜻을 숫자로 바꾸기", fillcolor="#e0e7ff"];
    store [label="저장소\\n(뜻 색인 + 단어 색인)", fillcolor="#fde68a"];
    pdf -> ext -> chunk -> emb -> store; }
  subgraph cluster_ask { label="② 질문이 들어오면"; style="rounded,dashed"; color="#94a3b8"; fontcolor="#94a3b8"; fontsize=17;
    q [label="질문", shape=oval, fillcolor="#bbf7d0"];
    hy [label="후보 15개 찾기\\n(뜻 비슷 + 단어 일치)", fillcolor="#bfdbfe"];
    rr [label="AI가 5개 고르기", fillcolor="#fcd34d"];
    ans [label="근거만 보고 답하기\\n+ 출처 붙이기", fillcolor="#bfdbfe"];
    out [label="답변\\n(답함·보류·되묻기·거절)", shape=oval, fillcolor="#bbf7d0"];
    q -> hy -> rr -> ans -> out; }
  store -> hy [style=dashed];
}
"""


def page_flow():
    st.title("🧭 어떻게 동작하나")
    st.caption("왼쪽에서 오른쪽으로 따라가면 됩니다. 위쪽 상자는 미리 한 번 해 두는 일, 아래쪽 상자는 질문이 올 때마다 하는 일입니다.")
    st.graphviz_chart(PIPELINE, width="stretch")
    st.subheader("단계별로 자세히")
    steps = [
        ("글자 뽑기", "PDF에서 글자를 쪽마다 뽑습니다. 표·그래프는 그림이라 글자로 안 나오므로, AI가 그림을 읽고 글로 풀어 뒤에 붙입니다. 한 번만 하고, 약 1달러 들었습니다.", "PyMuPDF + gemini-3.8-flash"),
        ("조각으로 자르기", "용어집은 용어 하나, 약관은 조항 하나를 한 조각으로 둡니다. 정의 하나가 반으로 잘리면 찾을 때 놓치기 때문입니다. 가이드북과 보고서는 950자씩 자르고 앞뒤 119자를 겹칩니다.", "구조 단위 청킹 + Recursive 950/119"),
        ("후보 15개 찾기", "‘뜻이 비슷한’ 조각(벡터 검색)과 ‘같은 단어가 있는’ 조각(BM25)을 반반 섞어 15개를 꺼냅니다. 한쪽만 쓰면 놓치는 것이 서로 달랐습니다.", "Hybrid 검색: gemini-embedding-2 + BM25(한국어 형태소 분석기 Kiwi)"),
        ("AI가 5개 고르기", "15개를 AI가 읽고 답에 필요한 5개만 고릅니다. 이 단계가 점수를 가장 확실하게 올렸습니다(근거를 찾는 비율 0.86 → 0.94).", "LLM rerank (답변 AI가 직접 고름)"),
        ("답하기", "고른 5개만 근거로 답합니다. 근거가 없으면 보류, 정보가 모자라면 되묻기, 해서는 안 되는 요청이면 거절합니다. 출처 번호는 코드가 파일·쪽으로 바꿔 붙입니다.", "gemini-3.5-flash-lite (최종) + 답변 규칙 v4"),
    ]
    for i, (t, body, tech) in enumerate(steps, 1):
        with st.expander(f"{i}. {t}", expanded=(i == 4)):
            st.write(body)
            st.caption(f"실제로 쓴 기술: {tech}")
    st.divider()
    st.subheader("비교용: Agent 구조 (T3, 최종 시스템 아님)")
    st.write("과제의 ‘기본 RAG 대 Agent’ 비교를 위해, 위의 찾기·답하기에 **‘판단하는 칸’**을 더한 버전입니다. "
             "질문 종류를 먼저 보고, 찾은 근거가 부족하면 검색어를 바꿔 다시 찾습니다. **최종 시스템(T4)은 위의 3칸뿐입니다.**")
    left, right = st.columns([3, 2])
    with left:
        st.graphviz_chart(flow_chart(AGENT_NODES, AGENT_EDGES), width="stretch")
    with right:
        st.markdown("""
**칸(노드)마다 하는 일**
- **질문 종류 판단**: 문서를 찾아 답할 질문인지, 내 상황 정보가 더 필요한지, 해서는 안 되는 요청인지 봅니다.
- **문서 찾기**: 위의 ‘후보 15개 → AI가 5개’와 같습니다.
- **답할 수 있나?**: 찾은 조각만으로 답이 되는지 AI가 판단합니다.
- **다시 찾기**: 부족하면 무엇이 부족한지 보고 검색어를 새로 씁니다. 최대 2번(총 3번 찾기).
- **답 쓰기 / 출처 확인**: 답을 쓰고, 출처 번호가 실제로 찾은 조각을 가리키는지 코드로 확인합니다.

**끝나는 조건**: 다시 찾기 최대 2번(총 3번 찾기), 출처 다시 쓰기 최대 1번. 그래서 끝없이 돌지 않습니다.
""")
    st.markdown('<div class="note"><b>결과</b> Agent(T3)는 개선판(T2)보다 조금 나았지만(시험 0.916 대 0.889) 운의 범위 안이었고 비용은 1.5배였습니다. '
                '그래서 최종으로는 쓰지 않았습니다. 시험 뒤에 ‘답 검사’ 칸을 더한 Agent v2도 해 봤지만 효과가 없어 버렸습니다(‘💡 배운 점’).</div>',
                unsafe_allow_html=True)


# ---------------------------------------------------------------- 2. try it yourself (live)
TYPE_TEXT = {"document": "문서를 찾아 답할 수 있는 질문", "needs_info": "내 계좌·계약 같은 정보가 더 있어야 답할 수 있는 질문",
             "inappropriate": "해서는 안 되는 요청 (상품 추천, 수익 예측 등)", "injection": "규칙을 어기라는 지시가 섞인 질문"}

EXAMPLES = [("POS001", "보통 질문"), ("NEG037", "다시 찾기가 일어나는 질문"), ("NEG013", "정보를 더 물어봐야 하는 질문"),
            ("NEG004", "거절해야 하는 질문"), ("POS045", "(버린 시도 v2용) 답 검사 후 고쳐 쓴 질문")]

SYSTEMS = {"★ T4 최종 시스템 (작은 AI, 칸 3개)": ("rag", CFG_LITE), "T2 개선판 (큰 AI, 칸 3개) · 비교용": ("rag", CFG_FLASH),
           "T3 Agent (스스로 점검, 큰 AI) · 비교용": ("agent", CFG_AGENT), "Agent v2 (+ 답 검사 칸) · 버린 시도": ("agent", CFG_AGENT_V2)}


def show_chunks(units, picked_ids=None, limit=None):
    for i, u in enumerate(units[:limit] if limit else units, 1):
        picked = picked_ids is not None and u["chunk_id"] in picked_ids
        text = esc(u["content"]).replace("\n", " ")
        badge = "✅ 고름 · " if picked else ""
        st.markdown(f'<div class="chunk {"picked" if picked else ""}"><span class="tag">{badge}{i}번 · {esc(u["source"])} p.{u["page"]}</span><br>{text[:300]}{"…" if len(text) > 300 else ""}</div>',
                    unsafe_allow_html=True)


def cost_row(steps: dict, searches: int):
    prices = load_prices()
    calls = steps.get("calls", [])
    usd = sum(call_usd(c, prices) for c in calls)
    sec = sum(c["seconds"] for c in calls)
    a, b, c, d = st.columns(4)
    a.metric("AI를 부른 횟수", f"{sum(1 for x in calls if x['kind'] == 'llm')}번")
    b.metric("문서를 찾은 횟수", f"{searches}번")
    c.metric("걸린 시간", f"{sec:.1f}초")
    d.metric("이 질문의 비용", f"{usd:.4f}달러")
    with st.expander("AI 호출 내역 자세히"):
        st.dataframe(pd.DataFrame([{"칸": x["node"], "모델": x["model"], "입력 토큰": x["input_tokens"], "출력 토큰": x["output_tokens"], "초": x["seconds"]} for x in calls]),
                     hide_index=True, width="stretch")


def step_box(n: int, title: str):
    box = st.container(border=True)
    box.markdown(f'<span class="step">{circled(n)}</span><b>{title}</b>', unsafe_allow_html=True)
    return box


def last_decision(steps: dict, node: str) -> dict:
    return next((d for d in reversed(steps.get("decisions", [])) if d["node"] == node), {})


def describe(node: str, n: int, state: dict, steps: dict):
    """One plain-language card for a finished node."""
    if node == "classify":
        d = last_decision(steps, "classify")
        box = step_box(n, "질문 종류 판단")
        box.write(f"→ **{TYPE_TEXT.get(d.get('type'), d.get('type'))}** 으로 봤어요.")
        box.caption(f"AI가 쓴 이유: {d.get('reason', '')}")
    elif node == "retrieve":
        search = state["searches"][-1]
        k = len(state["searches"])
        box = step_box(n, f"문서 찾기 ({k}번째)")
        box.write(f"검색어: **{search['query']}**")
        box.write("후보 15개를 꺼내 AI가 5개를 골랐어요." + (" 새로 찾은 조각만 앞의 것에 더했어요." if k > 1 else ""))
        found = {u["chunk_id"]: u for u in state["units"]}
        with box.expander("고른 5개 조각 보기"):
            show_chunks([found[c] for c in search["chunk_ids"] if c in found])
    elif node == "grade":
        d = last_decision(steps, "grade")
        box = step_box(n, "찾은 근거로 답할 수 있나?")
        if "skipped" in d:
            box.write("→ 이런 종류의 질문은 근거가 충분한지 따지지 않고 바로 답 쓰기로 가요.")
        elif d.get("sufficient"):
            box.write("→ **충분해요.** 답 쓰기로 갑니다.")
        else:
            more = "검색어를 바꿔 다시 찾아요." if d.get("research", 0) < cfg_of(state["_cfg"])["agent"]["max_research"] else "이미 3번 찾았으니 있는 근거로 답을 씁니다."
            box.write(f"→ **부족해요.** {more}")
            box.caption(f"부족한 점: {d.get('missing', '')}")
    elif node == "rewrite":
        d = last_decision(steps, "rewrite")
        box = step_box(n, "검색어 바꾸기")
        box.write(f"새 검색어: **{d.get('query', '')}**")
    elif node == "generate":
        out = state["out"]
        revised = bool(state.get("revise")) and bool(state.get("problems"))
        box = step_box(n, "답 쓰기" + (" (검사 지적을 보고 고쳐 씀)" if revised else ""))
        box.markdown(pill(out.status), unsafe_allow_html=True)
        box.caption(out.answer[:220] + ("…" if len(out.answer) > 220 else ""))
    elif node == "cite_check":
        d = last_decision(steps, "cite_check")
        box = step_box(n, "출처 번호 확인")
        box.write("→ **통과.** 출처 번호가 모두 실제로 찾은 조각을 가리켜요." if d.get("ok") else "→ **틀림.** 없는 번호를 썼거나 출처가 없어서 답을 다시 써요.")
    elif node == "check":
        d = last_decision(steps, "check")
        box = step_box(n, "답 검사 (다른 AI)")
        if d.get("ok"):
            box.write("→ **문제 없음.** 그대로 끝냅니다.")
        else:
            box.write("→ **고칠 점이 있어요.** 아래 지적을 보고 한 번 고쳐 씁니다.")
            for p in d.get("problems", []):
                box.caption(f"• {p}")


def run_agent_live(cfg_path: str, question: str, scope: str, graph_slot, log):
    from rag.rag import format_answer
    ag = system_of(cfg_path)
    nodes, edges = (AGENT_NODES + V2_NODES, AGENT_EDGES + V2_EDGES) if ag.check else (AGENT_NODES, AGENT_EDGES)
    steps = {"calls": []}
    state = {"question": question, "scope": scope, "steps": steps}
    path = ["start"]
    graph_slot.graphviz_chart(flow_chart(nodes, edges, path, "start"), width="stretch")
    for update in ag.graph.stream(dict(state), stream_mode="updates"):  # one item per finished node
        for node, change in update.items():
            state.update(change or {})
            state["_cfg"] = cfg_path
            path.append(node)
            graph_slot.graphviz_chart(flow_chart(nodes, edges, path, node), width="stretch")
            with log:
                describe(node, len(path) - 1, state, steps)
    path.append("end")
    graph_slot.graphviz_chart(flow_chart(nodes, edges, path), width="stretch")
    reason = ("근거가 부족한 채로 끝났어요 (3번 찾음)" if not state.get("sufficient", True)
              else "답 검사 후 고쳐 쓰고 끝났어요" if state.get("revise") else "정상적으로 끝났어요")
    return {"status": state["out"].status, "answer": format_answer(state["out"].answer, state["citations"]),
            "context": state["units"], "citations": state["citations"], "steps": steps, "searches": len(state["searches"]),
            "reason": reason, "path": path}


def run_rag_live(cfg_path: str, question: str, scope: str, graph_slot, log):
    from rag.rag import format_answer, generate_answer, map_citations
    from rag.rerank import rerank
    system = system_of(cfg_path)
    cfg, steps, path = system.cfg, {"calls": []}, ["start"]

    def advance(node):
        path.append(node)
        graph_slot.graphviz_chart(flow_chart(RAG_NODES, RAG_EDGES, path, node), width="stretch")

    graph_slot.graphviz_chart(flow_chart(RAG_NODES, RAG_EDGES, path, "start"), width="stretch")
    pool = system._retriever(scope).search(question, steps, k=cfg["retrieval"]["rerank_pool"])
    advance("search")
    with log:
        box = step_box(1, "후보 15개 찾기")
        box.write("뜻이 비슷한 조각과 같은 단어가 들어 있는 조각을 합쳐 점수 순으로 15개를 꺼냈어요.")
        with box.expander("15개 후보 보기"):
            show_chunks(pool)
    picked = rerank(question, pool, cfg["retrieval"]["k"], cfg["retrieval"].get("rerank_model") or cfg["answer"]["model"], cfg, steps)
    advance("rerank")
    ids = {u["chunk_id"] for u in picked}
    with log:
        box = step_box(2, "AI가 5개 고르기")
        box.write(f"고른 후보 번호: **{[i + 1 for i, u in enumerate(pool) if u['chunk_id'] in ids]}**  (점수 순서대로 썼다면 [1, 2, 3, 4, 5])")
        with box.expander("고른 조각 보기"):
            show_chunks(pool, ids)
    out = generate_answer(question, picked, cfg, steps)
    citations, _ = map_citations(out.citations, picked)
    advance("generate")
    with log:
        box = step_box(3, "답 쓰기 + 출처 붙이기")
        box.markdown(pill(out.status), unsafe_allow_html=True)
    path.append("end")
    graph_slot.graphviz_chart(flow_chart(RAG_NODES, RAG_EDGES, path), width="stretch")
    return {"status": out.status, "answer": format_answer(out.answer, citations), "context": picked, "citations": citations,
            "steps": steps, "searches": 1, "reason": "정상적으로 끝났어요", "path": path}


def page_live():
    st.title("💬 직접 검색해서 써보기")
    st.write("궁금한 금융 질문을 넣어 보세요. 시스템이 **어떤 칸을 어떤 순서로 지나가는지** 왼쪽 그림에 실시간으로 표시되고, "
             "오른쪽에는 칸마다 무엇을 판단했는지가 쉬운 말로 쌓입니다. 기본은 **최종 시스템(T4)**이고, "
             "Agent(T3)를 고르면 ‘근거가 부족하면 다시 찾기’ 같은 갈림길도 볼 수 있습니다.")
    st.caption("실제로 AI를 부릅니다. 질문 하나에 약 0.004~0.02달러(5~25원) 듭니다. 시험 문제는 쓰지 않습니다. 같은 질문도 매번 조금씩 다르게 흘러갈 수 있습니다.")
    dev = {i["qid"]: i for i in load_golden(split="dev")}
    ex = {f"{label} · {dev[q]['question'][:40]}…": q for q, label in EXAMPLES if q in dev}
    c1, c2 = st.columns([3, 2])
    with c1:
        pick = st.selectbox("예시 질문 (직접 써도 됩니다)", ["(직접 입력)"] + list(ex))
    with c2:
        mode = st.radio("어떤 도우미로 답할까요?", list(SYSTEMS), index=0,
                        help="제출하는 시스템은 T4입니다. 나머지는 비교해 보라고 넣어 둔 것입니다. 칸이 많은 Agent를 고르면 갈림길과 되돌아가는 길이 보입니다.")
    item = dev[ex[pick]] if pick in ex else None
    question = st.text_area("질문", value=item["question"] if item else "", height=90,
                            placeholder="예: 휴면성 증권계좌는 어떤 계좌인가요?  /  주택연금은 몇 살부터 가입할 수 있나요?")
    kind, cfg_path = SYSTEMS[mode]
    default_scope = scope_of(item, cfg_of(cfg_path)) if item else "B"
    scope = st.radio("찾을 문서", ["B", "A"], index=0 if default_scope == "B" else 1, horizontal=True,
                     format_func=lambda s: "전체 23개 문서" if s == "B" else "용어집·약관만 (기본 문제 세트의 조건)")
    st.markdown(LEGEND, unsafe_allow_html=True)
    run = st.button("▶ 검색하고 답 받기", type="primary")
    left, right = st.columns([5, 6])
    with left:
        st.markdown("#### 지나가는 길")
        graph_slot = st.empty()
    with right:
        st.markdown("#### 칸마다 한 일")
        log = st.container()
    nodes, edges = ((AGENT_NODES + (V2_NODES if cfg_path == CFG_AGENT_V2 else []), AGENT_EDGES + (V2_EDGES if cfg_path == CFG_AGENT_V2 else []))
                    if kind == "agent" else (RAG_NODES, RAG_EDGES))
    if not run or not question.strip():
        graph_slot.graphviz_chart(flow_chart(nodes, edges), width="stretch")
        with log:
            st.info("질문을 넣고 ‘검색하고 답 받기’를 누르면 여기에 단계별 설명이 나타납니다.")
        return
    env.setup()
    try:
        with st.spinner("AI가 일하는 중…"):
            res = (run_agent_live if kind == "agent" else run_rag_live)(cfg_path, question.strip(), scope, graph_slot, log)
    except Exception as e:  # show the failure instead of a blank page (missing index, API key, quota)
        st.error(f"실행하지 못했어요: {e}")
        st.caption("인덱스가 없으면 `python scripts/build_index.py --config configs/013b-rerank-lite.yaml`, API 키는 `.env`의 GOOGLE_API_KEY를 확인하세요.")
        return
    st.divider()
    st.markdown(f'### 최종 답 {pill(res["status"])}', unsafe_allow_html=True)
    st.write(res["answer"])
    st.caption(f"끝난 이유: {res['reason']} · 지나간 칸 {len(res['path']) - 2}개")
    cost_row(res["steps"], res["searches"])
    with st.expander("답에 쓴 조각 모두 보기 (초록 = 출처로 쓴 조각)"):
        show_chunks(res["context"], {c["chunk_id"] for c in res["citations"]})
    if item:
        with st.expander("정답과 비교해 보기"):
            st.write("**기준 답안**", item["target_answer"])
            st.write("**꼭 들어가야 할 내용**", ", ".join(item["must_include"]) or "-")
            st.write("**정답이 있는 쪽**", [f"{t['file']} p.{t['page']}" for t in item["targets"]] or "문서에 없는 질문 (보류·되묻기·거절이 정답)")


# ---------------------------------------------------------------- 3. history
MILESTONES = [
    ("처음 시스템", "800자로 자르기 · 뜻 검색 · 작은 AI", "dev_000_baseline"),
    ("용어·조항 단위로 자르기", "용어집은 용어, 약관은 조항 단위", "dev_002b_structure900"),
    ("단어 검색 섞기", "뜻 검색 + 단어 검색(Hybrid)", "dev_004_hybrid"),
    ("더 큰 AI", "gemini-3.6-flash", "dev_007_flash36"),
    ("조각 크기 950자", "900 → 950", "dev_001e_chunk950chain"),
    ("답변 규칙 다듬기 v2", "빠뜨림·지나친 보류 줄이기", "dev_010_answerv2"),
    ("답변 규칙 v4", "항목별로 답하기, 거절 규칙 정리", "dev_012_flash36_v4"),
    ("AI가 5개 고르기", "후보 15개 → 5개 (rerank)", "dev_013_rerank_flash36_fix"),
]


def page_history():
    st.title("📈 점수가 어떻게 올랐나")
    st.caption("연습 문제 90개(시험 문제와 따로)로 잰 값입니다. 설정은 모두 연습 문제로만 골랐습니다. 막대가 높을수록 정답에 가깝습니다.")
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
    st.markdown('<div class="note">변화가 ±0.03 안쪽이면 운에 따른 흔들림과 구별되지 않습니다. '
                '그 흔들림을 확실히 넘은 개선은 <b>‘AI가 5개 고르기’</b> 하나였습니다.</div>', unsafe_allow_html=True)
    st.subheader("작은 AI(3.5 flash lite)로 낮췄을 때")
    lite = [("작은 AI + 규칙 v2", "dev_011_lite_v2"), ("+ 규칙 v3", "dev_011b_lite_v3"), ("+ 규칙 v4", "dev_011c_lite_v4"),
            ("+ AI가 5개 고르기 (★ 최종)", "dev_013b_rerank_lite_fix")]
    cols = st.columns(4)
    for col, (n, e) in zip(cols, lite):
        col.metric(n, f"{score(e):.3f}" if score(e) else "-")
    st.caption("큰 AI + 다시 고르기는 0.928, 작은 AI + 다시 고르기는 0.894입니다. 답변 비용은 작은 AI가 약 40%입니다(질문당 0.0035달러 대 0.0086달러).")
    st.subheader("구조를 바꿔 본 시도: Agent (최종에 쓰지 않음)")
    agent = [("T2 개선판 (칸 3개)", "dev_013_rerank_flash36_fix", "비교 기준. T4와 같은 구조에 큰 AI"),
             ("T3 Agent (스스로 점검)", "dev_008b_agent950", "질문 종류 판단·근거 판단·다시 찾기"),
             ("Agent v2 (+ 답 검사) · 버린 시도", "dev_014_agent_v2", "답을 검사해 1번 고쳐 쓰기")]
    cols = st.columns(3)
    for col, (n, e, what) in zip(cols, agent):
        s = summary_of(e)
        col.metric(n, f"{score(e):.3f}" if s else "-", f"질문당 {s['cost']['usd_per_question']:.4f}달러" if s else None, delta_color="off")
        col.caption(what)
    st.caption("세 값의 차이는 운의 범위 안입니다. Agent v2의 답 검사 칸은 90개 중 3개만 지적했고, 겨냥한 ‘한 가지를 빠뜨린 답’ 10개는 하나도 잡지 못했습니다.")
    with st.expander("실험 번호와 실험 카드 보기 (자세히 알고 싶을 때)"):
        st.dataframe(df[["단계", "실험", "점수", "변화"]], hide_index=True, width="stretch")
        cards = sorted((ROOT / "experiments").glob("0*.md"))
        pick = st.selectbox("실험 카드", cards, format_func=lambda p: p.stem)
        st.markdown(pick.read_text(encoding="utf-8").split("-->", 1)[-1])


# ---------------------------------------------------------------- 4. chunks
def chunk_html(c: dict) -> str:
    text = esc(c["content"]).replace("\n", " ")
    return f'<div class="chunk"><span class="tag">{len(c["content"])}자 · p.{c["page"]}</span><br>{text[:420]}{"…" if len(text) > 420 else ""}</div>'


def page_chunks():
    st.title("✂️ 글을 어떻게 잘랐나")
    st.write("찾기는 ‘조각’ 단위로 합니다. 조각이 너무 크면 엉뚱한 내용이 섞이고, 너무 작으면 설명이 잘려 나갑니다. "
             "그래서 용어집과 약관은 **뜻 단위**(용어 하나, 조항 하나)로 자르고, 나머지는 **950자**로 잘랐습니다.")
    base = jsonl(str(index_dir(cfg_of(CFG_BASE), "B") / "chunks.jsonl"))
    final = jsonl(str(index_dir(cfg_of(CFG_LITE), "B") / "chunks.jsonl"))
    if not base or not final:
        st.warning("인덱스가 없습니다. scripts/build_index.py 를 먼저 실행하세요.")
        return
    m1, m2 = st.columns(2)
    m1.metric("처음 방식: 조각 수", f"{len(base):,}", help="800자씩 기계적으로")
    m2.metric("최종 방식: 조각 수", f"{len(final):,}", help="용어·조항 단위 + 950자")
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
        st.markdown("#### 최종: 뜻 단위 / 950자")
        for c in [c for c in final if c["source"] == doc and c["page"] == page]:
            st.markdown(chunk_html(c), unsafe_allow_html=True)
    st.caption("용어집 6쪽을 열어 보세요. 처음 방식은 여러 용어가 한 조각에 섞이고, 최종 방식은 용어마다 한 조각입니다.")


# ---------------------------------------------------------------- 5. final test
def page_test():
    st.title("🏁 최종 시험 결과")
    st.write("시험 문제 90개(제공) + 직접 만든 문제 41개 = **131문항**을 네 시스템에 한 번씩 풀게 했습니다. "
             "시험 문제를 보고 시스템을 고치지 않았습니다. 자세한 해석은 `submission/EVALUATION.md`에 있습니다.")
    systems = [("처음 시스템 (T1)", "T1", "800자로 자르기 · 뜻 검색 · 작은 AI"),
               ("개선판 (T2)", "T2", "용어·조항 단위 · 뜻+단어 검색 · AI가 5개 고르기 · 큰 AI"),
               ("Agent (T3)", "T3", "T2 + 스스로 점검하는 칸들"),
               ("★ 최종 선택 (T4)", "T4", "T2와 같은 구조 · 작은 AI")]
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
            st.progress(s["full"], text=f"완전히 맞힌 비율 {s['full'] * 100:.0f}%")
            st.caption(what)
            st.write(f"질문당 비용 **{s['usd']:.4f}달러** · 느린 쪽 10%의 응답 시간 **{s['p90']:.1f}초**")
    st.divider()
    st.subheader("문제 종류별 점수")
    gold = {i["qid"]: i["set"] for i in load_golden()}
    names = {"base_positive": "용어·약관 질문", "base_negative": "답하면 안 되거나 되물어야 하는 질문", "life_guide": "생활 금융 가이드",
             "additional": "보고서·정책 자료", "self2": "직접 만든 문제"}
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
    • 처음 → 개선판(T2): +0.17로 확실한 개선입니다(운의 범위 밖).<br>
    • 개선판 → Agent(T3): +0.03으로 운의 범위 안이라 효과가 있다고 말할 수 없고, 비용은 1.5배·느린 쪽 응답 시간은 2.4배입니다.<br>
    • 큰 AI → 작은 AI(T4): 점수는 0.03 낮지만(운의 범위 안) 비용은 0.4배, 응답은 2배 빠릅니다. 가격 때문에 T4를 최종으로 골랐습니다.<br>
    • T4는 시험 문제를 두 번째로 쓴 것입니다(처음엔 T1~T3만 돌림). 고른 이유는 가격이고 시험 점수가 아닙니다.<br>
    • 시험이 끝난 뒤 Agent v2를 직접 만든 문제 41개에만 한 번 돌렸습니다: 0.939 (T2 0.902, T3 0.927). 고쳐 쓴 답은 0개였습니다.</div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------- 6. per-question
RUN_NAMES = {"test_013b_rerank_lite": "★ 시험 T4 (최종 시스템)", "dev_013b_rerank_lite_fix": "최종 시스템 (연습 문제 90개)",
             "dev_013_rerank_flash36_fix": "개선판 큰 AI (연습 문제)", "dev_008b_agent950": "Agent (연습 문제)", "dev_014_agent_v2": "Agent v2 (연습 문제)",
             "test_013_rerank_flash36": "시험 T2", "test_000_baseline": "시험 T1", "test_008b_agent950": "시험 T3",
             "test_013_rerank_flash36_self2": "시험 T2 (직접 만든 41문항)", "test_000_baseline_self2": "시험 T1 (직접 만든 41문항)",
             "test_008b_agent950_self2": "시험 T3 (직접 만든 41문항)", "test_014_agent_v2_self2": "Agent v2 (직접 만든 41문항)"}


def page_results():
    st.title("🧾 문항별 결과")
    exps = sorted(p.name for p in RESULTS.iterdir() if (p / "runs.jsonl").exists() and (p / "grades.jsonl").exists())
    exp = st.selectbox("어느 실행을 볼까요?", exps, index=exps.index("test_013b_rerank_lite") if "test_013b_rerank_lite" in exps else 0,
                       format_func=lambda e: RUN_NAMES.get(e, e))
    runs = {r["qid"]: r for r in jsonl(str(RESULTS / exp / "runs.jsonl"))}
    grades = {g["qid"]: g for g in jsonl(str(RESULTS / exp / "grades.jsonl"))}
    gold = {i["qid"]: i for i in load_golden()}
    rows = [{"문항": q, "점수(0~2)": grades[q]["correctness"], "응답": STATUS.get(runs[q]["status"], (runs[q]["status"],))[0],
             "찾은 횟수": runs[q].get("n_searches", 1), "질문": runs[q]["question"][:70]} for q in grades if q in runs]
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
        st.write("꼭 들어가야 할 내용:", ", ".join(i.get("must_include") or []) or "-")
        st.write("정답 근거 쪽:", [f"{t['file']} p.{t['page']}" for t in i.get("targets", [])] or "문서에 없는 질문")
    if r.get("system") == "agent" and r.get("steps", {}).get("decisions"):
        with st.expander("이 문항이 Agent에서 지나간 길 보기"):
            path = ["start"] + agent_path(r)
            v2 = any(d["node"] == "check" for d in r["steps"]["decisions"])
            st.graphviz_chart(flow_chart(AGENT_NODES + (V2_NODES if v2 else []), AGENT_EDGES + (V2_EDGES if v2 else []), path + ["end"]), width="stretch")
    with st.expander("답에 넘긴 조각 보기"):
        show_chunks(r["context"], {c["chunk_id"] for c in r.get("citations", [])})


def agent_path(run: dict) -> list[str]:
    """Rebuild the node order of a saved agent run from its decisions (retrieve and generate leave none)."""
    path = []
    for d in run["steps"]["decisions"]:
        node = d["node"]
        if node == "classify":
            path += ["classify", "retrieve"]
        elif node == "grade":
            path.append("grade")
        elif node == "rewrite":
            path += ["rewrite", "retrieve"]
        elif node == "cite_check":
            path += ["generate", "cite_check"]
        elif node == "check":
            path.append("check")
    return path


# ---------------------------------------------------------------- 7. lessons
def page_lessons():
    st.title("💡 배운 점")
    st.caption("자세한 내용은 `submission/RETROSPECTIVE.md`(회고)와 `submission/EVALUATION.md`(가설별 결과)에 있습니다.")
    st.subheader("통한 것")
    good = [("용어·조항 단위로 자르기", "정답이 있는 쪽을 찾는 비율 0.88 → 0.96"),
            ("AI가 후보를 다시 고르기", "연습 문제 점수 0.883 → 0.928, 유일하게 운의 범위를 확실히 넘은 개선"),
            ("더 큰 AI", "0.772 → 0.822 (대신 비용 2.3배)"),
            ("답변 규칙을 절차로 쓰기", "작은 AI 0.822 → 0.856 (질문을 부분으로 나눠 하나씩 답하게)")]
    cols = st.columns(4)
    for col, (t, b) in zip(cols, good):
        with col:
            card("✅ " + t, b)
    st.subheader("안 통한 것")
    bad = [("조각 크기만 바꾸기", "400~1,200자 모두 운의 범위 안. 크기보다 ‘어디서 자르나’가 중요했습니다."),
           ("단어 검색만 쓰기", "용어 질문에서도 오히려 낮았습니다(0.80 대 뜻 검색 0.96)."),
           ("Agent의 다시 찾기", "이미 잘 찾고 있어서 다시 찾기가 거의 안 일어났습니다(90개 중 3~9개)."),
           ("답 검사 칸 (v2)", "빠진 내용이 기준 답에만 있는 세부 항목이라, 검사하는 AI 눈에는 완성된 답으로 보였습니다.")]
    cols = st.columns(4)
    for col, (t, b) in zip(cols, bad):
        with col:
            card("✖ " + t, b)
    st.subheader("처음 세운 가설은 맞았나")
    st.dataframe(pd.DataFrame([
        {"가설": "H1 뜻 단위로 자르면 근거를 더 잘 찾는다", "결과": "찾기에서는 맞음, 답 점수로는 운의 범위"},
        {"가설": "H2 조각에 문서 제목을 붙이면 더 정확하다", "결과": "시간이 부족해 확인 안 함"},
        {"가설": "H3 용어 질문은 단어 검색이 낫다", "결과": "틀림 (뜻 검색이 더 나음). 둘을 섞는 건 무난"},
        {"가설": "H4 Agent는 어려운 질문에서 낫지만 비용 2배 이상", "결과": "방향은 맞지만 운의 범위, 비용은 1.3~1.9배"},
        {"가설": "H5 작은 AI는 어려운 문제에서 차이가 난다", "결과": "부분적으로 맞음 (보고서·정책 자료에서 차이)"},
    ]), hide_index=True, width="stretch")
    st.subheader("다시 한다면")
    st.markdown("""
1. 찾는 방법을 먼저 다 고친 뒤, 남은 실패를 보고 Agent를 설계한다.
2. 채점하는 AI를 답하는 AI와 다른 모델로 처음부터 정한다.
3. 직접 만드는 문제는 몇 개를 먼저 풀어 보고 난이도를 맞춘다.
4. 가격 같은 조건은 시험 전에 모두 정한다.
5. 큰 실행 전에는 꼭 1문항만 먼저 돌려 본다.
""")


# ---------------------------------------------------------------- 8. glossary
def page_glossary():
    st.title("📖 용어 설명")
    terms = {
        "RAG": "먼저 문서를 찾고(검색), 찾은 내용을 보고 답을 쓰는(생성) 방식. AI가 기억에 의존해 지어내는 것을 줄입니다.",
        "조각 (청크)": "긴 문서를 찾기 좋게 자른 작은 부분. ‘청킹’은 자르는 일입니다.",
        "뜻 검색 (임베딩·벡터 검색)": "문장의 뜻을 숫자 목록으로 바꿔, 숫자가 가까운(뜻이 비슷한) 조각을 찾는 방식.",
        "단어 검색 (BM25)": "질문과 같은 단어가 많이 들어 있는 조각을 높게 치는 전통적인 검색 방식.",
        "섞어 찾기 (Hybrid)": "뜻 검색과 단어 검색 점수를 반반 섞어 찾는 방식.",
        "다시 고르기 (rerank)": "찾아 둔 후보 15개를 AI가 다시 읽고 정말 필요한 5개만 고르는 단계.",
        "Agent": "정해진 순서대로만 하지 않고, 중간중간 스스로 판단해 다음 행동을 고르는 구조. 여기서는 질문 종류를 보고, 근거가 부족하면 다시 찾습니다.",
        "칸 (노드)": "Agent 그림의 상자 하나. 한 가지 일(판단·찾기·답 쓰기)을 합니다. 화살표는 다음에 갈 칸이고, 갈림길에서는 판단 결과에 따라 길이 나뉩니다.",
        "LangGraph": "칸과 화살표로 Agent의 흐름을 만드는 도구(파이썬 라이브러리). 이 프로젝트의 Agent를 이걸로 만들었습니다.",
        "답 검사 (Reflection)": "다른 AI가 답 초안을 읽고 빠진 내용을 찾아 고쳐 쓰게 하는 단계. v2에서 시도했습니다.",
        "연습 문제 / 시험 문제 (dev / test)": "연습 문제 90개로 설정을 고르고, 시험 문제는 마지막에 한 번만 풉니다. 시험 문제로 고치면 점수가 부풀려지기 때문입니다.",
        "정답 점수": "틀림 0점·일부 1점·정답 2점을 평균해 0~1로 만든 값. 채점은 AI가 기준 답안과 비교해 합니다.",
        "운의 범위 (노이즈)": "같은 설정도 다시 돌리면 결과가 조금씩 달라지는 흔들림. 90문항 중 약 14문항의 답이 바뀝니다. 이보다 작은 차이는 개선이라고 말하지 않습니다.",
        "답함 / 보류 / 되묻기 / 거절": "근거가 있으면 답하고, 근거가 없으면 보류, 정보가 모자라면 되묻기, 해서는 안 되는 요청이면 거절합니다.",
        "토큰": "AI가 글을 읽고 쓰는 단위. 대략 한글 1~2글자. 비용은 토큰 수로 매겨집니다.",
    }
    for k, v in terms.items():
        with st.container(border=True):
            st.markdown(f"**{k}**")
            st.write(v)


PAGES = {"🏠 처음 보는 분을 위한 요약": page_overview, "🧭 어떻게 동작하나": page_flow, "💬 직접 검색해서 써보기": page_live,
         "📈 점수가 오른 과정": page_history, "✂️ 글을 자른 방식": page_chunks, "🏁 최종 시험 결과": page_test,
         "🧾 문항별 결과": page_results, "💡 배운 점": page_lessons, "📖 용어 설명": page_glossary}
st.sidebar.title("📚 금융 문서 QA")
PAGES[st.sidebar.radio("메뉴", list(PAGES), label_visibility="collapsed")]()
