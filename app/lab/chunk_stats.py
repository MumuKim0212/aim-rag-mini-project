import altair as alt
import pandas as pd
import streamlit as st


from lab.common import BA, ROOT, agent_bars, chunk_frame, colors, kpi_row, pages, picked, picked_note, picked_runs, styled

st.title("✂️ 청킹 방식별 청크")
st.caption("같은 페이지 텍스트를 청킹 방식마다 어떻게 나누는지 비교합니다. 코드로 바로 청킹하므로 API를 쓰지 않습니다.")
picked_note()
@st.cache_data(show_spinner="그 브랜치 코드로 청킹하는 중… (agent마다 처음 한 번 5~10초)")
def agent_chunks(sha: str, config: str) -> list[dict]:
    return BA.chunks_of(sha, config)


if picked():
    st.subheader("🤖 선택한 agent별 청킹")
    st.caption("각 agent의 브랜치 코드(그 브랜치의 chunking.py)와 그 agent 설정으로 같은 페이지(범위 B 전체)를 직접 청킹한 결과입니다.")
    sel = picked()
    names = [f"{n}. {a['label']}" for n, a in enumerate(sel, 1)]
    ch_by = {name: agent_chunks(a["sha"], a["config"]) for name, a in zip(names, sel)}
    stat = {}
    for name, a in zip(names, sel):
        c, lens = a["chunking"], pd.Series([x["chars"] for x in ch_by[name]])
        stat[name] = {"청킹 방식": c.get("method"), "크기 / 겹침": f"{c.get('chunk_size')} / {c.get('chunk_overlap')}",
                      "조항 최대 글자": c.get("max_chars", "–"), "머리말": c.get("add_header", False), "청크 수": len(lens),
                      "평균 길이": round(lens.mean()), "중앙값": int(lens.median()), "최대": int(lens.max()),
                      "페이지를 넘는 청크": sum(len(x["pages"]) > 1 for x in ch_by[name]),
                      "만든 사람 · 커밋": f"{a.get('maker', '-')} · {a['commit']}"}
    st.dataframe(pd.DataFrame(stat).astype(str), width="stretch")
    if len(sel) >= 2:
        base = {(x["chunk_id"], x["content"]) for x in ch_by[names[0]]}
        for name in names[1:]:
            other = {(x["chunk_id"], x["content"]) for x in ch_by[name]}
            same = len(base & other)
            (st.success if same == len(base) == len(other) else st.info)(
                f"{names[0]} 와 {name}: 청크 {len(base):,}개 / {len(other):,}개 중 {same:,}개가 완전히 같습니다"
                + (" → 두 agent의 청킹은 똑같습니다(차이는 검색 이후 단계에서 납니다)." if same == len(base) == len(other) else "."))
    dist = pd.DataFrame([{"agent": name, "길이": x["chars"]} for name in names for x in ch_by[name]])
    st.markdown("**청크 길이 분포** (agent마다 따로, 같은 축)")
    st.altair_chart(alt.Chart(dist).mark_bar().encode(
        x=alt.X("길이:Q", bin=alt.Bin(maxbins=30), title="청크 길이 (글자)"), y=alt.Y("count()", title="청크 수"),
        color=alt.Color("agent:N", scale=colors(names), legend=None), tooltip=["agent", "count()"]
    ).properties(width=300, height=200).facet(column=alt.Column("agent:N", title=None, sort=names)))

    st.markdown("**같은 페이지를 agent마다 어떻게 나눴는지**")
    files = sorted({x["source"] for x in ch_by[names[0]]})
    c1, c2 = st.columns([3, 1])
    file = c1.selectbox("문서", files, key="agent_chunk_file")
    pages_ = sorted({x["page"] for name in names for x in ch_by[name] if x["source"] == file})
    page = c2.selectbox("시작 페이지", pages_, key="agent_chunk_page")
    cols = st.columns(len(names))
    for col, name in zip(cols, names):
        with col:
            here = [x for x in ch_by[name] if x["source"] == file and x["page"] == page]
            st.markdown(f"**{name}** · {len(here)}개")
            for x in here:
                with st.expander(f"{x['chars']}자 · 쪽 {x['pages']}"):
                    st.text(x["content"])

    runs = picked_runs()
    if runs:
        df, common = chunk_frame(runs)
        st.markdown(f"**실행 결과로 본 청킹 수치** (함께 푼 dev 문항 {len(common)}개, agent마다 한 열)")
        st.dataframe(styled(df, "{:,.3f}"), width="stretch")
        agent_bars(df, ["정답 페이지 포함", "근거 문장 포함률", "문항당 넘긴 조각 수", "조각 평균 길이", "문항당 문맥 글자 수"])
    st.divider()

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

picked_methods = st.multiselect("길이 분포를 볼 방식", list(CHUNKERS), default=list(CHUNKERS)[:1] + list(CHUNKERS)[3:5])
if picked_methods:
    dist = pd.DataFrame([{"방식": n, "길이": len(c["content"])} for n in picked_methods for c in chunk(CHUNKERS[n], scope)])
    st.altair_chart(alt.Chart(dist).mark_bar().encode(
        x=alt.X("길이:Q", bin=alt.Bin(maxbins=30), title="청크 길이 (글자)"), y=alt.Y("count()", title="청크 수"),
        color=alt.Color("방식:N", legend=None), tooltip=["방식", "count()"]
    ).properties(width=260, height=180).facet(facet=alt.Facet("방식:N", title=None, sort=picked_methods), columns=3))
    st.caption("방식마다 따로 그린 막대입니다(같은 축). 막대가 오른쪽으로 갈수록 긴 청크가 많습니다.")

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
