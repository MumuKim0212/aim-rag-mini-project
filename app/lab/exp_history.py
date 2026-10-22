import altair as alt
import pandas as pd
import streamlit as st

from lab.common import all_runs, colors, picked, picked_compare, picked_note, summary, summary_table

st.title("📈 점수 변화")
st.caption("위: agent_list에서 고른 agent별로 실행 회차에 따른 변화(같은 회차는 같은 위치, 같은 색끼리 선으로 연결). "
           "아래: 팀 실험을 실행한 순서대로, 무엇을 바꾼 실험인지 색으로 구분했습니다.")
picked_note()

METRIC_COLS = {"정답 점수": "correctness_mean", "완전 정답률": "fully_correct", "대응 일치율": "status_ok",
               "출처 일치율": "citation_on_target"}
metric = st.radio("지표", list(METRIC_COLS), horizontal=True)

# ---------------------------------------------------------------- agents: x = run number of that agent
sel = picked()
if sel:
    st.subheader("🤖 agent별 점수 변화 (실행 회차)")
    pts = []
    names = [f"{n}. {a['label']}" for n, a in enumerate(sel, 1)]
    for name, a in zip(names, sel):
        for i, r in enumerate(all_runs(a), 1):
            s = summary(r["experiment"])
            pts.append({"agent": name, "회차": i, "값": (s.get("scores") or {}).get(METRIC_COLS[metric]),
                        "문항 수": r["n"], "USD/문항": r["usd_per_question"], "p90 초": r["p90"], "실행": r["started"][5:16]})
    d = pd.DataFrame(pts)
    if d.empty:
        st.info("고른 agent의 실행 결과가 없습니다. agent_list에서 실행하세요.")
    else:
        lo = max(0.0, round(float(d["값"].min()) - 0.1, 1))  # a readable range even when every run scored 1.0
        enc = dict(x=alt.X("회차:O", title="실행 회차 (같은 회차 = 같은 위치)", axis=alt.Axis(labelAngle=0)),
                   y=alt.Y("값:Q", title=metric, scale=alt.Scale(domain=[lo, 1.0]), axis=alt.Axis(format=".2f")),
                   color=alt.Color("agent:N", scale=colors(names), title=None, legend=alt.Legend(orient="bottom")))
        base = alt.Chart(d).encode(**enc, detail="agent:N", tooltip=["agent", "회차", "값", "문항 수", "USD/문항", "p90 초", "실행"])
        chart = (base.mark_line(strokeWidth=3) + base.mark_point(size=110, filled=True)
                 + base.mark_text(dy=-14, fontSize=11).encode(text=alt.Text("문항 수:Q", format="d")))
        st.altair_chart(chart.properties(height=280), width="stretch")
        st.caption("선 하나 = agent 하나(같은 색끼리만 연결). 점 위 숫자 = 그 회차의 문항 수. 문항 수가 다른 회차끼리는 직접 비교하기 어렵습니다.")
    picked_compare("선택한 agent 최근 실행 나란히 보기")
    st.divider()

# ---------------------------------------------------------------- team experiments, colored by what changed
KIND = {"001": "청크 크기", "002": "청킹 방식", "003": "머리말", "004": "검색 방식", "005": "검색량 (k·MMR)", "006": "임베딩 모델",
        "007": "답변 모델", "008": "Agent", "010": "답변 프롬프트", "011": "작은 모델 + 프롬프트", "012": "답변 프롬프트",
        "013": "LLM 재정렬", "014": "Agent", "015": "Agent", "016": "답변 프롬프트"}
SHORT = {"dev_000_baseline": "처음 RAG", "dev_000_baseline_r2": "처음 RAG 재실행", "dev_013_rerank_flash36_fix": "재정렬 (T2)",
         "dev_013b_rerank_lite_fix": "재정렬+작은 모델 (T4)", "dev_008b_agent950": "Agent T3", "dev_014_agent_v2": "Agent v2"}


def kind_of(card) -> str:
    if not isinstance(card, str) or not card:
        return "기준 (처음 RAG)"
    return KIND.get(card.split("/")[-1][:3], "기타")


