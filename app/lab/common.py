"""Shared loaders and labels for the lab report app. Everything here reads committed files (results/, golden/,
corpus/, configs/, experiments/); only the agent pages build agents, and only the live page calls the API."""

import json
import re
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

RESULTS = ROOT / "results"
sys.path.insert(0, str(ROOT / "scripts"))
import importlib  # noqa: E402

import agent as A  # noqa: E402  (repo root agent.py: Korean graph names, path of a run)
import branch_agents as BA  # noqa: E402  (agents on every origin branch, their runs: out/agent_runs/)


def _fresh(module):
    """Streamlit keeps imported modules across reruns: reload one whose file changed."""
    mtime = Path(module.__file__).stat().st_mtime
    if getattr(module, "_loaded_mtime", None) != mtime:
        module = importlib.reload(module)
        module._loaded_mtime = mtime
    return module


A, BA = _fresh(A), _fresh(BA)

# Final-test systems (submission/EVALUATION.md, PROCESS §9) and their dev counterparts
SYSTEMS = {
    "T1": ("처음 RAG", "test_000_baseline", "dev_000_baseline"),
    "T2": ("개선된 RAG (큰 모델)", "test_013_rerank_flash36", "dev_013_rerank_flash36_fix"),
    "T3": ("Agent (큰 모델)", "test_008b_agent950", "dev_008b_agent950"),
    "T4": ("최종 시스템 (작은 모델)", "test_013b_rerank_lite", "dev_013b_rerank_lite_fix"),
}
LABELS = {
    "dev_000_baseline": "T1 처음 RAG",
    "dev_013_rerank_flash36_fix": "T2 개선된 RAG",
    "dev_008b_agent950": "T3 Agent",
    "dev_013b_rerank_lite_fix": "T4 최종 (작은 모델)",
    "dev_014_agent_v2": "Agent v2 (메모+검토)",
    "test_000_baseline": "T1 처음 RAG",
    "test_013_rerank_flash36": "T2 개선된 RAG",
    "test_008b_agent950": "T3 Agent",
    "test_013b_rerank_lite": "T4 최종 (작은 모델)",
}
SETS = {"base_positive": "기본 질문", "base_negative": "함정 질문", "life_guide": "생활 가이드", "additional": "추가 자료",
        "self": "자작(20)", "self2": "자작 v2(41)"}
STATUS = {"answered": "답변", "abstained": "보류", "clarify": "되묻기", "refused": "거절", "retrieval_only": "검색만",
          "error": "오류"}
SCORE_COLS = {
    "correctness_mean": "정답 점수", "fully_correct": "완전 정답률", "status_ok": "대응 일치율",
    "citation_on_target": "출처 일치율", "page_hit@5": "정답 페이지 포함", "evid@5": "근거 문장 포함률",
    "gold@5": "정답 청크 수", "mrr": "MRR", "usd_per_question": "USD/문항", "llm_per_question": "LLM 호출/문항",
    "p50": "p50 초", "p90": "p90 초", "chars": "문맥 글자 수",
}


def label(exp: str) -> str:
    runs = {r["experiment"]: r["name"] for r in picked_runs()}
    if exp in runs:
        return f"🤖 {runs[exp]}"
    return f"{LABELS[exp]} · {exp}" if exp in LABELS else exp


def result_dir(exp: str) -> Path:
    """results/<exp> for committed experiments, out/agent_runs/results/<exp> for runs made on agent_list."""
    p = RESULTS / exp
    return p if p.exists() else BA.RESULTS / exp


# ---------------------------------------------------------------- agents picked on 1. 데이터 > agent_list

FETCH_EVERY_S = 300


