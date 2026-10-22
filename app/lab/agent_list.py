import pandas as pd
import streamlit as st

from lab.common import BA, branch_agents, duplicate_agents, latest_run, picked_runs

st.title("🤖 agent_list")
st.caption("GitHub 저장소 aim-rag-mini-project의 모든 브랜치(main 포함)에서 agent 파일(LangGraph 그래프를 만드는 코드, "
           "src/rag/systems.py에 등록된 것)을 찾습니다. 브랜치의 다른 파일이 언제 올라왔는지와 상관없이, 브랜치마다 agent 파일이나 "
           "그 설정을 마지막으로 올린 agent 하나를 고르고, 같은 agent가 여러 브랜치에 있으면(병합·복사) 한 번만 보여 줍니다. "
           "고른 agent는 아래 메뉴에 자동으로 함께 나옵니다.")

c1, c2 = st.columns([4, 1])
if c2.button("🔄 목록 새로고침", width="stretch"):
    branch_agents(force=True)
agents = branch_agents()
c1.caption(f"마지막 조회: {st.session_state.get('branch_agents_at')} · 브랜치 {len(agents)}개 (앱을 열 때마다 자동으로 다시 조회)")
if st.session_state.get("branch_agents_note"):
    st.warning(st.session_state.branch_agents_note)

chosen = set(st.session_state.get("picked_agents", []))
same = pd.Series([a["same_code_id"] for a in agents]).value_counts()
table = pd.DataFrame([{
    "선택": a["label"] in chosen, "agent": a["label"], "agent 파일": a.get("impl", ""), "설정": a["config"].removesuffix(".yaml"),
    "만든 사람": a.get("maker", ""), "올라온 시각": a["added_at"], "커밋": a["commit"], "브랜치 마지막 커밋": a["author"],
    "답변 모델": a["answer_model"],
    "결과": (lambda r, old: f"{r['n']}문항 · {r['correctness']:.3f}" if r else ("이전 버전 결과만 있음" if old else "없음"))(
        latest_run(a), latest_run(a, exact=False)),
    "같은 코드": f"{a['same_code_id']} ({same[a['same_code_id']]}개 같음)" if same[a["same_code_id"]] > 1 else a["same_code_id"],
    "설명": a["description"],
} for a in agents])
edited = st.data_editor(table, hide_index=True, width="stretch", key="agent_list_editor",
                        disabled=[c for c in table.columns if c != "선택"],
                        column_config={"선택": st.column_config.CheckboxColumn("선택", help="여러 개 고를 수 있습니다")})
picked_now = [a["label"] for a, on in zip(agents, edited["선택"]) if on]
if picked_now != st.session_state.get("picked_agents"):
    st.session_state.picked_agents = picked_now
    st.rerun()
dups = duplicate_agents()
if dups:
    with st.expander(f"자기 agent가 없는 브랜치 {len(dups)}개 (같은 agent를 병합으로 가지고 있어 목록에서 한 번만 보여 줌)"):
        st.dataframe(pd.DataFrame([{"브랜치": d["branch"], "커밋": d["commit"], "브랜치 마지막 커밋": d["author"],
                                    "가지고 있는 agent": d["config"].removesuffix(".yaml"), "만든 사람": d["maker"],
                                    "목록에서는": d["same_as"]} for d in dups]), hide_index=True, width="stretch")
st.caption("'만든 사람'은 그 agent 설정을 처음 커밋한 사람입니다. 다른 사람의 agent 파일을 비교용으로 복사해 온 것은 "
           "그 브랜치의 agent로 치지 않고, 브랜치마다 그 브랜치에 원래 있던 agent 중 가장 최근 것을 보여 줍니다.")
st.caption("'결과'는 이 PC에서 지금 목록의 agent(같은 코드·설정)를 마지막으로 실행한 결과(dev)입니다. 브랜치에 새 커밋이 올라와 "
           "코드가 바뀌면 '이전 버전 결과만 있음'으로 표시되고 다시 실행해야 비교에 들어갑니다. '같은 코드'가 같은 agent끼리는 "
           "코드와 설정이 완전히 같습니다.")

st.subheader("선택한 agent")
sel = [a for a in agents if a["label"] in picked_now]
if not sel:
    st.info("표에서 '선택'을 체크하세요. 여러 개 고를 수 있습니다.")
    st.stop()

runs = {r["label"]: r for r in picked_runs()}
st.dataframe(pd.DataFrame([{
    "번호": n, "agent": a["label"], "결과": "✅ 있음" if a["label"] in runs else "⬜ 없음",
    "문항 수": runs[a["label"]]["n"] if a["label"] in runs else None,
    "정답 점수": runs[a["label"]]["correctness"] if a["label"] in runs else None,
    "USD/문항": runs[a["label"]]["usd_per_question"] if a["label"] in runs else None,
    "실행 시각": runs[a["label"]]["started"] if a["label"] in runs else None,
} for n, a in enumerate(sel, 1)]), hide_index=True, width="stretch")
st.caption("결과가 있는 agent는 바로 아래 메뉴들에 반영됩니다. 번호는 모든 페이지에서 같습니다.")

missing = [a for a in sel if a["label"] not in runs]
st.markdown("**QA 데이터 만들기 (dev 문항으로 실행·채점)**")
target = st.radio("실행할 agent", ["결과 없는 agent만", "선택한 agent 전부 (같은 문항으로 다시)"], horizontal=True)
todo = missing if target.startswith("결과 없는") else sel
c1, c2 = st.columns(2)
limit = c1.select_slider("dev 문항 수 (앞에서부터, 모든 agent가 같은 문항)", [5, 10, 20, 30, 45, 90], value=10)
est = sum((0.004 if "lite" in str(a["answer_model"]) else 0.011) + 0.0015 for a in todo) * limit
c2.metric("예상 비용 (채점 포함)", f"{est:.2f} USD", f"agent {len(todo)}개 × {limit}문항", delta_color="off")
st.caption("같은 문항 수로 실행해야 정확히 비교됩니다(공통 문항만 비교). 동시에 3개까지 실행하고 나머지는 대기합니다. "
           "앱을 닫아도 실행은 끝까지 진행됩니다. test 문항은 쓰지 않습니다.")
if st.button(f"▶ agent {len(todo)}개 실행", type="primary", disabled=not todo):
    for a in todo:
        st.toast(f"시작: {a['label']} → {BA.start(a, limit, None)}")


@st.fragment(run_every="5s")
def status():
    jobs = [j for j in BA.jobs() if (j.get("entry") or {}).get("label") in picked_now][:12]
    if not jobs:
        return
    st.markdown("**실행 상태** (5초마다 갱신)")
    steps = {"queued": "대기", "checkout": "브랜치 코드 준비", "index": "인덱스 확인", "run": "답변 생성", "grade": "채점",
             "evaluate": "지표 계산", "done": "완료"}
    st.dataframe(pd.DataFrame([{
        "agent": j["entry"]["label"],
        "상태": {"running": "⏳ 실행 중", "queued": "⏳ 대기", "done": "✅ 완료", "failed": "❌ 실패", "stopped": "⏹ 중단됨"}.get(j.get("status")),
        "단계": steps.get(j.get("step"), j.get("step")),
        "진행": f"{j.get('done_questions', '')}/{j.get('limit') or 90}" if j.get("status") == "running" else "",
        "시작": j.get("started"), "실험": j["experiment"]} for j in jobs]), hide_index=True, width="stretch")
    if any(j.get("status") == "done" for j in jobs) and st.button("결과 반영 (새로고침)"):
        st.rerun(scope="app")


status()
