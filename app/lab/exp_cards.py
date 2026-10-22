import streamlit as st

from lab.common import cards

st.title("🗂️ 실험 카드")
st.caption("실험마다 결과를 보기 전에 가설·측정 방법·채택 기준을 적고(1~4절), 결과와 결정을 나중에 채운(5~7절) 기록입니다.")

cs = cards()
st.dataframe([{"카드": c["file"], "제목": c["title"], "상태": c["status"]} for c in cs], width="stretch", hide_index=True)

pick = st.selectbox("읽을 카드", cs, format_func=lambda c: f"{c['file']} — {c['title']}")
st.markdown("---")
st.markdown(pick["text"])