def branch_agents(force: bool = False) -> list[dict]:
    """Newest own agent on each origin branch. GitHub is fetched on app start, on demand and every 5 minutes;
    the list itself is rebuilt from the per-commit cache whenever the fetch or the selection rules
    (scripts/branch_agents.py) changed, so an open tab never keeps an entry made under older rules."""
    import time
    now = time.time()
    if force or now - st.session_state.get("branch_agents_fetched", 0) > FETCH_EVERY_S:
        with st.spinner("GitHub 브랜치에서 agent를 조회하는 중…"):
            try:
                BA.scan(fetch=True)
                st.session_state.branch_agents_note = ""
            except Exception as e:
                st.session_state.branch_agents_note = f"GitHub에 연결하지 못해 마지막으로 받은 정보로 보여 줍니다 ({type(e).__name__})."
        st.session_state.branch_agents_fetched = now
        st.session_state.branch_agents_at = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    stamp = (st.session_state.branch_agents_fetched, Path(BA.__file__).stat().st_mtime)
    if st.session_state.get("branch_agents_stamp") != stamp:
        shown, hidden = BA.distinct_agents(BA.scan(fetch=False))
        st.session_state.branch_agents, st.session_state.branch_agents_dup = shown, hidden
        st.session_state.branch_agents_stamp = stamp
    return st.session_state.branch_agents


def duplicate_agents() -> list[dict]:
    """Branches whose newest agent is the same as one listed (merged from its maker's branch)."""
    branch_agents()
    return st.session_state.get("branch_agents_dup", [])


def picked() -> list[dict]:
    names = st.session_state.get("picked_agents", [])
    return [a for a in branch_agents() if a["label"] in names]


def latest_run(entry: dict, exact: bool = True) -> dict | None:
    """Newest finished run of this branch agent. exact: only runs of identical code and config (same_code_id), so
    a newer commit on the branch is not shown with an older version's result."""
    rows_ = [r for r in BA.read_log() if r["status"] == "done" and r["branch"] == entry["branch"]
             and r["config"] == entry["config"] and (BA.RESULTS / r["experiment"] / "summary.json").exists()
             and (not exact or r.get("same_code_id") == entry["same_code_id"])]
    return max(rows_, key=lambda r: r["started"]) if rows_ else None


def all_runs(entry: dict) -> list[dict]:
    """Every finished run of this agent (identical code and config), oldest first."""
    rows_ = [r for r in BA.read_log() if r["status"] == "done" and r["branch"] == entry["branch"]
             and r["config"] == entry["config"] and r.get("same_code_id") == entry["same_code_id"]
             and (BA.RESULTS / r["experiment"] / "summary.json").exists()]
    return sorted(rows_, key=lambda r: r["started"])


def picked_runs() -> list[dict]:
    """Picked agents that have a finished run, numbered in pick order: name '1. <branch> agent'."""
    out = []
    for n, a in enumerate(picked(), 1):
        r = latest_run(a)
        if r:
            out.append({**a, **r, "no": n, "name": f"{n}. {a['label']}", "path": str(BA.RESULTS / r["experiment"])})
    return out


BEST = {"정답 점수": max, "완전 정답률": max, "대응 일치율": max, "출처 일치율": max, "근거 문장 포함률": max,
        "USD/문항": min, "LLM 호출/문항": min, "검색/문항": min, "p90 초": min}


def compare_runs(runs: list[dict]) -> tuple[pd.DataFrame, dict, list]:
    """Metrics of the picked runs on the questions they all answered (columns = '1. <agent>', ...)."""
    grades = {r["name"]: {g["qid"]: g["correctness"] for g in jsonl(str(Path(r["path"]) / "grades.jsonl"))} for r in runs}
    common = sorted(set.intersection(*(set(g) for g in grades.values()))) if grades else []
    cols = {}
    for r in runs:
        if not common:
            break
        m = {x["qid"]: x for x in jsonl(str(Path(r["path"]) / "metrics.jsonl")) if x["qid"] in common}
        g, lat = grades[r["name"]], sorted(m[q]["latency_s"] for q in common)
        cols[r["name"]] = {
            "정답 점수": sum(g[q] for q in common) / len(common) / 2, "완전 정답률": sum(g[q] == 2 for q in common) / len(common),
            "대응 일치율": sum(m[q].get("status_ok") or 0 for q in common) / len(common),
            "출처 일치율": pd.Series([m[q].get("citation_on_target") for q in common]).mean(),
            "근거 문장 포함률": pd.Series([m[q].get("evid") for q in common]).mean(),
            "USD/문항": sum(m[q]["usd"] for q in common) / len(common),
            "LLM 호출/문항": sum(m[q]["n_llm_calls"] or 0 for q in common) / len(common),
            "검색/문항": sum(m[q].get("n_searches") or 0 for q in common) / len(common),
            "p90 초": lat[int(0.9 * (len(lat) - 1))]}
    return pd.DataFrame(cols), grades, common


