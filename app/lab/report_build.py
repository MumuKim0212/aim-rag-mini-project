"""Report (7. Report): a comparison of the agents picked on 개요 › agent_list, nothing else. The web page and the
PDF draw the same blocks:

    ("h1" | "h2" | "p" | "note", text), ("bullets", [text, ...]), ("table", DataFrame, caption),
    ("chart", fn(fig, box), caption), ("images", [(png bytes, caption), ...], title)

A chart fn draws its axes inside box = (left, bottom, width, height) in figure fractions. Every sentence of the
conclusions is generated from the picked agents' runs (out/agent_runs/), their branch code (graph, chunks) and
their configs, so the text always matches the data. The PDF is A4 portrait, drawn with matplotlib (PdfPages) in
맑은 고딕, with no extra package.
"""

import io
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from lab.common import (BA, HIGHER, LOWER, PALETTE, SETS, A, all_runs, chunk_frame, compare_runs, golden, mermaid_png,
                        rows, summary)

FONT = Path("C:/Windows/Fonts/malgun.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/malgunbd.ttf")
NOISE = 14  # questions out of 90 that change when the same setting is run again (PROCESS.md 4절)


def color_of(name: str) -> str:
    return PALETTE[(int(name.split(".")[0]) - 1) % len(PALETTE)] if name[:1].isdigit() else "#64748b"


def multi_bars(fig, box, df: pd.DataFrame, metrics: list[str], fmt: str = "{:.3f}"):
    """One small panel per metric, one bar per agent (its color); best value marked ★ (worst ▼) when the metric
    has a better direction."""
    metrics = [m for m in metrics if m in df.index]
    left, bottom, width, height = box
    gap = 0.03
    w = (width - gap * (len(metrics) - 1)) / max(len(metrics), 1)
    for i, m in enumerate(metrics):
        ax = fig.add_axes([left + i * (w + gap), bottom, w, height])
        vals = pd.to_numeric(df.loc[m], errors="coerce")
        names = list(df.columns)
        ax.bar(range(len(names)), vals, color=[color_of(n) for n in names])
        judged = m in HIGHER | LOWER and vals.nunique() > 1
        best = vals.max() if m not in LOWER else vals.min()
        worst = vals.min() if m not in LOWER else vals.max()
        for j, v in enumerate(vals):
            mark = (" ★" if v == best else " ▼" if v == worst else "") if judged else ""
            ax.text(j, v, fmt.format(v) + mark, ha="center", va="bottom", fontsize=6.5)
        ax.set_title(m + (" (낮을수록 좋음)" if m in LOWER else ""), fontsize=7.5)
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels([n.split(".")[0] for n in names], fontsize=7)
        top = max(vals.max(), 1e-9)
        ax.set_ylim(0, top * 1.25)
        ax.tick_params(axis="y", labelsize=6)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)


def _graph_nodes(text: str) -> list[str]:
    return [line.strip().split("(")[0] for line in text.splitlines()
            if "(" in line and "-->" not in line and "-.->" not in line and "-. " not in line
            and not line.strip().startswith(("classDef", "class ", "graph", "config", "flowchart", "curve"))
            and line.strip().split("(")[0] not in ("__start__", "__end__")]


