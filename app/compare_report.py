"""Static HTML + PDF version of app/compare_app.py (same data, same look), for sharing.

    python app/compare_report.py [--pdf C:/Users/USER/Desktop/청크비교_세린vs섞은코드.pdf]

Writes out/chunk_compare_report.html and prints it to PDF with headless Edge.
"""

import argparse
import html
import json
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
MAX_CHARS = 1600
RUNS = [("serin", "세린님 청크", "dev_001e_chunk950chain_retrieval", "#94a3b8"),
        ("mixed", "섞은 코드", "dev_014_mixedchunk_retrieval", "#4f46e5"),
        ("header", "섞은 코드 + 머리말", "dev_014b_mixedchunk_header_retrieval", "#16a34a")]
METRICS = [("page_hit@5", "정답 쪽 찾음"), ("evid@5", "근거 문장 포함 (주 지표)"), ("mrr", "첫 정답 순위(MRR)"),
           ("gold@5", "정답 조각 수 (5개 중)")]

CSS = """
@page {size: A4; margin: 14mm 12mm;}
body {font-family: 'Malgun Gothic', 'Noto Sans KR', sans-serif; color:#0f172a; background:#fff; margin:0; font-size: 13px;}
h1 {font-weight: 800; letter-spacing: -0.5px; font-size: 1.9rem; margin: 0 0 14px 0;}
h3 {font-size: 1.15rem; margin: 22px 0 8px 0;}
.hero {background: linear-gradient(135deg,#eef2ff 0%,#e0f2fe 100%); border-radius: 18px; padding: 20px 24px; margin-bottom: 14px;}
.hero h2 {margin: 0 0 6px 0; font-size: 1.3rem;} .hero p {margin: 0; color: #334155;}
.grid {display:grid; grid-template-columns: repeat(3, 1fr); gap: 10px;}
.card {border: 1px solid #cbd5e1; border-radius: 14px; padding: 12px 14px; background: #f8fafc;}
.card h4 {margin: 0 0 4px 0;} .card p {margin: 0; color: #475569; font-size: 0.9rem;}
.metric .lab {color:#64748b; font-size: 0.82rem;} .metric .val {font-size: 1.6rem; font-weight: 800;}
.up {color:#166534; font-weight:700;} .down {color:#991b1b; font-weight:700;} .same {color:#64748b;}
table {border-collapse: collapse; width: 100%; font-size: 0.88rem;}
th, td {border-bottom: 1px solid #e2e8f0; padding: 5px 8px; text-align: right;} th:first-child, td:first-child {text-align:left;}
th {background:#f1f5f9;}
.chunk {border-left: 5px solid #94a3b8; background:#f1f5f9; border-radius: 8px; padding: 6px 10px; margin: 5px 0; font-size: 0.82rem; break-inside: avoid;}
.chunk.picked {border-left-color:#16a34a; background:#dcfce7;} .chunk.long {border-left-color:#dc2626; background:#fee2e2;}
.chunk .tag {font-size:0.75rem; color:#475569;}
.note {background:#fffbeb; border:1px solid #fde68a; border-radius:10px; padding:8px 12px; color:#78350f; margin: 8px 0;}
.legend span {display:inline-block; margin-right: 14px;} .legend i {display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:4px;}
.two {display:grid; grid-template-columns: 1fr 1fr; gap: 12px;}
.pb {break-before: page;}
.sub {color:#64748b; font-size: 0.85rem;}
"""


def load(exp: str):
    s = json.loads((RESULTS / exp / "summary.json").read_text(encoding="utf-8"))
    m = pd.DataFrame([json.loads(l) for l in (RESULTS / exp / "metrics.jsonl").read_text(encoding="utf-8").splitlines()
                      if l.strip()]).set_index("qid")
    return s, m


def delta(v: float, base: float, fmt: str = "{:+.3f}") -> str:
    d = v - base
    css = "up" if d > 1e-9 else "down" if d < -1e-9 else "same"
    return f'<span class="{css}">{fmt.format(d)}</span>'