HIGHER = {"정답 점수", "완전 정답률", "대응 일치율", "출처 일치율", "근거 문장 포함률", "정답 페이지 포함", "MRR", "정답 청크 수"}
LOWER = {"USD/문항", "LLM 호출/문항", "검색/문항", "p90 초", "p50 초", "토큰/문항"}
GOOD = "background-color:#dcfce7; color:#14532d; font-weight:700"
BAD = "background-color:#fee2e2; color:#7f1d1d; font-weight:700"
PALETTE = ["#2563eb", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#06b6d4"]


def styled(df: pd.DataFrame, digits: str = "{:.3f}"):
    """Rows = metrics, columns = agents: best value green, worst red (higher or lower is better per metric;
    rows that are neither, e.g. counts, are left plain)."""
    def mark(row):
        vals = pd.to_numeric(row, errors="coerce")
        if row.name not in HIGHER | LOWER or vals.nunique() < 2:
            return [""] * len(row)
        good, bad = (vals.max(), vals.min()) if row.name in HIGHER else (vals.min(), vals.max())
        return [GOOD if v == good else BAD if v == bad else "" for v in vals]
    return df.style.apply(mark, axis=1).format(digits, na_rep="–")


def colors(names: list[str]):
    """One fixed color per picked agent, the same on every page (by its number)."""
    import altair as alt
    return alt.Scale(domain=names, range=[PALETTE[(int(n.split(".")[0]) - 1) % len(PALETTE)] if n[:1].isdigit()
                                          else "#94a3b8" for n in names])


def agent_bars(df: pd.DataFrame, metrics: list[str], height: int = 170):
    """Grouped bars: one panel per metric, one bar per agent (column of df); best bar outlined in green, worst in
    red, so three agents' values sit next to each other on the same scale."""
    import altair as alt
    rows_ = []
    for m in metrics:
        if m not in df.index:
            continue
        vals = pd.to_numeric(df.loc[m], errors="coerce")
        judged = m in HIGHER | LOWER  # sizes and lengths are neither better nor worse: no outline
        good = vals.max() if m not in LOWER else vals.min()
        bad = vals.min() if m not in LOWER else vals.max()
        for agent, v in vals.items():
            rows_.append({"지표": m + (" (낮을수록 좋음)" if m in LOWER else "" if judged else " (참고)"), "agent": agent, "값": v,
                          "판정": "" if not judged or good == bad else "최고" if v == good else "최저" if v == bad else ""})
    data = pd.DataFrame(rows_)
    if data.empty:
        return
    base = alt.Chart(data).encode(
        x=alt.X("agent:N", title=None, axis=alt.Axis(labels=False, ticks=False)),
        y=alt.Y("값:Q", title=None), color=alt.Color("agent:N", scale=colors(list(df.columns)), legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["지표", "agent", alt.Tooltip("값:Q", format=".4f"), "판정"])
    bars = base.mark_bar(strokeWidth=3).encode(
        stroke=alt.Stroke("판정:N", scale=alt.Scale(domain=["최고", "최저", ""], range=["#16a34a", "#dc2626", "transparent"]),
                          legend=None))
    labels = base.mark_text(dy=-6, fontSize=11).encode(text=alt.Text("값:Q", format=".3~f"))
    st.altair_chart((bars + labels).properties(width=150, height=height).facet(
        facet=alt.Facet("지표:N", title=None), columns=4).resolve_scale(y="independent"))
    st.caption("막대 하나 = agent 하나 (색은 모든 페이지에서 같음). 초록 테두리 = 그 지표에서 가장 좋은 agent, 빨간 테두리 = 가장 나쁜 agent.")


def verdict(df: pd.DataFrame, grades: dict, common: list) -> str:
    """One line: which picked agent leads, by how much, and whether that is beyond noise."""
    from evalkit.paired import compare
    if df.shape[1] < 2:
        return ""
    order = sorted(df.columns, key=lambda k: (-df.loc["정답 점수", k], -df.loc["완전 정답률", k], df.loc["USD/문항", k]))
    lead, second = order[0], order[1]
    r = compare({q: grades[second][q] for q in common}, {q: grades[lead][q] for q in common}, max_score=2.0)
    net = len(r["b_better"]) - len(r["a_better"])
    if df.loc["정답 점수", lead] == df.loc["정답 점수", second] and net == 0:
        cheap = df.loc["USD/문항"].idxmin()
        return (f"🤝 정답 점수 동률 ({df.loc['정답 점수', lead]:.3f}, {len(common)}문항) — 점수로는 우열이 없고, "
                f"비용이 가장 낮은 것은 {cheap} ({df.loc['USD/문항', cheap]:.4f} USD/문항)입니다.")
    sure = r["ci95"][0] > 0 and len(r["b_better"]) + len(r["a_better"]) > 14 * len(common) / 90
    return (f"🏆 {lead} 우세 — 정답 점수 {df.loc['정답 점수', lead]:.3f} vs 2위 {second} {df.loc['정답 점수', second]:.3f} "
            f"({len(common)}문항, 순증 {net:+d}, 95% 신뢰구간 [{r['ci95'][0]:+.3f}, {r['ci95'][1]:+.3f}]). "
            + ("차이가 잡음보다 커서 우세가 확실합니다." if sure else "다만 차이가 잡음 범위 안이라 확실한 우세는 아닙니다."))


def picked_compare(title: str = "선택한 agent 비교 (dev)", bars: bool = True):
    """Side-by-side table of the picked runs with the verdict; nothing when fewer than one run."""
    runs = picked_runs()
    if not runs:
        return
    st.subheader(f"🤖 {title}")
    df, grades, common = compare_runs(runs)
    if df.empty:
        st.warning("선택한 agent들이 함께 푼 문항이 없습니다. agent_list에서 같은 문항 수로 실행하세요.")
        return
    if df.shape[1] >= 2:
        st.success(verdict(df, grades, common))
    st.dataframe(styled(df), width="stretch")
    st.caption(f"함께 푼 dev 문항 {len(common)}개 기준 · 초록 = 그 지표에서 가장 좋은 agent, 빨강 = 가장 나쁜 agent "
               "(점수는 높을수록, 비용·호출·시간은 낮을수록 좋음)")
    if bars:
        agent_bars(df, ["정답 점수", "완전 정답률", "대응 일치율", "출처 일치율", "USD/문항", "LLM 호출/문항", "p90 초"])


def chunk_frame(runs: list[dict]) -> tuple[pd.DataFrame, list]:
    """Chunking and retrieval numbers of the picked runs on their common questions (columns = agents)."""
    sets = [{r_["qid"] for r_ in jsonl(str(Path(r["path"]) / "metrics.jsonl"))} for r in runs]
    common = sorted(set.intersection(*sets)) if sets else []
    cols = {}
    for r in runs:
        m = {x["qid"]: x for x in jsonl(str(Path(r["path"]) / "metrics.jsonl")) if x["qid"] in common}
        ctx = {x["qid"]: x.get("context") or [] for x in jsonl(str(Path(r["path"]) / "runs.jsonl")) if x["qid"] in common}
        used = {u["chunk_id"]: len(u["content"]) for c in ctx.values() for u in c}
        answerable = [q for q in common if m[q].get("page_hit") is not None]
        mean = lambda k, qs: (sum(m[q].get(k) or 0 for q in qs) / len(qs)) if qs else None  # noqa: E731
        cols[r["name"]] = {
            "정답 페이지 포함": mean("page_hit", answerable), "근거 문장 포함률": mean("evid", answerable),
            "MRR": mean("mrr", answerable), "문항당 문맥 글자 수": mean("chars", common),
            "문항당 넘긴 조각 수": sum(len(c) for c in ctx.values()) / len(common) if common else None,
            "조각 평균 길이": sum(used.values()) / len(used) if used else None, "검색/문항": mean("n_searches", common)}
    return pd.DataFrame(cols), common


def picked_note():
    """One line at the top of a page: which picked agents this page includes."""
    runs, sel = picked_runs(), picked()
    if not sel:
        st.caption("👈 '1. 데이터 › agent_list'에서 agent를 고르면 이 페이지에 그 agent들의 결과가 함께 나옵니다.")
    else:
        missing = [a["label"] for a in sel if not latest_run(a)]
        st.info("🤖 선택한 agent: " + " · ".join(r["name"] for r in runs)
                + (f"  (결과 없음: {', '.join(missing)} — agent_list에서 실행)" if missing else ""))


@st.cache_data
def jsonl(path: str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


@st.cache_data
def _summary(path: str) -> dict:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def summary(exp: str) -> dict:
    return _summary(str(result_dir(exp) / "summary.json"))


def experiments() -> list[str]:
    """Committed experiments plus the runs of the agents picked on agent_list."""
    return sorted(p.parent.name for p in RESULTS.glob("*/summary.json")) + [r["experiment"] for r in picked_runs()]


def has(exp: str, name: str) -> bool:
    return (result_dir(exp) / name).exists()


def rows(exp: str, name: str) -> list[dict]:
    return jsonl(str(result_dir(exp) / name))


def summary_table() -> pd.DataFrame:
    names = {r["experiment"]: "🤖 " + r["name"] for r in picked_runs()}
    out = []
    for exp in experiments():
        s = summary(exp)
        sc, rt, co, ca, la = (s.get(k) or {} for k in ("scores", "retrieval", "cost", "calls", "latency_s"))
        kind = "검색만" if s.get("retrieval_only") else ("Agent" if str(s.get("system", "")).startswith("agent") else "RAG")
        out.append({
            "실험": exp, "이름": names.get(exp) or LABELS.get(exp, ""), "split": s.get("split"),
            "종류": "선택 agent" if exp in names else kind, "문항 수": s.get("n_questions"),
            "정답 점수": sc.get("correctness_mean"), "완전 정답률": sc.get("fully_correct"),
            "대응 일치율": sc.get("status_ok"), "출처 일치율": sc.get("citation_on_target"),
            "정답 페이지 포함": rt.get("page_hit@5"), "근거 문장 포함률": rt.get("evid@5"), "MRR": rt.get("mrr"),
            "문맥 글자 수": rt.get("chars"), "USD/문항": co.get("usd_per_question"),
            "LLM 호출/문항": ca.get("llm_per_question"), "p50 초": la.get("p50"), "p90 초": la.get("p90"),
            "카드": s.get("card"), "설명": s.get("description"), "기준": s.get("compare_to"),
            "만든 시각": s.get("created_at"),
        })
    return pd.DataFrame(out)


def graded(split: str | None = None) -> list[str]:
    return [e for e in experiments() if has(e, "grades.jsonl") and (split is None or e.startswith(split + "_"))]


@st.cache_data
def final_frame(system: str) -> pd.DataFrame:
    """One row per final-test question of system T1..T4: provided test 90 + self-written v2 41 (EVALUATION.md);
    the archived 20-question `self` set is left out, as in the write-up."""
    test = SYSTEMS[system][1]
    metrics = rows(test, "metrics.jsonl") + rows(test + "_self2", "metrics.jsonl")
    grades = {r["qid"]: r for r in rows(test, "grades.jsonl") + rows(test + "_self2", "grades.jsonl")}
    out = {}
    for m in metrics:
        if m["set"] == "self":
            continue
        g = grades.get(m["qid"], {})
        out[m["qid"]] = {**m, "correctness": g.get("correctness"), "reason": g.get("reason")}
    return pd.DataFrame(list(out.values()))


def final_stats(system: str) -> dict:
    df = final_frame(system)
    ans = df[df["behavior_group"] == "answer"]
    return {"n": len(df), "정답 점수": df["correctness"].mean() / 2, "완전 정답률": (df["correctness"] == 2).mean(),
            "대응 일치율": df["status_ok"].mean(), "출처 일치율": df["citation_on_target"].mean(),
            "보류율 (답변 가능)": (ans["status"] != "answered").mean(),
            "평균 초": df["latency_s"].mean(), "p90 초": df["latency_s"].quantile(0.9),
            "LLM 호출/문항": df["n_llm_calls"].mean(), "USD/문항": df["usd"].mean()}


@st.cache_data
def golden() -> dict:
    items = {}
    for name in ("provided.jsonl", "self.jsonl", "self2.jsonl"):
        for it in jsonl(str(ROOT / "golden" / name)):
            items.setdefault(it["qid"], it)
    return items


@st.cache_data
def pages() -> list[dict]:
    return jsonl(str(ROOT / "corpus" / "pages.jsonl"))


def paired(a: str, b: str, metric: str | None = None) -> dict:
    """evalkit.paired.compare on grades (score 0-2) or on a metrics.jsonl column."""
    from evalkit.paired import compare
    if metric:
        ma = {r["qid"]: r[metric] for r in rows(a, "metrics.jsonl") if r.get(metric) is not None}
        mb = {r["qid"]: r[metric] for r in rows(b, "metrics.jsonl") if r.get(metric) is not None}
        top = 5.0 if metric.startswith("gold@") else 1.0
        return compare(ma, mb, max_score=top)
    ga = {r["qid"]: r["correctness"] for r in rows(a, "grades.jsonl")}
    gb = {r["qid"]: r["correctness"] for r in rows(b, "grades.jsonl")}
    return compare(ga, gb, max_score=2.0)


@st.cache_data
def cards() -> list[dict]:
    out = []
    for p in sorted((ROOT / "experiments").glob("[0-9]*.md")):
        text = re.sub(r"<!--.*?-->", "", p.read_text(encoding="utf-8"), flags=re.S).strip()
        title = next((l[2:].strip() for l in text.splitlines() if l.startswith("# ")), p.stem)
        status = next((l.split(":", 1)[1].strip() for l in text.splitlines() if l.startswith("Status:")), "")
        out.append({"file": p.name, "title": title, "status": status, "text": text})
    return out


def pct(x) -> str:
    return "–" if x is None or pd.isna(x) else f"{x:.3f}"


def kpi_row(items: list[tuple[str, str, str | None]]):
    cols = st.columns(len(items))
    for col, (name, value, help_) in zip(cols, items):
        col.metric(name, value, help=help_)


@st.cache_resource
def agent_of(config: str):
    from rag.config import load_config
    from rag.systems import build_system
    cfg = load_config(ROOT / config)
    return build_system(cfg), cfg


@st.cache_data(show_spinner="흐름도를 그리는 중…")
def mermaid_png(mermaid: str) -> bytes | None:
    try:
        from langchain_core.runnables.graph_mermaid import draw_mermaid_png
        return draw_mermaid_png(mermaid)
    except Exception:
        return None


def show_mermaid(mermaid: str):
    png = mermaid_png(mermaid)
    if png:
        st.image(png)
    else:
        st.warning("mermaid.ink 에 연결할 수 없어 mermaid 원문을 보여 줍니다. https://mermaid.live 에 붙여 넣으면 그림으로 볼 수 있습니다.")
        st.code(mermaid, language="text")
