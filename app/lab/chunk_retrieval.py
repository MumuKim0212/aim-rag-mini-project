import altair as alt
import pandas as pd
import streamlit as st

from lab.common import (HIGHER, LOWER, agent_bars, chunk_frame, paired, picked_note, picked_runs, rows, styled, summary,
                        summary_table)

st.title("🔍 청킹·검색 비교 (LLM 없이)")
st.caption("답변을 만들지 않고 검색 결과만 채점한 실험들입니다(`--retrieval-only`). 정답 페이지와 근거 문장이 "
           "검색 결과 상위 5개에 들어왔는지로 청킹·검색 방식을 비교합니다. 비용은 질문 임베딩뿐입니다.")
picked_note()

with st.expander("지표 설명"):
    st.markdown("""
| 지표 | 뜻 |
|---|---|
| 정답 페이지 포함 (page_hit) | 검색 결과(답변에 넘긴 청크) 중 정답 페이지의 청크가 하나라도 있는 문항 비율 |
| 근거 문장 포함률 (evid) | 골든셋 근거 문장이 넘긴 청크에 글자 그대로 들어 있는 비율 (문항 평균) |
| MRR | 처음 나온 정답 청크 순위의 역수 평균 (1위면 1, 2위면 0.5) |
| 정답 청크 수 (gold) | 넘긴 청크 중 정답 페이지 청크의 수 |
| 문맥 글자 수 | 답변 단계에 넘어갈 글자 수 (길수록 근거는 많이 담지만 비용·지연 증가) |

검색만 한 실험은 상위 5개 기준이고, agent는 재검색으로 늘린 최종 문맥 기준입니다. 둘 다 LLM 채점 없이 코드로 계산합니다.
""")

runs = picked_runs()
METRICS = {"page_hit": "정답 페이지 포함", "evid": "근거 문장 포함률", "mrr": "MRR", "gold": "정답 청크 수",
           "chars": "문맥 글자 수"}

# ---------------------------------------------------------------- agents, one column each
if runs:
    st.subheader("🤖 선택한 agent별 실험 내용과 근거 문장 포함률")
    content = {}
    for r in runs:
        s = summary(r["experiment"])
        c = s.get("config") or {}
        ch, rt = c.get("chunking", {}), c.get("retrieval", {})
        content[r["name"]] = {"설명": s.get("description", ""), "설정 파일": f"{r['branch']} · {r['config']}",
                              "청킹": f"{ch.get('method')} {ch.get('chunk_size')}/{ch.get('chunk_overlap')}",
                              "검색": f"{rt.get('method')} k={rt.get('k')}" + (f", 재정렬 후보 {rt['rerank_pool']}" if rt.get("rerank_pool") else ""),
                              "답변 모델": (c.get("answer") or {}).get("model"), "실행": f"{r['n']}문항 · {r['started'][5:16]}"}
    st.dataframe(pd.DataFrame(content).astype(str), width="stretch")
    df_, common_ = chunk_frame(runs)
    st.dataframe(styled(df_, "{:,.3f}"), width="stretch")
    agent_bars(df_, ["근거 문장 포함률", "정답 페이지 포함", "MRR", "검색/문항"])
    st.caption(f"함께 푼 dev 문항 {len(common_)}개 기준. 초록 = 가장 좋은 agent, 빨강 = 가장 나쁜 agent.")
    st.divider()

# ---------------------------------------------------------------- retrieval-only experiments
t = summary_table()
r = t[(t["split"] == "dev") & (t["종류"] == "검색만")].copy()
r = r[["실험", "설명", "정답 페이지 포함", "근거 문장 포함률", "MRR", "문맥 글자 수", "카드"]].sort_values("근거 문장 포함률", ascending=False)
st.subheader("검색만 비교한 실험 (팀 실험)")
st.dataframe(r.style.format({"정답 페이지 포함": "{:.3f}", "근거 문장 포함률": "{:.3f}", "MRR": "{:.3f}",
                             "문맥 글자 수": "{:,.0f}"}), width="stretch", hide_index=True)