def build(sel: list[dict], runs: list[dict]) -> list[tuple]:
    """sel = picked agents (agent_list order), runs = their latest finished runs (picked_runs)."""
    if len(runs) < 2:
        return [("h1", "선택한 agent 성능 비교"),
                ("p", "비교하려면 '개요 › agent_list'에서 agent를 두 개 이상 고르고, 같은 문항 수로 실행한 결과가 있어야 합니다.")]
    names = [r["name"] for r in runs]
    by_name = {r["name"]: r for r in runs}
    entry = {r["name"]: next(a for a in sel if a["label"] == r["label"]) for r in runs}
    df, grades, common = compare_runs(runs)
    ret, _ = chunk_frame(runs)
    n = len(common)
    items = golden()
    met = {r["name"]: {x["qid"]: x for x in rows(r["experiment"], "metrics.jsonl")} for r in runs}
    sets_ = sorted({met[names[0]][q]["set"] for q in common})
    from evalkit.paired import compare

    # who leads, and is it beyond noise
    order = sorted(names, key=lambda k: (-df.loc["정답 점수", k], -df.loc["완전 정답률", k], df.loc["USD/문항", k]))
    lead = order[0]
    pairs = {}
    for k in order[1:]:
        pairs[k] = compare({q: grades[k][q] for q in common}, {q: grades[lead][q] for q in common}, max_score=2.0)
    beyond = {k: r["ci95"][0] > 0 and len(r["b_better"]) + len(r["a_better"]) > NOISE * n / 90 for k, r in pairs.items()}
    tie = all(df.loc["정답 점수", k] == df.loc["정답 점수", lead] for k in names)
    cheap = df.loc["USD/문항"].idxmin()
    fast = df.loc["p90 초"].idxmin()
    fewest = df.loc["LLM 호출/문항"].idxmin()

    # structure and chunking
    graphs, node_sets = {}, {}
    for k in names:
        try:
            graphs[k] = A.translate(BA.graph_of(entry[k]["sha"], entry[k]["config"]))
            node_sets[k] = _graph_nodes(graphs[k])
        except Exception as e:  # keep the report going without that graph
            graphs[k], node_sets[k] = None, []
            print("graph", k, e)
    chunks = {k: BA.chunks_of(entry[k]["sha"], entry[k]["config"]) for k in names}
    base = {(c["chunk_id"], c["content"]) for c in chunks[names[0]]}
    same_chunks = all({(c["chunk_id"], c["content"]) for c in chunks[k]} == base for k in names[1:])
    unique_nodes = {k: [A.NODES.get(x, x).replace("<br>", " ") for x in node_sets[k]
                        if not any(x in node_sets[o] for o in names if o != k)] for k in names}

    # questions where they differ
    differ = [q for q in common if len({grades[k][q] for k in names}) > 1]

    # ------------------------------------------------------------------ 1. 의견 및 결론
    lead_line = (f"정답 점수는 {len(names)}개 agent 모두 {df.loc['정답 점수', lead]:.3f}로 같다" if tie else
                 "정답 점수는 " + ", ".join(f"{k} {df.loc['정답 점수', k]:.3f}" for k in order) + "이다")
    sig = [f"{k}와의 차이 {pairs[k]['diff']:+.3f}, 95% 신뢰구간 [{pairs[k]['ci95'][0]:+.3f}, {pairs[k]['ci95'][1]:+.3f}], "
           f"{lead} 우세 {len(pairs[k]['b_better'])} / 열세 {len(pairs[k]['a_better'])}문항 → "
           + ("잡음보다 큰 차이" if beyond[k] else "구별 안 됨") for k in order[1:]]
    if any(beyond.values()):
        verdict = f"{lead}가 성능에서 확실히 우세하다."
        rec = (f"성능을 우선하면 {lead}를 쓴다. 비용은 {df.loc['USD/문항', lead]:.4f} USD/문항으로 "
               + ("가장 싸다." if lead == cheap else f"가장 싼 {cheap}({df.loc['USD/문항', cheap]:.4f})보다 비싸다."))
    else:
        verdict = "정답 점수로는 두 agent를 구별할 수 없다." if len(names) == 2 else "정답 점수로는 agent들을 구별할 수 없다."
        rec = (f"점수가 같은 수준이므로 비용·속도로 고르면 {cheap}가 맞다 (문항당 {df.loc['USD/문항', cheap]:.4f} USD"
               + (f", p90 {df.loc['p90 초', cheap]:.1f}초도 가장 빠름" if cheap == fast else f"; 가장 빠른 것은 {fast} p90 {df.loc['p90 초', fast]:.1f}초")
               + ").")
    B = [("h1", "1. 의견 및 결론"),
         ("p", f"비교한 agent: {', '.join(names)}. 같은 dev {n}문항(질문 묶음: {', '.join(SETS.get(s, s) for s in sets_)})을 각 agent가 "
               "자기 브랜치 코드로 답하고 같은 채점 기준으로 채점한 결과다."),
         ("note", f"결론: {verdict} {lead_line}. {rec}"),
         ("h2", "성능"),
         ("bullets", sig + [
             f"완전 정답률 " + ", ".join(f"{k} {df.loc['완전 정답률', k]:.3f}" for k in names)
             + f"; 대응 일치율 " + ", ".join(f"{k} {df.loc['대응 일치율', k]:.3f}" for k in names)
             + f"; 출처 일치율 " + ", ".join(f"{k} {df.loc['출처 일치율', k]:.3f}" for k in names) + ".",
             (f"점수가 갈린 문항은 {len(differ)}개다: " + ", ".join(
                 f"{q}(" + " / ".join(f"{k.split('.')[0]}번 {grades[k][q]}점" for k in names) + ")" for q in differ[:8])
              + (" …" if len(differ) > 8 else "") + ".") if differ else "모든 문항에서 점수가 같았다."]),
         ("h2", "비용과 속도"),
         ("bullets", [
             "문항당 비용: " + ", ".join(f"{k} {df.loc['USD/문항', k]:.4f} USD" for k in names) + f" → {cheap}가 가장 싸다.",
             "LLM 호출/문항: " + ", ".join(f"{k} {df.loc['LLM 호출/문항', k]:.1f}" for k in names) + f" → {fewest}가 가장 적다.",
             "p90 응답 시간: " + ", ".join(f"{k} {df.loc['p90 초', k]:.1f}초" for k in names) + f" → {fast}가 가장 빠르다."]),
         ("h2", "왜 차이가 나는가"),
         ("bullets", [
             ("구조: " + "; ".join(f"{k}에만 있는 노드는 {', '.join(unique_nodes[k]) or '없음'}" for k in names)
              + ". 노드가 많을수록 LLM 호출과 시간이 늘어난다."),
             ("청킹: 두 agent의 청크가 완전히 같다(" + f"{len(base):,}개). 차이는 청킹이 아니라 검색 이후 단계에서 난다."
              if same_chunks else "청킹: agent마다 청크가 다르다(4장 참고)."),
             "검색: 근거 문장 포함률 " + ", ".join(f"{k} {ret.loc['근거 문장 포함률', k]:.3f}" for k in names)
             + ", 문항당 검색 " + ", ".join(f"{k} {ret.loc['검색/문항', k]:.2f}회" for k in names) + "."]),
         ("h2", "의견"),
         ("bullets", [
             rec,
             (f"이번 비교는 {n}문항, 질문 묶음 {len(sets_)}개({', '.join(SETS.get(s, s) for s in sets_)})뿐이다. 함정 질문·추가 자료가 빠져 있어 "
              "보류·거절 판단과 긴 보고서 문항에서의 차이는 아직 모른다. dev 90문항 전체로 다시 실행해야 결론을 확정할 수 있다."
              if n < 90 else "dev 90문항 전체로 비교했다."),
             f"같은 설정도 다시 돌리면 90문항 중 약 {NOISE}문항이 바뀐다. {n}문항에서 1~2문항 차이는 잡음과 구별되지 않는다."])]

    # ------------------------------------------------------------------ 2. 비교 대상
    info = {}
    for k in names:
        a, r = entry[k], by_name[k]
        c = summary(r["experiment"]).get("config") or {}
        ch, rt = c.get("chunking", {}), c.get("retrieval", {})
        info[k] = {"만든 사람": a.get("maker", "-"), "브랜치 · 커밋": f"{a['branch']} · {a['commit']}",
                   "agent 파일": a.get("impl", "-"), "설정": a["config"], "답변 모델": (c.get("answer") or {}).get("model"),
                   "청킹": f"{ch.get('method')} {ch.get('chunk_size')}/{ch.get('chunk_overlap')}",
                   "검색": f"{rt.get('method')} k={rt.get('k')}" + (f", 재정렬 {rt['rerank_pool']}→{rt.get('k')}" if rt.get("rerank_pool") else ""),
                   "실행": f"{r['n']}문항 · {r['started'][:16].replace('T', ' ')}"}
    B += [("h1", "2. 비교 대상 agent"),
          ("table", pd.DataFrame(info).reset_index().rename(columns={"index": "항목"}), "agent 정보"),
          ("bullets", [f"{k}: {entry[k]['description']}" for k in names])]

    # ------------------------------------------------------------------ 3. 흐름도
    imgs = [(mermaid_png(graphs[k]), f"{k} — {' → '.join(A.NODES.get(x, x).replace('<br>', ' ') for x in node_sets[k])}")
            for k in names if graphs[k]]
    B += [("h1", "3. LangGraph 흐름도"),
          ("p", "각 agent 브랜치의 코드로 LangGraph 그래프를 만들어 그린 순서도다(노드 이름만 한글로 바꿈)."),
          ("images", [(png, cap) for png, cap in imgs if png], "agent별 흐름도")]

    # ------------------------------------------------------------------ 4. 청킹
    cstat = {}
    for k in names:
        lens = pd.Series([c["chars"] for c in chunks[k]])
        ch = entry[k]["chunking"]
        cstat[k] = {"방식": ch.get("method"), "크기 / 겹침": f"{ch.get('chunk_size')} / {ch.get('chunk_overlap')}",
                    "청크 수": f"{len(lens):,}", "평균 길이": f"{lens.mean():.0f}", "중앙값": f"{lens.median():.0f}",
                    "최대": f"{lens.max():,}", "페이지를 넘는 청크": sum(len(c["pages"]) > 1 for c in chunks[k])}

    def length_hist(fig, box):
        left, bottom, width, height = box
        w = (width - 0.04 * (len(names) - 1)) / len(names)
        top = 0
        axes = []
        for i, k in enumerate(names):
            ax = fig.add_axes([left + i * (w + 0.04), bottom, w, height])
            counts, _, _ = ax.hist([c["chars"] for c in chunks[k]], bins=30, range=(0, 3000), color=color_of(k))
            top = max(top, counts.max())
            ax.set_title(k, fontsize=7.5)
            ax.set_xlabel("청크 길이 (글자)", fontsize=7)
            ax.tick_params(labelsize=6)
            axes.append(ax)
        for ax in axes:
            ax.set_ylim(0, top * 1.1)

    B += [("h1", "4. 청킹 비교"),
          ("p", "각 agent의 브랜치 코드와 설정으로 범위 B 전체를 직접 청킹한 결과다."
                + (f" 두 agent의 청크 {len(base):,}개가 내용까지 완전히 같다." if same_chunks else "")),
          ("table", pd.DataFrame(cstat).astype(str).reset_index().rename(columns={"index": "항목"}), "agent별 청킹"),
          ("chart", length_hist, "청크 길이 분포 (agent마다 따로, 같은 축)")]

    # ------------------------------------------------------------------ 5. 검색
    rtab = ret.copy()
    B += [("h1", "5. 검색 성능 (LLM 채점 없이 계산)"),
          ("p", f"함께 푼 {n}문항에서 답변 단계에 넘긴 최종 문맥(재검색 포함) 기준이다. ★ = 가장 좋은 값, ▼ = 가장 나쁜 값."),
          ("table", rtab.map(lambda v: f"{v:,.3f}" if isinstance(v, float) else v).reset_index().rename(columns={"index": "지표"}),
           "agent별 검색 지표"),
          ("chart", lambda fig, box: multi_bars(fig, box, rtab, ["근거 문장 포함률", "정답 페이지 포함", "MRR", "검색/문항"]),
           "검색 지표 (막대 하나 = agent 하나, 번호 = agent 번호)")]

    # ------------------------------------------------------------------ 6. 답변
    per_set = {}
    for k in names:
        acc = {}
        for q in common:
            acc.setdefault(SETS.get(met[k][q]["set"], met[k][q]["set"]), []).append(grades[k][q] / 2)
        per_set[k] = {f"{s} ({len(v)}문항)": f"{sum(v) / len(v):.3f}" for s, v in acc.items()}
    pair_tab = pd.DataFrame([{"비교": f"{lead} vs {k}", "점수 차이": f"{r['diff']:+.3f}",
                              f"{lead.split('.')[0]}번 우세 / 열세 / 같음": f"{len(r['b_better'])} / {len(r['a_better'])} / {r['same']}",
                              "95% 신뢰구간": f"[{r['ci95'][0]:+.3f}, {r['ci95'][1]:+.3f}]",
                              "판정": "차이 있음" if beyond[k] else "구별 안 됨"} for k, r in pairs.items()])
    diff_rows = [{"qid": q, "질문": items.get(q, {}).get("question", "")[:40],
                  **{f"{k.split('.')[0]}번 점수": grades[k][q] for k in names},
                  **{f"{k.split('.')[0]}번 상태": met[k][q]["status"] for k in names}} for q in differ]
    B += [("h1", "6. 답변 성능 (LLM이 답하고 채점)"),
          ("table", df.loc[["정답 점수", "완전 정답률", "대응 일치율", "출처 일치율"]].map(lambda v: f"{v:.3f}")
           .reset_index().rename(columns={"index": "지표"}), f"답변 지표 (함께 푼 {n}문항)"),
          ("chart", lambda fig, box: multi_bars(fig, box, df, ["정답 점수", "완전 정답률", "대응 일치율", "출처 일치율"]),
           "답변 지표 (★ = 가장 좋음, ▼ = 가장 나쁨)"),
          ("table", pd.DataFrame(per_set).reset_index().rename(columns={"index": "질문 묶음"}), "질문 묶음별 정답 점수"),
          ("table", pair_tab, f"짝비교 (1위 {lead} 기준, 문항별 점수)")]
    if diff_rows:
        B += [("table", pd.DataFrame(diff_rows), "점수가 갈린 문항")]

    # ------------------------------------------------------------------ 7. 비용·속도
    cost = df.loc[["USD/문항", "LLM 호출/문항", "검색/문항", "p90 초"]]
    tok = {k: summary(by_name[k]["experiment"]).get("cost", {}).get("tokens_per_question") for k in names}
    cost_tab = cost.map(lambda v: f"{v:.4f}" if v < 0.1 else f"{v:.2f}")
    cost_tab.loc["토큰/문항"] = [f"{tok[k]:,.0f}" if tok[k] else "-" for k in names]
    B += [("h1", "7. 비용·속도"),
          ("table", cost_tab.reset_index().rename(columns={"index": "지표"}), "비용과 속도 (낮을수록 좋음)"),
          ("chart", lambda fig, box: multi_bars(fig, box, cost, ["USD/문항", "LLM 호출/문항", "p90 초"], fmt="{:.4g}"),
           "비용·속도 (★ = 가장 좋음)")]

    # ------------------------------------------------------------------ 8. 실행 이력
    hist = []
    for k in names:
        for i, r in enumerate(all_runs(entry[k]), 1):
            hist.append({"agent": k, "회차": i, "실행 시각": r["started"][5:16].replace("T", " "), "문항 수": r["n"],
                         "정답 점수": f"{r['correctness']:.3f}", "USD/문항": f"{r['usd_per_question']:.4f}", "p90 초": f"{r['p90']:.1f}"})
    B += [("h1", "8. 실행 이력"),
          ("table", pd.DataFrame(hist), "agent별 모든 실행 (같은 코드·설정)"),
          ("p", "문항 수가 다른 회차끼리는 직접 비교하지 않는다. 위 비교는 각 agent의 가장 최근 실행을 함께 푼 문항으로 맞춰 계산했다.")]

    # ------------------------------------------------------------------ 9. 한계
    judge = {summary(by_name[k]["experiment"]).get("config", {}).get("judge", {}).get("model") for k in names}
    models = {k: (summary(by_name[k]["experiment"]).get("config") or {}).get("answer", {}).get("model") for k in names}
    B += [("h1", "9. 한계"),
          ("bullets", [f"문항 수: {n}문항(dev)만 비교했다. dev는 90문항이다." if n < 90 else "dev 90문항 전체로 비교했다.",
                       f"질문 묶음: {', '.join(SETS.get(s, s) for s in sets_)}만 포함됐다.",
                       f"잡음: 같은 설정도 재실행하면 90문항 중 약 {NOISE}문항이 바뀐다.",
                       f"채점 모델: {', '.join(m for m in judge if m)}. 답변 모델: "
                       + ", ".join(f"{k} {models[k]}" for k in names)
                       + (" — 채점 모델과 답변 모델이 같아 자기 답변을 선호할 수 있다." if judge & set(models.values()) else "."),
                       "dev 문항으로만 비교했다(test는 최종 결정 뒤 다시 쓰지 않는 팀 규칙)."]),
          ("p", f"작성: {datetime.now():%Y-%m-%d %H:%M} · 원자료: out/agent_runs/ (각 agent의 실행·채점 결과), 각 브랜치의 코드와 설정")]
    return B


