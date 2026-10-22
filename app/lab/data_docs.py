import json

import altair as alt
import pandas as pd
import streamlit as st

from lab.common import ROOT, kpi_row, pages

st.title("📄 문서와 페이지 추출")
st.caption("PDF를 페이지별 텍스트로 뽑은 결과(`corpus/pages.jsonl`)입니다. 팀 전체가 이 파일 하나로 청킹하므로 모든 실험의 출발점이 같습니다.")

from rag.config import BASELINE, load_config  # noqa: E402
from rag.ingest import in_scope, indexable, title_of  # noqa: E402

cfg = load_config(BASELINE)
pg = pages()
info = json.loads((ROOT / "corpus" / "extraction.json").read_text(encoding="utf-8"))

df = pd.DataFrame([{
    "파일": p["file"], "문서 제목": title_of(p["file"], cfg), "페이지": p["page"], "글자 수": len(p["text"]),
    "텍스트 레이어 글자": len(p.get("text_layer") or ""), "VLM 보충": p.get("visual_mode") == "added",
    "색인 대상": indexable(p, cfg), "범위 A": in_scope(p, cfg, "A"),
} for p in pg])

kpi_row([
    ("PDF", f"{df['파일'].nunique()}개", None),
    ("페이지", f"{len(df)}쪽", None),
    ("VLM으로 보충한 페이지", f"{int(df['VLM 보충'].sum())}쪽", f"표·그림 속 글자 ({info.get('visual', {}).get('model')})"),
    ("색인에서 뺀 페이지", f"{int((~df['색인 대상']).sum())}쪽", "용어집·약관 끝의 출처(URL) 목록"),
])

st.subheader("검색 범위")
st.markdown("""
| 범위 | 포함 문서 | 쓰는 질문 |
|---|---|---|
| **A** | 용어집 + 표준약관 15개 | 기본 질문, 함정 질문 |
| **B** | 23개 전부 (A + 가이드북, 주택연금, 퇴직연금, 보험, 정책금융, 자영업자 보고서) | 생활 가이드, 추가 자료, 자작 질문 |

질문마다 골든셋의 `set` 값으로 범위가 자동으로 정해집니다(`configs/baseline.yaml`의 `set_scope`).
""")

st.subheader("문서별 페이지")
by_doc = df.groupby(["파일", "문서 제목"]).agg(
    페이지=("페이지", "count"), 글자=("글자 수", "sum"), VLM_보충=("VLM 보충", "sum"),
    색인_제외=("색인 대상", lambda s: int((~s).sum())), 범위=("범위 A", lambda s: "A·B" if s.all() else "B")).reset_index()
st.dataframe(by_doc, width="stretch", hide_index=True)
st.altair_chart(alt.Chart(by_doc).mark_bar().encode(
    x=alt.X("글자:Q", title="글자 수"), y=alt.Y("문서 제목:N", sort="-x", title=None),
    color=alt.Color("범위:N", title="범위"), tooltip=["파일", "페이지", "글자", "VLM_보충"]), width="stretch")

st.subheader("페이지 내용 보기")
c1, c2 = st.columns([2, 1])
file = c1.selectbox("문서", sorted(df["파일"].unique()))
n = int(df[df["파일"] == file]["페이지"].max())
page = c2.number_input("페이지", 1, n, 1)
p = next(x for x in pg if x["file"] == file and x["page"] == page)
st.caption(f"글자 {len(p['text']):,}자 · 텍스트 레이어 {len(p.get('text_layer') or ''):,}자 · "
           f"VLM 보충: {'예' if p.get('visual_mode') == 'added' else '아니요'} · 색인 대상: {'예' if indexable(p, cfg) else '아니요'}")
t1, t2 = st.tabs(["색인에 쓰는 텍스트", "PDF 텍스트 레이어만"])
t1.text(p["text"])
t2.text(p.get("text_layer") or "(없음)")