st.altair_chart(alt.Chart(r).mark_circle(size=120).encode(
    x=alt.X("문맥 글자 수:Q", scale=alt.Scale(zero=False)), y=alt.Y("근거 문장 포함률:Q", scale=alt.Scale(zero=False)),
    color=alt.Color("정답 페이지 포함:Q", scale=alt.Scale(scheme="viridis")),
    tooltip=["실험", "설명", "정답 페이지 포함", "근거 문장 포함률", "MRR", "문맥 글자 수"]), width="stretch")
st.caption("오른쪽 위로 갈수록 근거는 많이 담지만 문맥이 길어집니다. 왼쪽 위가 효율이 좋은 방식입니다.")

# ---------------------------------------------------------------- baseline vs every picked agent
st.subheader("두 방식 짝비교: 기준 vs 선택한 agent")
options = r["실험"].tolist()
default = options.index("dev_001e_chunk950chain_retrieval") if "dev_001e_chunk950chain_retrieval" in options else 0
c1, c2 = st.columns([2, 1])
base = c1.selectbox("기준", options, index=default, help="검색만 비교한 팀 실험 중 하나")
pair_metric = c2.selectbox("짝비교 지표", list(METRICS)[:4], index=1, format_func=lambda k: METRICS[k])
others = [(x["name"], x["experiment"]) for x in runs]
if not others:
    st.info("agent_list에서 agent를 고르면 기준과 agent들을 지표별로 한 표에 비교합니다. 아래는 팀 실험 두 개를 비교합니다.")
    b = st.selectbox("비교", options, index=options.index("dev_014_mixedchunk_retrieval") if "dev_014_mixedchunk_retrieval" in options else 1)
    others = [(b, b)]

base_m = {x["qid"]: x for x in rows(base, "metrics.jsonl")}
cols, extra = {}, {}
for name, exp in others:
    m = {x["qid"]: x for x in rows(exp, "metrics.jsonl")}
    qs = [q for q in m if q in base_m and base_m[q].get("evid") is not None and m[q].get("evid") is not None]
    if not qs:
        continue
    for label, src in ((f"기준: {base}", base_m), (name, m)):
        cols.setdefault(label, {})
        cols[label] = {METRICS[k]: sum(src[q].get(k) or 0 for q in qs) / len(qs) for k in METRICS}
    res = paired(base, exp, pair_metric)
    extra[name] = {"함께 푼 문항": len(qs), f"{METRICS[pair_metric]} 차이 (agent − 기준)": res["diff"],
                   "agent 우세 / 기준 우세 / 같음": f"{len(res['b_better'])} / {len(res['a_better'])} / {res['same']}",
                   "95% 신뢰구간": f"[{res['ci95'][0]:+.3f}, {res['ci95'][1]:+.3f}]",
                   "판정": "차이 있음" if res["ci95"][0] > 0 or res["ci95"][1] < 0 else "구별 안 됨"}
if cols:
    table = pd.DataFrame(cols)
    st.dataframe(styled(table, "{:,.3f}"), width="stretch")
    st.caption(f"열 = 기준 + 선택한 agent {len(cols) - 1}개. 각 agent는 기준과 함께 푼 문항만으로 계산했습니다(문항 수가 다르면 "
               "agent마다 기준 값도 그 문항들 기준). 초록 = 가장 좋은 값, 빨강 = 가장 나쁜 값.")
    diff = table.drop(columns=[table.columns[0]]).sub(table[table.columns[0]], axis=0)
    st.markdown("**기준 대비 차이 (agent − 기준)**")
    def tone(row):  # green = better than the baseline, red = worse; sizes such as 문맥 글자 수 stay plain
        sign = 1 if row.name in HIGHER else -1 if row.name in LOWER else 0
        return ["color:#16a34a; font-weight:700" if sign * v > 0 else "color:#dc2626; font-weight:700" if sign * v < 0
                else "" for v in row]
    st.dataframe(diff.style.format("{:+,.3f}").apply(tone, axis=1), width="stretch")
    st.markdown(f"**짝비교 ({METRICS[pair_metric]}, 문항별)**")
    st.dataframe(pd.DataFrame(extra).astype(str), width="stretch")
    st.caption("판정 기준(팀 규칙): 바뀐 문항이 잡음(90문항 중 14개)보다 많고 신뢰구간이 0을 포함하지 않아야 차이가 있다고 봅니다. "
               "문항 수가 적으면 신뢰구간이 넓어 '구별 안 됨'이 나오기 쉽습니다.")