# ---------------------------------------------------------------- PDF (matplotlib, A4)

def plain(s) -> str:
    """맑은 고딕 has no U+2212 MINUS SIGN; print it as a hyphen-minus."""
    return str(s).replace("−", "-")


def _em(ch: str) -> float:
    """Approximate glyph width in em for 맑은 고딕: Hangul/CJK full width, Latin and digits about half, space less."""
    if ch == " ":
        return 0.3
    if ord(ch) < 0x2E80:
        return 0.55 if ch.isupper() or ch.isdigit() else 0.5
    return 1.0


def wrap(text: str, width_em: float) -> list[str]:
    """Greedy word wrap by measured width (textwrap counts characters, which wraps Korean far too early or late)."""
    lines, line, w = [], "", 0.0
    for word in text.split(" "):
        ww = sum(_em(c) for c in word)
        if line and w + 0.3 + ww > width_em:
            lines.append(line)
            line, w = word, ww
        else:
            line, w = (f"{line} {word}" if line else word), (w + 0.3 + ww if line else ww)
        while w > width_em:  # a single word longer than the line
            cut, cw = 0, 0.0
            while cut < len(line) and cw + _em(line[cut]) <= width_em:
                cw += _em(line[cut])
                cut += 1
            lines.append(line[:cut])
            line = line[cut:]
            w = sum(_em(c) for c in line)
    return lines + [line] if line or not lines else lines