def bars(groups: list[str], series: list[tuple[str, str, list[float]]], vmax: float, width=720, height=210) -> str:
    """Grouped vertical bar chart as inline SVG."""
    pad_l, pad_b, pad_t = 34, 34, 18
    gw = (width - pad_l) / len(groups)
    bw = gw * 0.7 / len(series)
    out = [f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" font-size="11">']
    for t in range(5):
        y = pad_t + (height - pad_t - pad_b) * (1 - t / 4)
        out.append(f'<line x1="{pad_l}" x2="{width}" y1="{y}" y2="{y}" stroke="#e2e8f0"/>'
                   f'<text x="{pad_l - 4}" y="{y + 4}" text-anchor="end" fill="#64748b">{vmax * t / 4:g}</text>')
    for gi, g in enumerate(groups):
        x0 = pad_l + gi * gw + gw * 0.15
        for si, (_, color, vals) in enumerate(series):
            v = vals[gi]
            h = (height - pad_t - pad_b) * v / vmax
            x = x0 + si * bw
            out.append(f'<rect x="{x:.1f}" y="{height - pad_b - h:.1f}" width="{bw - 3:.1f}" height="{h:.1f}" rx="3" fill="{color}"/>')
            label = f"{v:.3f}" if vmax <= 1 else f"{v:g}"
            out.append(f'<text x="{x + (bw - 3) / 2:.1f}" y="{height - pad_b - h - 4:.1f}" text-anchor="middle" fill="#0f172a">{label}</text>')
        out.append(f'<text x="{pad_l + gi * gw + gw / 2:.1f}" y="{height - pad_b + 16}" text-anchor="middle" fill="#334155">{html.escape(g)}</text>')
    out.append("</svg>")
    legend = "".join(f'<span><i style="background:{c}"></i>{html.escape(n)}</span>' for n, c, _ in series)
    return f'<div class="legend">{legend}</div>' + "".join(out)


def chunk_html(c: dict, css: str = "") -> str:
    text = html.escape(c["content"]).replace("\n", " ")
    where = "p." + "-".join(str(p) for p in sorted({c["pages"][0], c["pages"][-1]}))
    return (f'<div class="chunk {css}"><span class="tag">{len(c["content"]):,}자 · {where}</span><br>'
            f'{text[:300]}{"…" if len(text) > 300 else ""}</div>')


def build() -> str:
    loaded = {key: load(exp) for key, _, exp, _ in RUNS}
    sums = {key: loaded[key][0]["retrieval"] for key in loaded}
    data = json.loads((ROOT / "out" / "chunk_compare.json").read_text(encoding="utf-8"))
    st_ = data["stats"]
    p = [f"<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>청크 비교</title><style>{CSS}</style></head><body>"]
    p.append("<h1>✂️ 청크 비교: 세린님 vs 섞은 코드</h1>")
    p.append('<div class="hero"><h2>같은 문제, 같은 검색, 자르는 방법만 다르게</h2><p>세린님의 구조 단위 자르기(용어 하나, 조 하나, 나머지는 950자)에 '
             '대진님 코드의 두 가지를 더했습니다. ① 1,600자를 넘는 조각을 줄 끝에서 한 번 더 자르기, ② 조각 앞에 [문서 제목 | 쪽 | 조] 머리말 붙이기. '
             '개발용 90문항(정답 쪽이 있는 74문항)으로 검색만 비교했고 LLM은 쓰지 않았습니다. 시험용(test) 문항은 보지 않았습니다.</p></div>')
    p.append('<div class="grid">'
             '<div class="card"><h4>세린님 청크</h4><p>용어집은 용어 하나씩, 약관은 조 하나씩(1,600자 넘으면 ①② 항 앞에서 자름), 나머지 문서는 950/119자.</p></div>'
             '<div class="card"><h4>섞은 코드</h4><p>세린님 방식 + ①② 항이 없어 1,600자를 넘던 조각을 줄 끝에서 다시 잘라 어떤 조각도 1,600자를 넘지 않게.</p></div>'
             '<div class="card"><h4>섞은 코드 + 머리말</h4><p>위 방식 + 모든 조각 맨 앞에 [문서 제목 | p.쪽 | 제N조(…)] 한 줄. 잘린 조각도 조 이름 유지.</p></div></div>')

    p.append("<h3>검색 성적</h3><p class='sub'>같은 설정: 구조 단위 + 950/119 + hybrid 검색, k=5. 초록/빨강 숫자는 세린님 대비 차이.</p>")
    p.append("<table><tr><th>지표</th>" + "".join(f"<th>{n}</th>" for _, n, _, _ in RUNS) + "</tr>")
    for metric, label in METRICS:
        base = sums["serin"][metric]
        cells = [f"<td><b>{base:.3f}</b></td>"] + [f"<td><b>{sums[k][metric]:.3f}</b> ({delta(sums[k][metric], base)})</td>"
                                                    for k, _, _, _ in RUNS[1:]]
        p.append(f"<tr><td>{label}</td>{''.join(cells)}</tr>")
    p.append("</table>")
    p.append(bars([l for _, l in METRICS[:3]], [(n, c, [sums[k][m] for m, _ in METRICS[:3]]) for k, n, _, c in RUNS], 1.0))

    p.append("<h3>문항별로 누가 이겼나 (근거 문장 포함, evid@5)</h3><p class='sub'>같은 설정을 다시 돌려도 14문항 정도가 흔들리므로 "
             "좋아진 문항 − 나빠진 문항이 14를 넘어야 의미 있는 차이로 봅니다.</p>")
    base_m = loaded["serin"][1]
    gold_ids = base_m.index[base_m["evid@5"].notna()]
    p.append("<table><tr><th>비교</th><th>좋아진 문항</th><th>나빠진 문항</th><th>같음</th><th>순증</th></tr>")
    changed_rows = []
    for key, name, _, _ in RUNS[1:]:
        d = loaded[key][1].loc[gold_ids, "evid@5"] - base_m.loc[gold_ids, "evid@5"]
        up, down = int((d > 0).sum()), int((d < 0).sum())
        p.append(f"<tr><td>{name} vs 세린님</td><td>{up}</td><td>{down}</td><td>{int((d == 0).sum())}</td><td><b>{up - down:+d}</b></td></tr>")
        for qid, v in d[d != 0].items():
            changed_rows.append((name, qid, base_m.loc[qid, "evid@5"], loaded[key][1].loc[qid, "evid@5"], v))
    p.append("</table>")
    if changed_rows:
        p.append("<p class='sub' style='margin-top:8px'>달라진 문항</p><table><tr><th>비교</th><th>문항</th><th>세린님</th><th>비교 대상</th><th>차이</th></tr>")
        p += [f"<tr><td>{n}</td><td>{q}</td><td>{a:.3f}</td><td>{b:.3f}</td><td>{delta(b, a)}</td></tr>" for n, q, a, b, _ in changed_rows]
        p.append("</table>")

    p.append("<h3 class='pb'>조각 크기</h3><table><tr><th></th>" + "".join(f"<th>{n}</th>" for _, n, _, _ in RUNS) + "</tr>")
    for k, label, fmt in [("n", "조각 수", "{:,}"), ("mean", "평균 길이(자)", "{:.0f}"), ("median", "중간값(자)", "{:,}"),
                          ("max", "최대(자)", "{:,}"), ("over_max", f"{MAX_CHARS:,}자 초과", "{:,}")]:
        p.append(f"<tr><td>{label}</td>" + "".join(f"<td>{fmt.format(st_[r][k])}</td>" for r, *_ in RUNS) + "</tr>")
    p.append("</table>")
    bins = [0, 200, 400, 600, 800, 1000, 1200, 1600, 10_000]
    labels = ["~200", "~400", "~600", "~800", "~1000", "~1200", "~1600", "1600↑"]
    counts = {k: pd.cut(pd.Series(st_[k]["lens"]), bins, labels=labels).value_counts().reindex(labels).tolist() for k, *_ in RUNS}
    vmax = max(max(v) for v in counts.values())
    vmax = (int(vmax / 100) + 1) * 100
    p.append(bars(labels, [(n, c, counts[k]) for k, n, _, c in RUNS[:2]], vmax))
    p.append('<div class="note">머리말이 있는 쪽의 1,600자 초과 7개는 본문이 아니라 머리말 한 줄(약 30~45자)이 더해진 것입니다. '
             '본문은 섞은 코드와 같이 최대 1,593자입니다.</div>')

    p.append("<h3>길던 조각이 어떻게 달라졌나</h3><p class='sub'>세린님 방식에서 1,600자를 넘던 조각과, 섞은 코드 + 머리말에서 그 자리에 생긴 조각.</p>")
    for c in [c for c in data["chunks"]["serin"] if len(c["content"]) > MAX_CHARS]:
        pages = set(c["pages"])
        parts = [x for x in data["chunks"]["header"] if x["source"] == c["source"] and set(x["pages"]) & pages
                 and x["content"].split("\n", 1)[-1][:40] in c["content"]]
        p.append(f"<p><b>{html.escape(c['source'])}</b> p.{c['page']} · {len(c['content']):,}자 → {len(parts)}조각</p>")
        p.append('<div class="two"><div>' + chunk_html(c, "long") + "</div><div>" + "".join(chunk_html(x, "picked") for x in parts) + "</div></div>")

    mx, hd = sums["mixed"], sums["header"]
    p.append("<h3>결론</h3><ul>"
             f"<li><b>잘린 조각</b>: 섞은 코드는 1,600자 넘는 조각을 없앴습니다(7개 → 0개). 조각 수는 {st_['serin']['n']:,} → {st_['mixed']['n']:,}개로 거의 같습니다.</li>"
             f"<li><b>검색 성적</b>: 근거 포함(evid@5) 세린님 {sums['serin']['evid@5']:.3f} → 섞은 코드 {mx['evid@5']:.3f} → 머리말까지 {hd['evid@5']:.3f}.</li>"
             "<li>문항별 순증이 ±14 안쪽이면 운에 따른 흔들림과 구별되지 않습니다.</li></ul>")
    p.append("</body></html>")
    return "\n".join(p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", default=str(Path.home() / "Desktop" / "청크비교_세린vs섞은코드.pdf"))
    args = ap.parse_args()
    out = ROOT / "out" / "chunk_compare_report.html"
    out.write_text(build(), encoding="utf-8")
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={args.pdf}", out.as_uri()], check=True, capture_output=True)
    print(out, "->", args.pdf)


if __name__ == "__main__":
    main()
