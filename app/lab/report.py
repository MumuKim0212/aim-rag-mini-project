import matplotlib
import streamlit as st

from lab.common import ROOT, picked, picked_note, picked_runs

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

from lab import report_build as R  # noqa: E402

st.title("📑 선택한 agent 성능 비교 리포트")
st.caption("'개요 › agent_list'에서 고른 agent들만 비교합니다. 첫 장은 어느 agent가 얼마나 나은지에 대한 의견과 결론이고, 이어서 "
           "비교 대상·흐름도·청킹·검색·답변·비용·실행 이력·한계 순서입니다. 수치와 문장은 고른 agent의 실행 결과에서 지금 만듭니다.")
picked_note()

sel, runs = picked(), picked_runs()
if len(runs) < 2:
    st.warning("비교하려면 agent_list에서 agent를 두 개 이상 고르고, 같은 문항 수로 실행한 결과가 있어야 합니다.")
    st.page_link("lab/agent_list.py", label="agent_list로 가기", icon="🤖")
    st.stop()

for f in (R.FONT, R.FONT_BOLD):
    if f.exists():
        font_manager.fontManager.addfont(str(f))
plt.rcParams.update({"font.family": "Malgun Gothic", "axes.unicode_minus": False})

with st.spinner("고른 agent의 결과·흐름도·청크를 모으는 중… (처음 한 번 수십 초)"):
    blocks = R.build(sel, runs)

c1, c2 = st.columns([3, 1])
c1.info("오른쪽 버튼으로 같은 내용을 A4 PDF로 받을 수 있습니다. PDF는 out/agent_report.pdf 에도 저장됩니다.")
key = "|".join(r["experiment"] for r in runs)
if c2.button("📄 PDF 만들기", type="primary", width="stretch"):
    with st.spinner("PDF를 만드는 중…"):
        data = R.pdf_bytes(blocks)
        (ROOT / "out").mkdir(exist_ok=True)
        (ROOT / "out" / "agent_report.pdf").write_bytes(data)
        st.session_state["report_pdf"] = (key, data)
saved = st.session_state.get("report_pdf")
if saved and saved[0] == key:  # only the PDF of the agents picked now
    c2.download_button("⬇ PDF 내려받기", saved[1], "선택한_agent_성능_비교_리포트.pdf", "application/pdf", width="stretch")

st.markdown("**목차** · " + " · ".join(b[1] for b in blocks if b[0] == "h1"))
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
        fig = plt.figure(figsize=(10, 3.2))
        b[1](fig, (0.06, 0.18, 0.92, 0.68))
        st.markdown(f"**{b[2]}**")
        st.pyplot(fig)
        plt.close(fig)
    elif kind == "images" and b[1]:
        st.markdown(f"**{b[2]}**")
        cols = st.columns(len(b[1]))
        for col, (png, cap) in zip(cols, b[1]):
            col.image(png, caption=cap)
