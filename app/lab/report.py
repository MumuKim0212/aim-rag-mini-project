import matplotlib
import streamlit as st

from lab.common import ROOT

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

from lab import report_build as R  # noqa: E402

st.title("📑 실습 리포트")
st.caption("이번 실습에서 한 모든 실험을 한 문서로 정리했습니다. 첫 장은 실험 전체에 대한 의견과 결론이고, 이어서 데이터·실험 과정·Agent·최종 test·"
           "한계 순서입니다. 수치는 results/와 out/agent_runs/에서 지금 다시 읽은 값입니다.")

for f in (R.FONT, R.FONT_BOLD):
    if f.exists():
        font_manager.fontManager.addfont(str(f))
plt.rcParams.update({"font.family": "Malgun Gothic", "axes.unicode_minus": False})

blocks = R.build()

c1, c2 = st.columns([3, 1])
c1.info("오른쪽 버튼으로 같은 내용을 A4 PDF로 받을 수 있습니다. PDF는 out/report.pdf 에도 저장됩니다.")
if c2.button("📄 PDF 만들기", type="primary", width="stretch"):
    with st.spinner("PDF를 만드는 중…"):
        data = R.pdf_bytes(blocks)
        (ROOT / "out").mkdir(exist_ok=True)
        (ROOT / "out" / "report.pdf").write_bytes(data)
        st.session_state["report_pdf"] = data
if st.session_state.get("report_pdf"):
    c2.download_button("⬇ PDF 내려받기", st.session_state["report_pdf"], "금융문서_RAG_실습_리포트.pdf", "application/pdf",
                       width="stretch")

toc = [b[1] for b in blocks if b[0] == "h1"]
st.markdown("**목차** · " + " · ".join(toc))
st.divider()

for b in blocks:
    kind = b[0]
    if kind == "h1":
        st.header(b[1])
    elif kind == "h2":
        st.subheader(b[1])
    elif kind == "p":
        st.write(b[1])
    elif kind == "note":
        st.success(b[1])
    elif kind == "bullets":
        st.markdown("\n".join(f"- {x}" for x in b[1]))
    elif kind == "table":
        st.markdown(f"**{b[2]}**")
        st.dataframe(b[1].astype(str), hide_index=True, width="stretch")  # report tables are display text
    elif kind == "chart":
        fig, ax = plt.subplots(figsize=(9, 3.6))
        b[1](ax)
        fig.tight_layout()
        st.markdown(f"**{b[2]}**")
        st.pyplot(fig)
        plt.close(fig)
