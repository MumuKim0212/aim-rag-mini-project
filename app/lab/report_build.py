"""Content of the lab report (7. Report) and its PDF. The web page and the PDF draw the same blocks:

    ("h1" | "h2" | "p" | "note", text), ("bullets", [text, ...]), ("table", DataFrame, caption), ("chart", fn, caption)

A chart fn draws on a matplotlib Axes. Numbers are read from results/, out/agent_runs/ and corpus/ when the report
is built, so the text and the tables always agree with the files. The PDF is A4 portrait, drawn with matplotlib
(PdfPages) in 맑은 고딕, with no extra package.
"""

import io
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from lab.common import BA, ROOT, SYSTEMS, final_frame, final_stats, golden, pages, summary

FONT = Path("C:/Windows/Fonts/malgun.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/malgunbd.ttf")
COLORS = ["#2563eb", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#06b6d4", "#64748b"]

# dev chain of adopted changes (EVALUATION.md 3절), label -> experiment
CHAIN = [("처음 RAG (800/100, 벡터, lite)", "dev_000_baseline"), ("구조 단위 청킹 + 900", "dev_002b_structure900"),
         ("Hybrid 검색", "dev_004_hybrid"), ("답변 모델 3.6-flash", "dev_007_flash36"), ("답변 프롬프트 v2", "dev_010_answerv2"),
         ("답변 프롬프트 v4", "dev_012_flash36_v4"), ("LLM 재정렬 15→5 (T2)", "dev_013_rerank_flash36_fix"),
         ("작은 모델 + 재정렬 (T4)", "dev_013b_rerank_lite_fix"), ("Agent T3", "dev_008b_agent950"), ("Agent v2", "dev_014_agent_v2")]


def _paired(a: dict, b: dict) -> dict:
    from evalkit.paired import compare
    return compare(a, b, max_score=2.0)


def _final_effects() -> pd.DataFrame:
    frames = {k: final_frame(k).set_index("qid")["correctness"].to_dict() for k in SYSTEMS}
    rows = []
    for name, a, b in (("설정 튜닝", "T1", "T2"), ("구조 (Agent)", "T2", "T3"), ("모델 크기", "T2", "T4"), ("최종 vs 처음", "T1", "T4")):
        r = _paired(frames[a], frames[b])
        rows.append({"효과": name, "비교": f"{b} − {a}", "점수 차이": f"{r['diff']:+.3f}",
                     "95% 신뢰구간": f"[{r['ci95'][0]:+.3f}, {r['ci95'][1]:+.3f}]",
                     "우세/열세/같음": f"{len(r['b_better'])}/{len(r['a_better'])}/{r['same']}",
                     "판정": "차이 있음" if r["ci95"][0] > 0 or r["ci95"][1] < 0 else "구별 안 됨"})
    return pd.DataFrame(rows)


def _agent_head_to_head():
    """The two distinct branch agents on the largest question count both ran (same questions)."""
    shown, _ = BA.distinct_agents(BA.scan(fetch=False))
    runs = {}
    for a in shown:
        rs = [r for r in BA.read_log() if r["status"] == "done" and r["branch"] == a["branch"] and r["config"] == a["config"]
              and r.get("same_code_id") == a["same_code_id"] and (BA.RESULTS / r["experiment"] / "grades.jsonl").exists()]
        if rs:
            runs[a["label"]] = (a, max(rs, key=lambda r: (r["n"], r["started"])))
    if len(runs) < 2:
        return None
    (la, (aa, ra)), (lb, (ab, rb)) = list(runs.items())[:2]
    g = lambda r: {x["qid"]: x["correctness"] for x in map(json.loads, (BA.RESULTS / r["experiment"] / "grades.jsonl").read_text(encoding="utf-8").splitlines())}  # noqa: E731
    ga, gb = g(ra), g(rb)
    common = sorted(set(ga) & set(gb))
    res = _paired({q: ga[q] for q in common}, {q: gb[q] for q in common})
    table = pd.DataFrame({
        la: {"만든 사람": aa["maker"], "agent 파일 · 설정": f"{aa['impl'].split('/')[-1]} · {aa['config']}", "문항 수": ra["n"],
             "정답 점수": f"{ra['correctness']:.3f}", "완전 정답률": f"{ra['fully_correct']:.3f}", "USD/문항": f"{ra['usd_per_question']:.4f}",
             "LLM 호출/문항": f"{ra['llm_per_question']:.1f}", "p90 초": f"{ra['p90']:.1f}"},
        lb: {"만든 사람": ab["maker"], "agent 파일 · 설정": f"{ab['impl'].split('/')[-1]} · {ab['config']}", "문항 수": rb["n"],
             "정답 점수": f"{rb['correctness']:.3f}", "완전 정답률": f"{rb['fully_correct']:.3f}", "USD/문항": f"{rb['usd_per_question']:.4f}",
             "LLM 호출/문항": f"{rb['llm_per_question']:.1f}", "p90 초": f"{rb['p90']:.1f}"}})
    sets = sorted({x["set"] for x in map(json.loads, (BA.RESULTS / ra["experiment"] / "metrics.jsonl").read_text(encoding="utf-8").splitlines())})
    return {"table": table, "names": (la, lb), "runs": (ra, rb), "res": res, "n": len(common), "sets": sets}


def build() -> list[tuple]:
    S = {k: final_stats(k) for k in SYSTEMS}
    eff = _final_effects()
    dev = {e: (summary(e).get("scores") or {}).get("correctness_mean") for _, e in CHAIN}
    pg = pages()
    assets_path = ROOT / "out" / "doc_assets.json"
    assets = json.loads(assets_path.read_text(encoding="utf-8")) if assets_path.exists() else []
    items = golden()
    h2h = _agent_head_to_head()
    t1, t2, t3, t4 = (S[k] for k in ("T1", "T2", "T3", "T4"))
    e = {r["효과"]: r for r in eff.to_dict("records")}
    B = []

    # ------------------------------------------------------------------ 1. 의견 및 결론 (first page)
    B += [("h1", "1. 의견 및 결론"),
          ("p", f"금융 PDF 23개를 근거로 답하는 RAG를 처음 만든 뒤(T1), dev 90문항으로 한 번에 한 요소씩 바꾸며 개선했고, 고정한 네 시스템을 "
                f"test 131문항(제공 90 + 자작 41)에서 한 번씩 실행했다. 처음 RAG {t1['정답 점수']:.3f}에서 큰 모델 개선판 {t2['정답 점수']:.3f}, "
                f"Agent {t3['정답 점수']:.3f}, 최종 시스템(작은 모델) {t4['정답 점수']:.3f}이 나왔다."),
          ("note", f"결론: 최종 시스템은 T4(구조 단위 청킹 + Hybrid 검색 + LLM 재정렬 + gemini-3.5-flash-lite + 프롬프트 v4)다. "
                   f"처음보다 정답 점수가 {e['최종 vs 처음']['점수 차이']} 올랐고(95% 신뢰구간 {e['최종 vs 처음']['95% 신뢰구간']}, 잡음보다 확실히 큼), "
                   f"문항당 {t4['USD/문항']:.4f} USD, p90 {t4['p90 초']:.1f}초로 운영할 수 있다. 큰 모델(T2)보다 점수는 "
                   f"{t2['정답 점수'] - t4['정답 점수']:.3f} 낮지만 그 차이는 신뢰구간이 0을 포함하고, 비용은 {t4['USD/문항'] / t2['USD/문항']:.2f}배다."),
          ("h2", "결론 1. 성능을 올린 것은 '검색을 고치는 일'이었다"),
          ("bullets", [
              f"설정 튜닝 전체 효과(T2 − T1)는 {e['설정 튜닝']['점수 차이']}, 신뢰구간 {e['설정 튜닝']['95% 신뢰구간']}로 이번 실습에서 가장 크고 확실한 개선이다.",
              "그중 잡음을 넘은 단일 변경은 LLM 재정렬(Hybrid 후보 15개 → 5개) 하나였다(카드 013, 순승 +7, dev 0.883 → 0.928). "
              "정답 청크가 후보 15개 안에는 있는데 상위 5개에 못 들던 문항을 정확히 겨냥했고, 근거 포함률이 0.861 → 0.938로 올랐다.",
              "구조 단위 청킹(용어집은 용어 1개, 약관은 조 1개)은 점수 차이는 작았지만 800자 청크에 용어 약 8개가 섞여 검색에서 묻히던 용어 정의 "
              "4문항을 해결했다. '청크를 의미 단위로 자르는 것'이 '청크 크기를 고르는 것'보다 중요했다.",
              "반대로 청크 크기 탐색(400~1,200), 답변 프롬프트 수정, BM25 단독, k 조정은 모두 잡음(같은 설정 재실행 시 90문항 중 14문항이 바뀜) "
              "범위 안이었다."]),
          ("h2", "결론 2. Agent 구조는 이번 문제에서 값을 하지 못했다"),
          ("bullets", [
              f"같은 검색·모델·프롬프트 위에서 그래프만 바꾼 효과(T3 − T2)는 {e['구조 (Agent)']['점수 차이']}, 신뢰구간 "
              f"{e['구조 (Agent)']['95% 신뢰구간']}로 0을 포함한다. 대신 비용 {t3['USD/문항'] / t2['USD/문항']:.1f}배, p90 시간 "
              f"{t3['p90 초'] / t2['p90 초']:.1f}배가 든다.",
              "재검색이 실제로 새 근거를 찾아 답에 쓴 경우는 적었다(카드 008: 재검색 9문항 중 재검색 청크를 인용한 것 3문항). "
              "재정렬이 들어간 뒤에는 첫 검색이 이미 충분해 재검색할 일이 거의 없었다.",
              "답변 검토·1회 수정을 넣은 Agent v2(카드 014)는 겨냥한 불완전 답변 10문항을 하나도 잡지 못했고(dev 0.928, T2와 같음), "
              "청크 잘림을 진단해 페이지를 넓히는 복구 Agent(카드 015)는 사전 점검에서 개선 여지가 2문항뿐이라 본 실행 기준을 넘지 못했다.",
          ] + ([f"팀원 브랜치의 agent 두 개({h2h['names'][0]}, {h2h['names'][1]})를 같은 dev {h2h['n']}문항으로 돌려 보면 "
                f"{h2h['runs'][0]['correctness']:.3f} 대 {h2h['runs'][1]['correctness']:.3f}, 신뢰구간 "
                f"[{h2h['res']['ci95'][0]:+.3f}, {h2h['res']['ci95'][1]:+.3f}]로 구별되지 않는다. 비용은 "
                f"{h2h['runs'][0]['usd_per_question']:.4f} 대 {h2h['runs'][1]['usd_per_question']:.4f} USD/문항이다."] if h2h else [])),
          ("h2", "결론 3. 정확도와 비용은 '작은 모델 + 좋은 검색'이 가장 균형이 좋다"),
          ("bullets", [
              f"T4는 T2보다 {e['모델 크기']['점수 차이']}(신뢰구간 {e['모델 크기']['95% 신뢰구간']})로 구별되지 않을 만큼만 낮고, "
              f"비용은 {t4['USD/문항']:.4f} 대 {t2['USD/문항']:.4f} USD, p90은 {t4['p90 초']:.1f}초 대 {t2['p90 초']:.1f}초다.",
              "작은 모델이 약한 곳은 보고서·정책 자료(추가 자료) 세트로, 여러 조건을 한 번에 정리해야 하는 문항이다. "
              "용어·약관 질문은 큰 모델과 차이가 거의 없다.",
              "1,000문항에 약 3.6 USD로, 실제 상담 보조로 쓰기에 무리가 없는 비용이다."]),
          ("h2", "의견: 남은 문제와 다음에 할 일"),
          ("bullets", [
              "T4가 틀린 문항의 약 61%는 '근거는 다 찾았는데 답이 불완전'한 경우다(예외 조항, 비중, 비교 차액 누락). 검색을 더 고쳐도 줄지 않는다. "
              "다음 개선은 답변 단계에서 '질문이 묻는 항목을 빠짐없이 답했는지' 점검하는 쪽이어야 한다고 본다. 다만 카드 014의 일반적인 검토 노드는 "
              "효과가 없었으므로, 질문을 항목으로 쪼개고 항목마다 근거를 대응시키는 방식처럼 더 구조적인 접근이 필요하다.",
              "답변 불가 질문에서 본문은 '자료에 없다'고 쓰고 status는 answered로 붙이는 불일치가 있다. 본문과 status를 맞추는 코드 검사는 "
              "비용 없이 대응 일치율을 올릴 수 있는 가장 싼 개선이다.",
              "일상어 질문이 용어집의 정식 용어를 못 찾는 실패(예: '이자 깎아달라' → 금리인하요구권)는 질문 재작성으로 겨냥할 수 있지만 "
              "test에서 2문항뿐이라 우선순위는 낮다.",
              "Agent는 지금 체인에서는 비용만 늘리므로 최종 시스템에 넣지 않는 것이 맞다. 다시 시도한다면 재검색보다 '답변 완결성 점검'을 "
              "그래프의 중심에 두는 설계가 데이터와 맞는다.",
              "팀원 agent 비교는 90문항 전체로 다시 돌려야 결론을 낼 수 있다. 앞 30문항은 모두 '기본 질문' 세트라 함정 질문·추가 자료에서의 "
              "차이를 보지 못한다."]),
          ("h2", "이 결론을 얼마나 믿을 수 있나"),
          ("bullets", [
              "같은 설정을 다시 돌리면 90문항 중 약 14문항이 바뀐다. 그래서 모든 판단은 문항별 짝비교의 신뢰구간으로 했고, 0.01 수준의 차이는 해석하지 않았다.",
              "설정을 dev로 골랐기 때문에 test가 약 0.05 낮게 나왔다(T2 dev 0.928 → 제공 test 0.883). dev 수치는 낙관적이다.",
              "채점 모델이 T2·T3의 답변 모델과 같아 자기 답변을 선호할 수 있다. 채점 11건을 사람이 대조해 9건이 맞았다.",
              "제공 test 90문항은 T4를 고르면서 한 번 더 봤다. T4를 고른 이유는 가격이며 test 점수가 아니다."]),
          ]

    # ------------------------------------------------------------------ 2. 개요
    doc_tables = sum(a["pdf_tables"] for a in assets)
    doc_images = sum(a["images"] for a in assets)
    vlm_pages = sum(1 for p in pg if p.get("visual_mode") == "added")
    split = pd.Series([i.get("split") for i in items.values()]).value_counts()
    B += [("h1", "2. 실습 개요"),
          ("p", "과제: 금융 PDF를 검색해 파일명·페이지 근거와 함께 한국어로 답하고, 답할 수 없으면 보류·되묻기·거절하는 RAG Agent를 만들고, "
                "평가 지표와 평가 루프를 직접 만들어 개선한다."),
          ("table", pd.DataFrame({"항목": ["PDF", "페이지", "PDF 속 표", "PDF 속 이미지", "VLM으로 표·그림을 글로 보충한 페이지",
                                          "제공 질문 (dev / test)", "자작 질문 (test)"],
                                  "값": [f"{len({p['file'] for p in pg})}개", f"{len(pg)}쪽", f"{doc_tables}개" if assets else "-",
                                        f"{doc_images}개" if assets else "-", f"{vlm_pages}쪽",
                                        f"180 ({split.get('dev', 0)} / 90)", "41 (self2)"]}), "데이터와 골든셋"),
          ("bullets", ["범위 A(용어집 + 표준약관 15개)와 범위 B(23개 전부)로 나눠 질문 세트마다 검색 범위를 정했다.",
                       "골든셋의 근거 문장 353개를 페이지 텍스트와 자동 대조해 모두 일치시켰고, 정답 페이지·근거 문장 포함률을 LLM 없이 계산했다.",
                       "모든 실험은 결과를 보기 전에 카드에 가설과 채택 기준을 적고(사전 등록), test는 최종 설정을 고정한 뒤 한 번만 실행했다."])]

    # ------------------------------------------------------------------ 3. 실험 과정
    chain = pd.DataFrame([{"단계": n, "dev 정답 점수": dev[e_]} for n, e_ in CHAIN if dev.get(e_) is not None])

    def chain_chart(ax):
        d = chain
        ax.plot(range(len(d)), d["dev 정답 점수"], color="#94a3b8", zorder=1)
        ax.scatter(range(len(d)), d["dev 정답 점수"], s=60, zorder=2,
                   color=["#ef4444" if "Agent" in s else "#2563eb" for s in d["단계"]])
        for i, (s, v) in enumerate(zip(d["단계"], d["dev 정답 점수"])):
            ax.annotate(f"{v:.3f}", (i, v), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=7)
        ax.set_xticks(range(len(d)))
        ax.set_xticklabels(d["단계"], rotation=35, ha="right", fontsize=7)
        ax.axhline(0.722, color="#ef4444", ls="--", lw=0.8)
        ax.set_ylabel("dev 정답 점수")
        ax.set_ylim(0.65, 1.0)
        ax.grid(axis="y", alpha=0.3)

    B += [("h1", "3. 실험 과정 (dev 90문항)"),
          ("p", "한 번에 한 요소만 바꾸고, 채택된 변경이 다음 실험의 기준이 되었다. 아래 점수는 LLM이 답하고 LLM이 채점한 dev 정답 점수다."),
          ("chart", chain_chart, "채택된 변경의 dev 정답 점수 (빨간 점 = Agent, 빨간 점선 = 처음 RAG 0.722)"),
          ("table", pd.DataFrame([
              ["청크 크기 (001)", "400~1,200 탐색 → 950", "점수 차이는 잡음 범위", "950 채택 (검색 지표 최고)"],
              ["구조 단위 청킹 (002)", "용어집 용어 1개, 약관 조 1개", "근거 포함률 0.795, 용어 정의 4문항 해결", "채택"],
              ["검색 방식 (004)", "Hybrid (벡터 + BM25)", "0.772", "채택 (기준 미달, 사용자 결정)"],
              ["검색량 (005)", "k=3 / 8", "k=8은 문맥 길이 상한 초과", "k=5 유지"],
              ["답변 모델 (007)", "lite → 3.6-flash", "0.822", "채택 (비용 2.3배)"],
              ["프롬프트 (010, 012)", "v2 / v4", "0.861 / 0.883", "채택 (각각 잡음 범위)"],
              ["LLM 재정렬 (013)", "후보 15 → 5", "0.883 → 0.928, 순승 +7", "채택 (유일하게 잡음 밖)"],
              ["작은 모델 (011, 013b)", "lite + v4 + 재정렬", "0.894", "최종 채택 (가격)"],
              ["Agent T3 / v2 (008, 014)", "재검색 / 답변 검토", "0.939 / 0.928", "채택 안 함 (비용 대비 이득 없음)"],
              ["복구 Agent (015)", "청크 잘림 진단 → 페이지 확장", "개선 여지 2문항 < 기준 3", "본 실행 생략"],
              ["혼합 청킹 (014 mixed)", "글자 수 상한 자르기", "근거 포함률 −0.008", "채택 안 함"]],
              columns=["실험 (카드)", "바꾼 것", "결과", "결정"]), "실험별 결과와 결정")]

    # ------------------------------------------------------------------ 4. Agent
    B += [("h1", "4. Agent"),
          ("p", "Agent는 LangGraph로 질문 유형 분류 → 검색 → 근거 판단 → (부족하면 검색어 재작성 후 재검색) → 답변 → 인용 확인 순서로 만들었다. "
                "v2는 답변 검토와 1회 수정을, 복구 Agent는 근거 부족의 원인 진단(청크 잘림 / 다른 근거 필요 / 글자 깨짐)과 페이지 확장을 더했다.")]
    if h2h:
        B += [("table", h2h["table"].reset_index().rename(columns={"index": "항목"}),
               f"팀원 브랜치 agent 비교 (같은 dev {h2h['n']}문항, 세트: {', '.join(h2h['sets'])})"),
              ("p", f"짝비교: {h2h['names'][1]}가 우세한 문항 {len(h2h['res']['b_better'])}개({', '.join(h2h['res']['b_better']) or '-'}), "
                    f"{h2h['names'][0]}가 우세한 문항 {len(h2h['res']['a_better'])}개({', '.join(h2h['res']['a_better']) or '-'}), "
                    f"점수 차이 {h2h['res']['diff']:+.3f}, 95% 신뢰구간 [{h2h['res']['ci95'][0]:+.3f}, {h2h['res']['ci95'][1]:+.3f}] → 구별 안 됨.")]

    # ------------------------------------------------------------------ 5. 최종 test
    final = pd.DataFrame({f"{k} {SYSTEMS[k][0]}": {
        "정답 점수": f"{v['정답 점수']:.3f}", "완전 정답률": f"{v['완전 정답률']:.3f}", "대응 일치율": f"{v['대응 일치율']:.3f}",
        "출처 일치율": f"{v['출처 일치율']:.3f}", "LLM 호출/문항": f"{v['LLM 호출/문항']:.2f}", "USD/문항": f"{v['USD/문항']:.4f}",
        "p90 초": f"{v['p90 초']:.1f}"} for k, v in S.items()}).reset_index().rename(columns={"index": "지표"})

    def final_chart(ax):
        names = list(S)
        vals = [S[k]["정답 점수"] for k in names]
        bars = ax.bar(names, vals, color=["#94a3b8", "#2563eb", "#ef4444", "#10b981"])
        for b, v, k in zip(bars, vals, names):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.01, f"{v:.3f}\n{S[k]['USD/문항']:.4f} USD", ha="center", fontsize=8)
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("test 정답 점수")
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels([f"{k}\n{SYSTEMS[k][0]}" for k in names], fontsize=8)

    B += [("h1", "5. 최종 test (131문항)"),
          ("chart", final_chart, "네 시스템의 test 정답 점수와 문항당 비용"),
          ("table", final, "최종 test 지표"),
          ("table", eff, "효과 나눠 보기 (문항별 짝비교)")]

    # ------------------------------------------------------------------ 6. 한계
    B += [("h1", "6. 평가의 한계"),
          ("bullets", ["잡음: 같은 설정 재실행 시 90문항 중 14문항이 바뀐다. 한 문항 차이(0.011)는 해석하지 않았다.",
                       "dev 낙관: 설정을 dev로 골라 test가 약 0.05 낮다.",
                       "LLM 채점자: T2·T3의 답변 모델과 채점 모델이 같다(자기 선호 가능성). 엄격한 쪽 오류 1건(POS011)을 확인했다.",
                       "본문 기준 채점: status 라벨이 틀려도 본문이 맞으면 점수를 받는다. 라벨은 대응 일치율로 따로 본다.",
                       "정답 단위는 페이지다. 여러 쪽에 걸친 근거는 근거 문장 포함률로 함께 봤다.",
                       "팀원 agent 비교는 dev 앞부분 일부 문항(한 세트)만 썼다."]),
          ("p", f"작성: {datetime.now():%Y-%m-%d %H:%M} · 원자료: results/, out/agent_runs/, submission/EVALUATION.md, experiments/")]
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
        fig.text(W / 2 / W, 0.35 / H, f"금융 문서 RAG 실습 리포트 · {state['page']}", ha="center", fontsize=7, color="#64748b")
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
        h = 3.2
        need(h + 0.4)
        text(caption, size=8.5, weight="bold", color="#334155", gap=0.02)
        ax = state["fig"].add_axes([(LEFT + 0.55) / W, (state["y"] - h + 0.75) / H, (width_in - 0.7) / W, (h - 0.9) / H])
        fn(ax)
        for lab in ax.get_xticklabels() + ax.get_yticklabels():
            lab.set_fontsize(7)
        state["y"] -= h + 0.1

    with PdfPages(buf) as pdf:
        new_page()
        text("금융 문서 RAG 실습 리포트", size=18, weight="bold", gap=0.02)
        text(f"aim-rag-mini-project · {datetime.now():%Y-%m-%d}", size=9, color="#64748b", gap=0.25)
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
        finish()
    return buf.getvalue()
