"""Chunker comparison page in the style of app/streamlit_app.py: Serin's structure chunker (dev_001e) vs the
mixed chunker (chunking_sum.py: Serin's units + LimDaeJin's hard cap and header), dev retrieval only.

    python app/chunk_compare_data.py                       # chunk data -> out/chunk_compare.json
    streamlit run app/compare_app.py --server.port 8502

No LLM calls; the test split is not read.
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
MAX_CHARS = 1600
RUNS = [("serin", "세린님 청크", "dev_001e_chunk950chain_retrieval"),
        ("mixed", "섞은 코드 (머리말 없음)", "dev_014_mixedchunk_retrieval"),
        ("header", "섞은 코드 + 머리말", "dev_014b_mixedchunk_header_retrieval")]
METRICS = [("page_hit@5", "정답 쪽 찾음", "5개 조각 안에 정답 쪽이 하나라도 있는 비율"),
           ("evid@5", "근거 문장 포함", "답에 필요한 근거 문장이 5개 조각 안에 들어 있는 비율 (주 지표)"),
           ("mrr", "첫 정답 순위", "첫 정답 조각이 위에 있을수록 1에 가까움"),
           ("gold@5", "정답 조각 수", "5개 중 정답 쪽 조각의 평균 개수")]

st.set_page_config(page_title="청크 비교: 세린님 vs 섞은 코드", page_icon="✂️", layout="wide")
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
.chunk {border-left: 5px solid #94a3b8; background:#f1f5f9; border-radius: 8px; padding: 8px 12px; margin: 6px 0; font-size: 0.9rem; color:#0f172a;}
.chunk.picked {border-left-color:#16a34a; background:#dcfce7; color:#0f172a;}
.chunk.long {border-left-color:#dc2626; background:#fee2e2; color:#0f172a;}
.chunk .tag {font-size:0.78rem; color:#475569;}
.note {background:#fffbeb; border:1px solid #fde68a; border-radius:10px; padding:10px 14px; color:#78350f;}
.note b {color:#78350f;}
</style>
""", unsafe_allow_html=True)


def card(title: str, body: str):
    st.markdown(f'<div class="card"><h4>{title}</h4><p>{body}</p></div>', unsafe_allow_html=True)


@st.cache_data
def summary(exp: str) -> dict:
    return json.loads((RESULTS / exp / "summary.json").read_text(encoding="utf-8"))