t = summary_table()
d = t[(t["split"] == "dev") & t["정답 점수"].notna() & (t["종류"] != "선택 agent")].sort_values("만든 시각").reset_index(drop=True)
d["순서"] = d.index + 1
d["바꾼 것"] = d["카드"].map(kind_of)
d["이름표"] = [SHORT.get(e, e.removeprefix("dev_")) for e in d["실험"]]
kinds = list(dict.fromkeys(d["바꾼 것"]))
kind_scale = alt.Scale(domain=kinds, scheme="tableau10")

st.subheader("팀 실험 점수 변화 (실행 순서)")
base = alt.Chart(d).encode(x=alt.X("순서:Q", title="실행 순서"),
                           tooltip=["순서", "실험", "바꾼 것", "설명", metric, "USD/문항", "p90 초"])
line = base.mark_line(color="#cbd5e1").encode(y=alt.Y(f"{metric}:Q", scale=alt.Scale(zero=False)))
dots = base.mark_circle(size=130).encode(y=f"{metric}:Q", color=alt.Color("바꾼 것:N", scale=kind_scale, title="바꾼 것",
                                                                          legend=alt.Legend(orient="right")))
text = base.mark_text(dy=-12, fontSize=10, color="#94a3b8").encode(y=f"{metric}:Q", text="이름표:N")
ref = alt.Chart(d).mark_rule(strokeDash=[4, 4], color="red").encode(y=alt.datum(0.722))
st.altair_chart((line + dots + text + ref).properties(height=380), width="stretch")
st.caption("점 색 = 그 실험에서 바꾼 것(오른쪽 범례), 점 위 글자 = 실험 이름. 빨간 점선 = 처음 RAG 정답 점수 0.722. "
           "같은 설정을 다시 돌리면 90문항 중 약 14문항이 바뀌므로 작은 차이는 잡음일 수 있습니다.")

st.subheader("비용과 점수")
team_pts = d[["순서", "실험", "이름표", "바꾼 것", "정답 점수", "USD/문항", "p90 초", "설명"]]
agent_pts = []
for n, a in enumerate(sel, 1):
    runs = all_runs(a)
    if runs:
        r = runs[-1]
        s = summary(r["experiment"])
        agent_pts.append({"실험": r["experiment"], "이름표": f"🤖 {n}", "agent": f"{n}. {a['label']}",
                          "정답 점수": s["scores"]["correctness_mean"], "USD/문항": r["usd_per_question"], "p90 초": r["p90"],
                          "설명": f"{r['n']}문항 · {a['description'][:80]}"})
x = alt.X("USD/문항:Q", title="문항당 비용 (USD)")
y = alt.Y("정답 점수:Q", scale=alt.Scale(zero=False))
tb = alt.Chart(team_pts).encode(x=x, y=y, tooltip=["실험", "바꾼 것", "정답 점수", "USD/문항", "p90 초", "설명"])
layers = [tb.mark_circle(size=140).encode(color=alt.Color("바꾼 것:N", scale=kind_scale, title="팀 실험: 바꾼 것")),
          tb.mark_text(dx=8, align="left", fontSize=10, color="#94a3b8").encode(text="이름표:N")]
if agent_pts:
    ap = pd.DataFrame(agent_pts)
    ab = alt.Chart(ap).encode(x=x, y=y, tooltip=["agent", "정답 점수", "USD/문항", "p90 초", "설명"])
    layers += [ab.mark_point(shape="diamond", filled=True, size=380, stroke="white", strokeWidth=1.5).encode(
                   color=alt.Color("agent:N", scale=colors(list(ap["agent"])), title="🤖 agent (최근 실행)")),
               ab.mark_text(dx=12, align="left", fontSize=12, fontWeight="bold", color="#e2e8f0").encode(text="이름표:N")]
st.altair_chart(alt.layer(*layers).resolve_scale(color="independent").properties(height=380), width="stretch")
st.caption("왼쪽 위로 갈수록 싸고 정확합니다. 동그라미 = 팀 실험(색 = 바꾼 것, 옆 글자 = 실험 이름), 큰 마름모 = 고른 agent(🤖 번호, 최근 실행).")

with st.expander("실험 목록 (순서·바꾼 것·설명)"):
    st.dataframe(d[["순서", "실험", "바꾼 것", "정답 점수", "완전 정답률", "대응 일치율", "USD/문항", "p90 초", "설명"]],
                 width="stretch", hide_index=True)
