import json
import subprocess
import sys

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
ASSETS = ROOT / "out" / "doc_assets.json"


@st.cache_data
def assets(mtime: float) -> dict:
    return {(r["file"], r["page"]): r for r in json.loads(ASSETS.read_text(encoding="utf-8"))}


if not ASSETS.exists():
    st.warning("표·이미지 정보가 아직 없습니다 (`out/doc_assets.json`). PDF에서 표와 이미지를 찾는 데 약 1~2분 걸립니다(API 없음).")
    if st.button("표·이미지 정보 만들기"):
        with st.spinner("PDF에서 표와 이미지를 찾는 중…"):
            subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "scripts" / "doc_assets.py")], cwd=ROOT)
        st.rerun()
A = assets(ASSETS.stat().st_mtime) if ASSETS.exists() else {}

df = pd.DataFrame([{
    "파일": p["file"], "문서 제목": title_of(p["file"], cfg), "페이지": p["page"], "글자 수": len(p["text"]),
    "VLM 보충": p.get("visual_mode") == "added", "색인 대상": indexable(p, cfg), "범위 A": in_scope(p, cfg, "A"),
    "PDF 표": A.get((p["file"], p["page"]), {}).get("pdf_tables", 0),
    "이미지": A.get((p["file"], p["page"]), {}).get("images", p.get("images", 0)),
    "VLM 표": A.get((p["file"], p["page"]), {}).get("vlm_tables", 0),
    "VLM 그림": A.get((p["file"], p["page"]), {}).get("vlm_figures", 0),
} for p in pg])

kpi_row([
    ("PDF", f"{df['파일'].nunique()}개", None),
    ("페이지", f"{len(df)}쪽", None),
    ("PDF 속 표", f"{int(df['PDF 표'].sum())}개", "PyMuPDF가 PDF 구조에서 찾은 표"),
    ("PDF 속 이미지", f"{int(df['이미지'].sum())}개", "페이지에 들어 있는 그림 파일"),
    ("VLM이 글로 옮긴 표·그림", f"{int(df['VLM 표'].sum())} · {int(df['VLM 그림'].sum())}", f"표·그림이 있는 범위 B 페이지 {int(df['VLM 보충'].sum())}쪽 ({info.get('visual', {}).get('model')})"),
])

st.subheader("검색 범위")
st.markdown("""
| 범위 | 포함 문서 | 쓰는 질문 |
|---|---|---|
| **A** | 용어집 + 표준약관 15개 | 기본 질문, 함정 질문 |
| **B** | 23개 전부 (A + 가이드북, 주택연금, 퇴직연금, 보험, 정책금융, 자영업자 보고서) | 생활 가이드, 추가 자료, 자작 질문 |

질문마다 골든셋의 `set` 값으로 범위가 자동으로 정해집니다(`configs/baseline.yaml`의 `set_scope`).
""")

st.subheader("문서별 페이지·표·이미지")
by_doc = df.groupby(["파일", "문서 제목"]).agg(
    페이지=("페이지", "count"), 글자=("글자 수", "sum"),
    PDF_표=("PDF 표", "sum"), 표_있는_쪽=("PDF 표", lambda s: int((s > 0).sum())),
    이미지=("이미지", "sum"), 이미지_있는_쪽=("이미지", lambda s: int((s > 0).sum())),
    VLM_보충_쪽=("VLM 보충", "sum"), VLM_표=("VLM 표", "sum"), VLM_그림=("VLM 그림", "sum"),
    색인_제외=("색인 대상", lambda s: int((~s).sum())), 범위=("범위 A", lambda s: "A·B" if s.all() else "B")).reset_index()
by_doc.columns = [c.replace("_", " ") for c in by_doc.columns]
st.dataframe(by_doc.sort_values("PDF 표", ascending=False), width="stretch", hide_index=True)
st.caption("PDF 표·이미지 = PDF 파일 구조에서 찾은 개수. VLM 표·그림 = 표·그림이 있는 범위 B 페이지를 이미지 모델이 읽고 글(표는 `| … |` 형식)로 "
           "옮겨 페이지 텍스트 뒤에 붙인 개수. 용어집·약관(범위 A)은 표·그림이 거의 없어 VLM을 쓰지 않았습니다.")

long = by_doc.melt(id_vars=["문서 제목"], value_vars=["PDF 표", "이미지", "VLM 표", "VLM 그림"], var_name="종류", value_name="개수")
st.altair_chart(alt.Chart(long[long["개수"] > 0]).mark_bar().encode(
    y=alt.Y("문서 제목:N", sort="-x", title=None), x=alt.X("개수:Q"), color=alt.Color("종류:N", title=None),
    yOffset="종류:N", tooltip=["문서 제목", "종류", "개수"]).properties(height=520), width="stretch")

st.subheader("페이지 내용 보기")
c1, c2 = st.columns([2, 1])
file = c1.selectbox("문서", sorted(df["파일"].unique()))
rows_f = df[df["파일"] == file]
n = int(rows_f["페이지"].max())
with_assets = rows_f[(rows_f["PDF 표"] > 0) | (rows_f["이미지"] > 0)]["페이지"].tolist()
page = c2.number_input("페이지", 1, n, int(with_assets[0]) if with_assets else 1,
                       help=f"표·이미지가 있는 쪽: {', '.join(map(str, with_assets[:30]))}{' …' if len(with_assets) > 30 else ''}")
p = next(x for x in pg if x["file"] == file and x["page"] == page)
a = A.get((file, page), {})
k = st.columns(5)
k[0].metric("글자 수", f"{len(p['text']):,}")
k[1].metric("PDF 표", a.get("pdf_tables", 0), " · ".join(a.get("pdf_table_shapes", [])) or None, delta_color="off",
            help="행 x 열")
k[2].metric("이미지", a.get("images", p.get("images", 0)))
k[3].metric("VLM 표 · 그림", f"{a.get('vlm_tables', 0)} · {a.get('vlm_figures', 0)}")
k[4].metric("색인 대상", "예" if indexable(p, cfg) else "아니요")
t1, t2, t3 = st.tabs(["색인에 쓰는 텍스트", "PDF 텍스트 레이어만", "VLM이 옮긴 표·그림"])
t1.text(p["text"])
t2.text(p.get("text_layer") or "(없음)")
t3.markdown(p.get("visual") or "(이 페이지는 VLM 보충이 없습니다)")