@st.cache_data
def metrics(exp: str) -> pd.DataFrame:
    rows = [json.loads(l) for l in (RESULTS / exp / "metrics.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    return pd.DataFrame(rows).set_index("qid")


@st.cache_data
def chunk_data() -> dict:
    return json.loads((ROOT / "out" / "chunk_compare.json").read_text(encoding="utf-8"))


def chunk_html(c: dict, css: str = "") -> str:
    text = c["content"].replace("<", "&lt;").replace(">", "&gt;").replace("\n", " ")
    where = "p." + "-".join(str(p) for p in sorted({c["pages"][0], c["pages"][-1]}))
    return (f'<div class="chunk {css}"><span class="tag">{len(c["content"]):,}자 · {where}</span><br>'
            f'{text[:420]}{"…" if len(text) > 420 else ""}</div>')


st.title("✂️ 청크 비교: 세린님 vs 섞은 코드")
st.markdown('<div class="hero"><h2>같은 문제, 같은 검색, 자르는 방법만 다르게</h2><p>세린님의 구조 단위 자르기(용어 하나, 조 하나, '
            '나머지는 950자)에 대진님 코드의 두 가지를 더했습니다. ① 1,600자를 넘는 조각을 줄 끝에서 한 번 더 자르기, '
            '② 조각 앞에 [문서 제목 | 쪽 | 조] 머리말 붙이기. 개발용 90문항(정답 쪽이 있는 74문항)으로 검색만 비교했고, LLM은 쓰지 않았습니다.</p></div>',
            unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
with c1:
    card("세린님 청크", "용어집은 용어 하나씩, 약관은 조 하나씩(1,600자 넘으면 ①② 항 앞에서 자름), 나머지 문서는 950/119자.")
with c2:
    card("섞은 코드", "세린님 방식 그대로 + ①② 항이 없어 1,600자를 넘던 조각을 줄 끝에서 다시 잘라 어떤 조각도 1,600자를 넘지 않게.")
with c3:
    card("섞은 코드 + 머리말", "위 방식 + 모든 조각 맨 앞에 [문서 제목 | p.쪽 | 제N조(…)] 한 줄. 잘린 조각도 조 이름을 유지.")

st.subheader("검색 성적")
st.caption("같은 설정(구조 단위 + 950/119 + hybrid 검색, k=5). 괄호 대신 화살표 숫자가 세린님 대비 차이입니다.")
sums = {key: summary(exp)["retrieval"] for key, _, exp in RUNS}
for metric, label, help_text in METRICS:
    cols = st.columns(3)
    for col, (key, name, _) in zip(cols, RUNS):
        v, base = sums[key][metric], sums["serin"][metric]
        col.metric(f"{label} · {name}", f"{v:.3f}", None if key == "serin" else f"{v - base:+.3f}", help=help_text)

chart = pd.DataFrame({name: [sums[key][m] for m, *_ in METRICS[:3]] for key, name, _ in RUNS},
                     index=[label for _, label, _ in METRICS[:3]])
st.bar_chart(chart, stack=False, height=300)

st.subheader("문항별로 누가 이겼나")
st.caption("근거 문장 포함(evid@5)을 문항마다 비교했습니다. 이 프로젝트에서는 같은 설정을 다시 돌려도 14문항 정도가 흔들리므로, "
           "좋아진 문항 수 − 나빠진 문항 수가 14를 넘어야 의미 있는 차이로 봅니다.")
base_m = metrics(RUNS[0][2])
gold = base_m["evid@5"].notna()
rows = []
for key, name, exp in RUNS[1:]:
    m = metrics(exp)
    d = (m.loc[gold[gold].index, "evid@5"] - base_m.loc[gold, "evid@5"])
    rows.append({"비교": f"{name} vs 세린님", "좋아진 문항": int((d > 0).sum()), "나빠진 문항": int((d < 0).sum()),
                 "같음": int((d == 0).sum()), "순증": int((d > 0).sum() - (d < 0).sum())})
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
for key, name, exp in RUNS[1:]:
    m = metrics(exp)
    d = (m.loc[gold[gold].index, "evid@5"] - base_m.loc[gold, "evid@5"])
    changed = d[d != 0]
    if len(changed):
        with st.expander(f"{name}: 달라진 {len(changed)}문항 보기"):
            st.dataframe(pd.DataFrame({"세린님 evid@5": base_m.loc[changed.index, "evid@5"],
                                       f"{name} evid@5": m.loc[changed.index, "evid@5"],
                                       "차이": changed}).round(3), width="stretch")

st.subheader("조각 크기")
data = chunk_data()
s = data["stats"]
cols = st.columns(3)
for col, (key, name, _) in zip(cols, RUNS):
    col.metric(f"조각 수 · {name}", f"{s[key]['n']:,}")
    col.caption(f"평균 {s[key]['mean']:.0f}자 · 중간값 {s[key]['median']}자 · 최대 {s[key]['max']:,}자 · "
                f"{MAX_CHARS:,}자 초과 {s[key]['over_max']}개")
bins = [0, 200, 400, 600, 800, 1000, 1200, 1600, 10_000]
labels = ["~200", "~400", "~600", "~800", "~1000", "~1200", "~1600", "1600 초과"]
hist = pd.DataFrame({name: pd.cut(pd.Series(s[key]["lens"]), bins, labels=labels).value_counts().reindex(labels)
                     for key, name, _ in RUNS[:2]})
st.bar_chart(hist, stack=False, height=280)
st.markdown('<div class="note">머리말이 있는 쪽의 1,600자 초과 7개는 본문이 아니라 머리말 한 줄(약 30~45자)이 더해진 것입니다. '
            '본문은 섞은 코드와 똑같이 최대 1,593자입니다.</div>', unsafe_allow_html=True)

st.subheader("길던 조각이 어떻게 달라졌나")
long_ = [c for c in data["chunks"]["serin"] if len(c["content"]) > MAX_CHARS]
pick = st.selectbox("세린님 방식에서 1,600자를 넘던 조각", range(len(long_)),
                    format_func=lambda i: f"{long_[i]['source']} p.{long_[i]['page']} · {len(long_[i]['content']):,}자")
c = long_[pick]
pages = set(c["pages"])
left, right = st.columns(2)
with left:
    st.markdown("#### 세린님: 한 조각")
    st.markdown(chunk_html(c, "long"), unsafe_allow_html=True)
with right:
    st.markdown("#### 섞은 코드 + 머리말: 나뉜 조각")
    head = c["content"][:60]
    hit = [x for x in data["chunks"]["header"] if x["source"] == c["source"] and set(x["pages"]) & pages]
    for x in hit:
        body = x["content"].split("\n", 1)[-1]
        if body[:40] in c["content"]:
            st.markdown(chunk_html(x, "picked"), unsafe_allow_html=True)

st.subheader("결론")
mx, hd = sums["mixed"], sums["header"]
st.markdown(f"""
- **잘린 조각**: 섞은 코드는 1,600자 넘는 조각을 없앴습니다(7개 → 0개). 조각 수는 {s['serin']['n']:,} → {s['mixed']['n']:,}개로 거의 같습니다.
- **검색 성적**: 섞은 코드(머리말 없음)는 근거 포함 {sums['serin']['evid@5']:.3f} → {mx['evid@5']:.3f}, 머리말까지 붙이면 {hd['evid@5']:.3f}입니다.
- 위 '문항별' 표의 순증이 ±14 안쪽이면 운에 따른 흔들림과 구별되지 않습니다.
""")
