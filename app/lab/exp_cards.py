import streamlit as st

import re

from lab.common import BA, cards, picked, picked_note

st.title("🗂️ 실험 카드")
st.caption("실험마다 결과를 보기 전에 가설·측정 방법·채택 기준을 적고(1~4절), 결과와 결정을 나중에 채운(5~7절) 기록입니다.")
picked_note()
for n, a in enumerate(picked(), 1):
    with st.expander(f"🤖 {n}. {a['label']} — 그 브랜치의 카드 {a.get('card') or '(없음)'}"):
        text = BA.git("show", f"{a['sha']}:{a['card']}", check=False) if a.get("card") else ""
        st.markdown(re.sub(r"<!--.*?-->", "", text, flags=re.S) or "이 agent 설정에는 카드가 연결되어 있지 않습니다.")

cs = cards()
st.dataframe([{"카드": c["file"], "제목": c["title"], "상태": c["status"]} for c in cs], width="stretch", hide_index=True)

pick = st.selectbox("읽을 카드", cs, format_func=lambda c: f"{c['file']} — {c['title']}")
st.markdown("---")
st.markdown(pick["text"])
