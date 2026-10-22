"""Streamlit viewer for the whole project: pipeline flow, how the score moved, chunks, a live question run
step by step, and per-question results.

    streamlit run app/streamlit_app.py

The live page calls the Gemini API (needs .env) and uses the indexes in out/index (build them with
scripts/build_index.py). It uses dev questions only, never the test split.
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

FINAL_CFG = "configs/013-rerank-flash36.yaml"
BASE_CFG = "configs/baseline.yaml"
RESULTS = ROOT / "results"

st.set_page_config(page_title="금융 문서 RAG 따라가기", layout="wide")


# ---------------------------------------------------------------- shared loaders
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


# ---------------------------------------------------------------- page 1: flow
PIPELINE = """
digraph G {
  rankdir=LR; node [shape=box, style="rounded,filled", fillcolor="#eef2ff", fontname="Helvetica"];
  subgraph cluster_prep { label="준비 (한 번만)"; style=dashed;
    pdf [label="PDF 23개\\n(용어집·약관 15·가이드·추가 자료)"];
    ext [label="쪽별 텍스트 추출 PyMuPDF\\n+ 표·차트는 VLM이 글로 정리"];
    chunk [label="청킹 (규칙)\\n용어집=용어 1개\\n약관=조 1개\\n나머지=950자/겹침 119"];
    emb [label="임베딩 gemini-embedding-2"];
    vs [label="Chroma (벡터)", fillcolor="#fef3c7"]; bm [label="BM25 (Kiwi 형태소)", fillcolor="#fef3c7"];
    pdf -> ext -> chunk -> emb -> vs; chunk -> bm; }
  subgraph cluster_ask { label="질문할 때"; style=dashed;
    q [label="질문", shape=oval, fillcolor="#dcfce7"];
    hy [label="Hybrid 검색\\n벡터+BM25 → 후보 15개"];
    rr [label="LLM rerank\\n15개 중 5개 고름", fillcolor="#fde68a"];
    ans [label="답변 gemini-3.6-flash\\n프롬프트 v4\\n근거만 사용, 상태 선택"];
    out [label="상태(답함/보류/되묻기/거절)\\n+ 답 + 출처(파일·쪽)", shape=oval, fillcolor="#dcfce7"];
    q -> hy -> rr -> ans -> out; }
  vs -> hy; bm -> hy;
}
"""

AGENT = """
digraph A {
  rankdir=TB; node [shape=box, style="rounded,filled", fillcolor="#eef2ff", fontname="Helvetica"];
  s [label="질문", shape=oval]; e [label="끝", shape=oval];
  classify [label="classify\\n질문 유형 4가지"]; retrieve [label="retrieve\\n(rerank 포함, 누적 10개)"];
  grade [label="grade\\n근거가 충분한가?"]; rewrite [label="rewrite\\n검색어 다시 쓰기 (최대 2회)"];
  generate [label="generate\\n(기본 RAG와 같은 답변)"]; cite [label="cite_check\\n인용 번호 확인 (실패 시 1회 재시도)"];
  s -> classify -> retrieve -> grade;
  grade -> rewrite [label="부족"]; rewrite -> retrieve;
  grade -> generate [label="충분 / 2회 소진"];
  generate -> cite; cite -> generate [label="실패"]; cite -> e [label="통과"];
}
"""


def page_flow():
    st.title("금융 문서 RAG: 어떻게 만들었나")
    st.caption("최종 시스템(T2) = 구조 단위 청킹 + Hybrid 검색 + LLM rerank + gemini-3.6-flash + 프롬프트 v4")
    st.graphviz_chart(PIPELINE, width="stretch")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("단계별 쉬운 설명")
        st.markdown(
            "1. **추출**: PDF를 쪽 단위 글자로 바꿉니다. 표·그래프는 이미지라 글자로 안 뽑혀서, 모델이 읽어서 글로 정리해 덧붙입니다.\n"
            "2. **청킹**: 글을 검색 단위로 자릅니다. 용어집은 용어 하나, 약관은 조 하나로 자르고 나머지는 950자씩 자릅니다. 규칙 코드이고 LLM은 안 씁니다.\n"
            "3. **검색**: 질문과 뜻이 가까운 조각(벡터)과 단어가 겹치는 조각(BM25)을 합쳐 15개를 뽑습니다.\n"
            "4. **rerank**: 모델이 15개를 읽고 질문에 답하는 데 필요한 5개를 고릅니다. 이번 개선에서 가장 컸습니다.\n"
            "5. **답변**: 5개 조각만 근거로 답하고, 상태(답함/보류/되묻기/거절)와 인용 번호를 냅니다. 코드가 번호를 파일·쪽으로 바꿔 출처로 붙입니다.")
    with c2:
        st.subheader("최종 설정 값")
        cfg = cfg_of(FINAL_CFG)
        rows = {"청킹": f"{cfg['chunking']['method']} / {cfg['chunking']['chunk_size']}자 / 겹침 {cfg['chunking']['chunk_overlap']}",
                "임베딩": cfg["embedding"]["model"], "검색": f"{cfg['retrieval']['method']} (α={cfg['retrieval']['hybrid_alpha']}), k={cfg['retrieval']['k']}, 후보 {cfg['retrieval'].get('rerank_pool')}",
                "답변 모델": cfg["answer"]["model"], "프롬프트": cfg["answer"]["prompt"], "thinking": cfg["answer"]["thinking_level"],
                "채점 모델(고정)": "gemini-3.6-flash + prompts/judge_v1.md"}
        st.table(pd.DataFrame({"값": rows}))
    st.divider()
    st.subheader("비교용 Agent (T3): 같은 검색·답변 위에 구조만 더함")
    st.graphviz_chart(AGENT)


# ---------------------------------------------------------------- page 2: history
MILESTONES = [
    ("처음 RAG (Recursive 800, 벡터, lite, v1)", "dev_000_baseline"),
    ("+ 구조 단위 청킹, 나머지 900", "dev_002b_structure900"),
    ("+ Hybrid 검색", "dev_004_hybrid"),
    ("+ 답변 모델 3.6-flash", "dev_007_flash36"),
    ("+ 청크 950", "dev_001e_chunk950chain"),
    ("+ 프롬프트 v2", "dev_010_answerv2"),
    ("+ 프롬프트 v4", "dev_012_flash36_v4"),
    ("+ LLM rerank (최종 T2)", "dev_013_rerank_flash36_fix"),
]
SIDE = [("lite + v2", "dev_011_lite_v2"), ("lite + v3", "dev_011b_lite_v3"), ("lite + v4", "dev_011c_lite_v4"),
        ("lite + v4 + rerank", "dev_013b_rerank_lite_fix"), ("Agent (카드 008, 900 체인·v1)", "dev_008_agent")]


def score_row(label, exp):
    s = summary_of(exp)
    if not s:
        return None
    sc, c = s["scores"], s["cost"]
    return {"단계": label, "실험": exp, "정답 점수": sc.get("correctness_mean"), "완전 정답 비율": sc.get("fully_correct"),
            "근거 포함률 evid@5": s["retrieval"].get("evid@5"), "답변 USD/문항": c.get("usd_per_question"),
            "p90 지연(초)": (s.get("latency_s") or {}).get("p90")}


def page_history():
    st.title("점수가 어떻게 올랐나 (dev 90문항)")
    rows = [r for r in (score_row(*m) for m in MILESTONES) if r]
    df = pd.DataFrame(rows)
    st.line_chart(df.set_index("단계")[["정답 점수", "완전 정답 비율"]])
    st.dataframe(df, width="stretch", hide_index=True)
    st.caption("한 번씩 돌린 값입니다. 같은 설정을 다시 돌리면 90문항 중 약 14문항의 답이 바뀌므로 0.02 안팎의 차이는 구별되지 않습니다. 개선 폭이 노이즈를 이긴 것은 rerank뿐입니다(카드 013).")
    st.subheader("곁가지 실험")
    side = [r for r in (score_row(*m) for m in SIDE) if r]
    st.dataframe(pd.DataFrame(side), width="stretch", hide_index=True)
    st.subheader("실험 카드")
    cards = sorted((ROOT / "experiments").glob("0*.md"))
    pick = st.selectbox("카드 보기", cards, format_func=lambda p: p.stem)
    st.markdown(pick.read_text(encoding="utf-8").split("-->", 1)[-1])
    tests = [(n, e) for n, e in (("T1 처음 RAG", "test_000_baseline"), ("T2 개선된 RAG", "test_013_rerank_flash36"),
                                 ("T3 Agent", "test_008b_agent950")) if summary_of(e)]
    if tests:
        st.subheader("최종 test (한 번 실행한 결과)")
        st.dataframe(pd.DataFrame([score_row(n, e) for n, e in tests]), width="stretch", hide_index=True)


# ---------------------------------------------------------------- page 3: chunks
def page_chunks():
    st.title("청킹: 글이 어떻게 잘렸나")
    label = st.radio("설정", ["최종: 구조 단위 + 950자", "처음: Recursive 800자"], horizontal=True)
    cfg = cfg_of(FINAL_CFG if label.startswith("최종") else BASE_CFG)
    path = index_dir(cfg, "B") / "chunks.jsonl"
    chunks = jsonl(str(path))
    if not chunks:
        st.warning(f"{path} 가 없습니다. scripts/build_index.py 로 인덱스를 먼저 만드세요.")
        return
    df = pd.DataFrame([{"문서": c["source"], "쪽": c["page"], "글자 수": len(c["content"]), "내용": c["content"]} for c in chunks])
    st.write(f"조각 {len(df):,}개, 글자 수 중앙값 {int(df['글자 수'].median())}")
    docs = sorted(df["문서"].unique())
    doc = st.selectbox("문서", docs)
    sub = df[df["문서"] == doc]
    st.bar_chart(sub["글자 수"].reset_index(drop=True))
    page = st.select_slider("쪽", options=sorted(sub["쪽"].unique()))
    for _, r in sub[sub["쪽"] == page].iterrows():
        with st.expander(f"p.{r['쪽']} · {r['글자 수']}자 · {r['내용'][:40]}…"):
            st.text(r["내용"])


# ---------------------------------------------------------------- page 4: live
def calls_table(steps: dict, prices: dict):
    rows = [{"단계": c["node"], "모델": c["model"], "입력 토큰": c["input_tokens"], "출력 토큰": c["output_tokens"],
             "초": c["seconds"], "USD": round(call_usd(c, prices), 5)} for c in steps.get("calls", [])]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


def show_units(units, picked_ids=None):
    for i, u in enumerate(units, 1):
        mark = "✅ " if picked_ids is not None and u["chunk_id"] in picked_ids else ""
        with st.expander(f"{mark}[{i}] {u['source']} p.{u['page']} (점수 {u.get('score')})"):
            st.text(u["content"])


def page_live():
    st.title("질문 하나를 따라가기")
    st.caption("실제로 API를 호출합니다(질문 하나에 약 0.01 USD). dev 질문 또는 직접 입력.")
    dev = [i for i in load_golden(split="dev")]
    options = {"(직접 입력)": None, **{f"{i['qid']} · {i['question'][:50]}": i for i in dev}}
    choice = st.selectbox("dev 질문 고르기", list(options))
    item = options[choice]
    question = st.text_input("질문", value=item["question"] if item else "")
    mode = st.radio("시스템", ["RAG (T2)", "Agent (T3)"], horizontal=True)
    if not (st.button("실행") and question.strip()):
        return
    env.setup()
    prices = load_prices()
    scope = "B"
    if mode.startswith("RAG"):
        from rag import llm
        from rag.rag import format_answer, generate_answer, map_citations
        from rag.rerank import rerank
        system = system_of(FINAL_CFG)
        cfg, steps = system.cfg, {"calls": []}
        retriever = system._retriever(scope)
        with st.status("1. Hybrid 검색 (벡터 + BM25)", expanded=True):
            pool = retriever.search(question, steps, k=cfg["retrieval"]["rerank_pool"])
            st.write(f"후보 {len(pool)}개. 아래는 합친 점수 순서입니다.")
            show_units(pool)
        with st.status("2. LLM rerank: 15개 중 5개 고르기", expanded=True):
            picked = rerank(question, pool, cfg["retrieval"]["k"], cfg["answer"]["model"], cfg, steps)
            ids = {u["chunk_id"] for u in picked}
            moved = [i + 1 for i, u in enumerate(pool) if u["chunk_id"] in ids]
            st.write(f"고른 후보 번호: {moved} (원래 상위 5개는 [1~5])")
        with st.status("3. 답변 (고른 5개만 근거)", expanded=True):
            out = generate_answer(question, picked, cfg, steps)
            citations, _ = map_citations(out.citations, picked)
            st.markdown(f"**상태:** `{out.status}`")
            st.markdown(format_answer(out.answer, citations))
            show_units(picked, ids)
        st.subheader("호출 기록")
        calls_table(steps, prices)
    else:
        agent = system_of("configs/008b-agent-950.yaml")
        with st.spinner("Agent 실행 중"):
            res = agent.run(question, scope)
        st.markdown(f"**상태:** `{res['status']}` · 검색 {res['n_searches']}회 · LLM {res['n_llm_calls']}회")
        st.subheader("노드별 판단")
        st.json(res["steps"].get("decisions", []))
        st.subheader("검색어")
        st.write([s["query"] for s in res["searches"]])
        st.subheader("답변")
        st.markdown(res["answer"])
        show_units(res["context"], {c["chunk_id"] for c in res["citations"]})
        calls_table(res["steps"], prices)
    if item:
        with st.expander("정답과 비교 (채점 기준)"):
            st.write("기준 답안:", item["target_answer"])
            st.write("반드시 포함:", item["must_include"])
            st.write("정답 근거 쪽:", item["targets"])


# ---------------------------------------------------------------- page 5: results
def page_results():
    st.title("문항별 결과 둘러보기")
    exps = sorted(p.name for p in RESULTS.iterdir() if (p / "runs.jsonl").exists() and (p / "grades.jsonl").exists())
    exp = st.selectbox("실험", exps, index=exps.index("dev_013_rerank_flash36_fix") if "dev_013_rerank_flash36_fix" in exps else 0)
    runs = {r["qid"]: r for r in jsonl(str(RESULTS / exp / "runs.jsonl"))}
    grades = {g["qid"]: g for g in jsonl(str(RESULTS / exp / "grades.jsonl"))}
    mets = {m["qid"]: m for m in jsonl(str(RESULTS / exp / "metrics.jsonl"))}
    gold = {i["qid"]: i for i in load_golden()}
    df = pd.DataFrame([{"qid": q, "세트": mets.get(q, {}).get("set"), "점수": grades[q]["correctness"], "상태": runs[q]["status"],
                        "evid@5": mets.get(q, {}).get("evid@5"), "질문": runs[q]["question"][:60]} for q in grades if q in runs])
    c1, c2 = st.columns(2)
    only_bad = c1.checkbox("만점이 아닌 것만", value=True)
    sets = c2.multiselect("세트", sorted(df["세트"].dropna().unique()))
    if only_bad:
        df = df[df["점수"] < 2]
    if sets:
        df = df[df["세트"].isin(sets)]
    st.write(f"{len(df)}문항")
    pick = st.dataframe(df, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row")
    rows = pick.selection.rows
    qid = df.iloc[rows[0]]["qid"] if rows else (df.iloc[0]["qid"] if len(df) else None)
    if not qid:
        return
    r, g, i = runs[qid], grades[qid], gold.get(qid, {})
    st.subheader(f"{qid}: {r['question']}")
    a, b = st.columns(2)
    with a:
        st.markdown(f"**시스템 답변** (`{r['status']}`)")
        st.markdown(r["answer"])
        st.markdown(f"**채점** {g['correctness']}점: {g['reason']}")
    with b:
        st.markdown("**기준 답안**")
        st.write(i.get("target_answer"))
        st.write("반드시 포함:", i.get("must_include"), "· 기대 행동:", i.get("expected_behavior"))
        st.write("정답 근거 쪽:", i.get("targets"))
    st.markdown("**답변에 넘긴 조각 5개**")
    cited = {c["chunk_id"] for c in r.get("citations", [])}
    show_units(r["context"], cited)
    rr = (r.get("steps") or {}).get("rerank")
    if rr:
        st.caption(f"rerank 후보 {len(rr['pool'])}개 중 고른 것: {len(rr['picked'])}개, 실패={rr['failed']}")


PAGES = {"1. 전체 흐름": page_flow, "2. 점수가 오른 과정": page_history, "3. 청킹 보기": page_chunks,
         "4. 질문 따라가기 (실시간)": page_live, "5. 문항별 결과": page_results}
st.sidebar.title("금융 문서 RAG")
PAGES[st.sidebar.radio("페이지", list(PAGES))]()