def pdf_bytes(blocks: list[tuple], png_dir: Path | None = None) -> bytes:
    """A4 PDF of the blocks; png_dir also saves every page as a PNG (to look at the layout)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    from matplotlib.backends.backend_pdf import PdfPages

    for f in (FONT, FONT_BOLD):
        if f.exists():
            font_manager.fontManager.addfont(str(f))
    plt.rcParams.update({"font.family": "Malgun Gothic", "axes.unicode_minus": False, "pdf.fonttype": 42})

    W, H = 8.27, 11.69                       # A4 inches
    LEFT, RIGHT, TOP, BOTTOM = 0.75, 0.75, 0.8, 0.8
    width_in = W - LEFT - RIGHT
    buf = io.BytesIO()
    state = {"fig": None, "y": 0.0, "page": 0}

    def new_page():
        if state["fig"] is not None:
            finish()
        state["fig"] = plt.figure(figsize=(W, H))
        state["y"] = H - TOP
        state["page"] += 1

    def finish():
        fig = state["fig"]
        fig.text(W / 2 / W, 0.35 / H, f"선택한 agent 성능 비교 리포트 · {state['page']}", ha="center", fontsize=7, color="#64748b",
                 fontproperties=font_manager.FontProperties(fname=str(FONT), size=7))
        pdf.savefig(fig)
        if png_dir:
            png_dir.mkdir(parents=True, exist_ok=True)
            fig.savefig(png_dir / f"page_{state['page']:02d}.png", dpi=70)
        plt.close(fig)

    def need(height):
        if state["fig"] is None or state["y"] - height < BOTTOM:
            new_page()

    def text(s, size=9.5, weight="normal", color="#0f172a", indent=0.0, gap=0.06, bg=None):
        width_em = (width_in - indent) * 72 / size * (0.96 if weight == "bold" else 1.0)
        lines = []
        for para in plain(s).split("\n"):
            lines += wrap(para, width_em) or [""]
        line_h = size / 72 * 1.55
        for i, line in enumerate(lines):
            need(line_h)
            if bg and i == 0:
                h = line_h * len(lines) + 0.12
                rect = plt.Rectangle(((LEFT - 0.08) / W, (state["y"] - h + 0.06) / H), (width_in + 0.16) / W, h / H,
                                     transform=state["fig"].transFigure, color=bg, zorder=0)
                state["fig"].patches.append(rect)
            # pin the font file: by family name matplotlib sometimes picks the bold 맑은 고딕 for normal text
            fp = font_manager.FontProperties(fname=str(FONT_BOLD if weight == "bold" and FONT_BOLD.exists() else FONT), size=size)
            state["fig"].text((LEFT + indent) / W, (state["y"] - line_h * 0.8) / H, line, fontproperties=fp,
                              color=color, va="baseline")
            state["y"] -= line_h
        state["y"] -= gap

    def table(df: pd.DataFrame, caption: str):
        df = df.astype(str).map(plain)
        df.columns = [plain(c) for c in df.columns]
        chunk = 22
        for start in range(0, len(df), chunk):
            part = df.iloc[start:start + chunk]
            ncols = len(part.columns)
            fs = 7.5 if ncols <= 4 else 6.8
            # wrap long cells so rows stay readable
            col_em = max(5.0, width_in * 72 / fs / ncols * 0.9)
            cells = [["\n".join(wrap(v, col_em)) or v for v in row] for row in part.values.tolist()]
            heights = [max(c.count("\n") + 1 for c in row) for row in cells]
            head_lines = max(len(wrap(str(c), col_em)) for c in part.columns)
            h = (sum(heights) + head_lines + 0.6) * fs / 72 * 1.45 + 0.35
            need(h)
            text(caption + (" (계속)" if start else ""), size=8.5, weight="bold", color="#334155", gap=0.02)
            ax = state["fig"].add_axes([LEFT / W, (state["y"] - h + 0.3) / H, width_in / W, (h - 0.3) / H])
            ax.axis("off")
            tb = ax.table(cellText=cells, colLabels=["\n".join(wrap(str(c), col_em)) for c in part.columns],
                          loc="upper center", cellLoc="left", colLoc="left")
            tb.auto_set_font_size(False)
            tb.set_fontsize(fs)
            total = sum(heights) + head_lines
            for (r, c), cell in tb.get_celld().items():
                lines_ = head_lines if r == 0 else heights[r - 1]
                cell.set_height(lines_ / total * 0.98)
                cell.set_edgecolor("#cbd5e1")
                if r == 0:
                    cell.set_facecolor("#e2e8f0")
                    cell.set_text_props(fontweight="bold")
            state["y"] -= h + 0.08

    def chart(fn, caption):
        h = 2.6
        need(h + 0.4)
        text(caption, size=8.5, weight="bold", color="#334155", gap=0.02)
        fn(state["fig"], ((LEFT + 0.35) / W, (state["y"] - h + 0.55) / H, (width_in - 0.45) / W, (h - 0.85) / H))
        state["y"] -= h + 0.1

    def images(items, title):
        import matplotlib.image as mpimg
        per_row = 2
        col_w = (width_in - 0.3) / per_row
        for start in range(0, len(items), per_row):
            row = items[start:start + per_row]
            pics = [mpimg.imread(io.BytesIO(png), format="png") for png, _ in row]
            hs = [min(col_w * p.shape[0] / p.shape[1], 6.6) for p in pics]
            h = max(hs) + 0.9
            need(h + 0.3)
            text(title + (" (계속)" if start else ""), size=8.5, weight="bold", color="#334155", gap=0.05)
            top = state["y"]
            for i, (pic, ph, (_, cap)) in enumerate(zip(pics, hs, row)):
                pw = ph * pic.shape[1] / pic.shape[0]
                x0 = LEFT + i * (col_w + 0.3) + (col_w - pw) / 2
                ax = state["fig"].add_axes([x0 / W, (top - ph) / H, pw / W, ph / H])
                ax.imshow(pic)
                ax.axis("off")
                fp = font_manager.FontProperties(fname=str(FONT), size=7)
                for j, line in enumerate(wrap(plain(cap), col_w * 72 / 7)[:4]):
                    state["fig"].text((LEFT + i * (col_w + 0.3)) / W, (top - ph - 0.18 - j * 0.15) / H, line,
                                      fontproperties=fp, color="#334155")
            state["y"] = top - h

    with PdfPages(buf) as pdf:
        new_page()
        text("선택한 agent 성능 비교 리포트", size=18, weight="bold", gap=0.02)
        text(f"aim-rag-mini-project · {datetime.now():%Y-%m-%d %H:%M}", size=9, color="#64748b", gap=0.25)
        first_h1 = True
        for b in blocks:
            kind = b[0]
            if kind == "h1":
                if not first_h1:
                    new_page()
                first_h1 = False
                text(b[1], size=14, weight="bold", color="#1e3a8a", gap=0.12)
            elif kind == "h2":
                state["y"] -= 0.08
                text(b[1], size=11, weight="bold", color="#0f172a", gap=0.05)
            elif kind == "p":
                text(b[1])
            elif kind == "note":
                text(b[1], size=9.5, weight="bold", color="#14532d", bg="#dcfce7", gap=0.15)
            elif kind == "bullets":
                for item in b[1]:
                    lines = wrap(plain(item), (width_in - 0.17) * 72 / 9.5)
                    text("• " + lines[0], gap=0.0)
                    for rest in lines[1:]:
                        text(rest, indent=0.17, gap=0.0)
                    state["y"] -= 0.05
            elif kind == "table":
                table(b[1], b[2])
            elif kind == "chart":
                chart(b[1], b[2])
            elif kind == "images" and b[1]:
                images(b[1], b[2])
        finish()
    return buf.getvalue()
