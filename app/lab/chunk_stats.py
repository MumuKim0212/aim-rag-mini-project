import altair as alt
import pandas as pd
import streamlit as st

from lab.common import ROOT, kpi_row, pages

st.title("✂️ 청킹 방식별 청크")
st.caption("같은 페이지 텍스트를 청킹 방식마다 어떻게 나누는지 비교합니다. 코드로 바로 청킹하므로 API를 쓰지 않습니다.")

CHUNKERS = {
    "처음 기준: Recursive 800/100": "configs/baseline.yaml",
    "Recursive 1000/125": "configs/001c-chunk1000.yaml",
    "구조 단위 + Recursive 900/112": "configs/002b-structure-900.yaml",
    "최종: 구조 단위 + Recursive 950/119": "configs/008b-agent-950.yaml",
    "혼합: 최종 + 글자 수 상한 자르기": "configs/014-mixed-chunk.yaml",
    "혼합 + 머리말 [문서 | 쪽 | 조항]": "configs/014b-mixed-chunk-header.yaml",
}


@st.cache_data(show_spinner="청킹하는 중…")
def chunk(config: str, scope: str) -> list[dict]:
    from rag.chunking import chunk_pages
    from rag.config import load_config
    from rag.ingest import in_scope, indexable
    cfg = load_config(ROOT / config)
    pg = [p for p in pages() if indexable(p, cfg) and in_scope(p, cfg, scope)]
    return chunk_pages(pg, cfg)


scope = st.radio("검색 범위", ["B", "A"], horizontal=True,
                 format_func=lambda s: {"A": "A (용어집 + 약관)", "B": "B (전체 23개)"}[s])
stats = []
for name, config in CHUNKERS.items():
    ch = chunk(config, scope)
    lens = pd.Series([len(c["content"]) for c in ch])
    stats.append({"방식": name, "청크 수": len(ch), "평균 길이": round(lens.mean()), "중앙값": int(lens.median()),
                  "최대": int(lens.max()), "페이지를 넘는 청크": sum(len(c.get("pages") or [c["page"]]) > 1 for c in ch),
                  "설정": config})
stats = pd.DataFrame(stats)
st.dataframe(stats, width="stretch", hide_index=True)
st.caption("구조 단위 청킹은 용어집을 용어 1개, 약관을 조 1개씩 나누고 나머지 문서는 Recursive로 자릅니다. "
           "혼합은 너무 긴 조항을 글자 수 상한에서 한 번 더 자릅니다(`chunking.hard_cap`, 혼합 설정에서만 켜짐).")

picked = st.multiselect("길이 분포를 볼 방식", list(CHUNKERS), default=list(CHUNKERS)[:1] + list(CHUNKERS)[3:5])
if picked:
    dist = pd.DataFrame([{"방식": n, "길이": len(c["content"])} for n in picked for c in chunk(CHUNKERS[n], scope)])
    st.altair_chart(alt.Chart(dist).mark_bar(opacity=0.6).encode(
        x=alt.X("길이:Q", bin=alt.Bin(maxbins=40), title="청크 길이 (글자)"),
        y=alt.Y("count()", stack=None, title="청크 수"), color=alt.Color("방식:N")), width="stretch")

st.subheader("같은 페이지가 어떻게 나뉘는지")
c1, c2, c3 = st.columns([2, 2, 1])
name = c1.selectbox("방식", list(CHUNKERS), index=3)
ch = chunk(CHUNKERS[name], scope)
files = sorted({c["source"] for c in ch})
file = c2.selectbox("문서", files)
in_file = [c for c in ch if c["source"] == file]
page = c3.selectbox("시작 페이지", sorted({c["page"] for c in in_file}))
shown = [c for c in in_file if c["page"] == page]
kpi_row([("이 페이지에서 시작하는 청크", f"{len(shown)}개", None),
         ("문서 전체 청크", f"{len(in_file)}개", None)])
for c in shown:
    with st.expander(f"{c['chunk_id']} · {len(c['content'])}자 · 페이지 {c.get('pages') or [c['page']]}"):
        st.text(c["content"])
