"""에이전트 실행·흐름 보기 (카드 015 복구 에이전트 / 세린님 T3 에이전트).

같은 저장소의 에이전트(src/rag/agent_repair.py, src/rag/agent.py)를 불러와 질문 하나를 실행한 뒤 지나간 노드와
판단을 한글로 보여준다. 처음 한 번은 인덱스가 필요하다: python scripts/build_index.py --config configs/015-context-repair.yaml

    python agent.py                                  # 예시 문항 ADD-HP09 (청크 잘림 → 페이지 확장 경로)
    python agent.py --qid POS001                     # dev 골드셋 문항 하나 (정답 페이지와 비교)
    python agent.py "주택연금 가입 나이 조건은?" --scope B   # 직접 쓴 질문 (A: 용어집+약관, B: 전체 23개 PDF)
    python agent.py --mode t3 --qid POS001           # 복구 노드가 없는 세린님 T3 에이전트
    python agent.py --graph                          # 실행 없이 한글 흐름도만 out/agent_flow_<mode>.png 로 저장

질문 1개에 LLM 4–6회(약 0.006–0.02 USD)를 쓴다. test 세트 문항은 실행하지 않는다.
흐름도는 agent_langgraph.ipynb 에서 그림으로 볼 수 있다.
"""

import argparse
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get("AGENT_REPO", HERE))  # 이 파일이 있는 저장소 (다른 체크아웃을 쓰려면 AGENT_REPO)
CONFIGS = {"repair": "configs/015-context-repair.yaml", "t3": "configs/008b-agent-950.yaml"}
EXAMPLE_QID = "ADD-HP09"

NODES = {
    "__start__": "시작",
    "__end__": "끝",
    "classify": "질문 유형 분류",
    "retrieve": "문서 검색",
    "grade": "근거 충분한지 판단",
    "diagnose": "근거 진단<br>충분한가, 왜 부족한가",
    "expand_context": "잘린 청크를<br>페이지 전체로 확장",
    "rewrite": "검색어 다시 쓰기",
    "flag_page": "깨진 페이지 기록<br>나중에 다시 추출",
    "generate": "답변 작성",
    "cite_check": "인용 번호 확인",
    "check": "답변 검토",
}
EDGES = {  # (출발, 도착) -> 분기 설명
    ("diagnose", "generate"): "근거 충분 또는<br>재검색 한도 소진",
    ("diagnose", "expand_context"): "청크가 잘림",
    ("diagnose", "rewrite"): "다른 근거가 필요",
    ("diagnose", "flag_page"): "글자가 깨짐",
    ("grade", "generate"): "근거 충분 또는<br>재검색 한도 소진",
    ("grade", "rewrite"): "근거 부족",
    ("cite_check", "generate"): "인용 오류:<br>1회 다시 작성",
    ("cite_check", "__end__"): "통과",
    ("cite_check", "check"): "검토로",
    ("check", "generate"): "문제 있음: 1회 수정",
    ("check", "__end__"): "통과",
}
QTYPES = {"document": "문서로 답할 질문", "needs_info": "질문자 정보가 더 필요", "inappropriate": "부적절한 요청",
          "injection": "지시문 주입 포함"}
CAUSES = {"none": "-", "cut": "청크가 잘림", "not_found": "다른 근거가 필요", "garbled": "글자가 깨짐"}
STATUS = {"answered": "답변", "abstained": "보류", "clarify": "되묻기", "refused": "거절"}


def _import_repo():
    if not (REPO / "src" / "rag" / "agent_repair.py").exists():
        sys.exit(f"{REPO} 에 src/rag/agent_repair.py 가 없습니다. LimDaeJin/agent 브랜치에서 실행하거나 AGENT_REPO 를 지정하세요.")
    for p in (str(REPO), str(REPO / "src")):
        if p not in sys.path:
            sys.path.insert(0, p)


def load_agent(mode: str = "repair"):
    """(에이전트, 설정)을 돌려준다. API 키와 인덱스는 질문을 실행할 때만 필요하다."""
    _import_repo()
    from rag.config import load_config
    from rag.env import setup
    from rag.systems import build_system
    setup()  # .env 읽기, LangSmith 추적 끄기
    cfg = load_config(REPO / CONFIGS[mode])
    return build_system(cfg), cfg


def korean_mermaid(agent, path: list[str] | None = None) -> str:
    """LangGraph가 그린 mermaid의 노드·분기 이름을 한글로 바꾼다. path를 주면 지나간 노드를 색칠한다."""
    return translate(agent.graph.get_graph().draw_mermaid(), path)


def translate(text: str, path: list[str] | None = None) -> str:
    """draw_mermaid() 결과를 한글로 바꾼다 (다른 브랜치 agent의 그래프 텍스트에도 쓴다).
    mermaid.ink 렌더러는 따옴표 안의 <br> 뒤 괄호를 거부하므로 이름에 괄호를 쓰지 않는다."""
    text = re.sub(r"^---.*?---\n", "", text, flags=re.S)  # 머리말(config) 제거
    lines = []
    for line in text.splitlines():
        node = re.match(r"^\s*(\w+)\((?:\[)?(?:<p>)?\w+(?:</p>)?(?:\])?\)(:::\w+)?;?$", line)
        edge = re.match(r"^\s*(\w+)\s+(-->|-\.->|-\.\s*&nbsp;(\w+)&nbsp;\s*\.->)\s+(\w+);$", line)
        if node:
            name, cls = node.group(1), node.group(2) or ""
            shape = ('(["{}"])' if name.startswith("__") else '("{}")').format(NODES.get(name, name))
            lines.append(f"\t{name}{shape}{cls}")
        elif edge:
            src, arrow, _, dst = edge.groups()
            label = EDGES.get((src, dst))
            if label and arrow != "-->":
                lines.append(f'\t{src} -. "{label}" .-> {dst};')
            elif label:
                lines.append(f'\t{src} -- "{label}" --> {dst};')
            else:
                lines.append(f"\t{src} {'-->' if arrow == '-->' else '-.->'} {dst};")
        else:
            lines.append(line)
    if path:
        lines.append("\tclassDef visited fill:#ffd166,stroke:#b5651d,stroke-width:2px")
        lines.extend(f"\tclass {n} visited" for n in dict.fromkeys(path))
    return "\n".join(lines)


def visited_path(steps: dict) -> list[str]:
    """steps["decisions"]에서 지나간 노드 순서를 되살린다 (검색·답변 노드는 판단 기록이 없어서 앞뒤로 끼워 넣는다)."""
    path = ["__start__"]
    for d in steps.get("decisions", []):
        node = d["node"]
        if node == "classify":
            path += ["classify", "retrieve"]
        elif node == "rewrite":
            path += ["rewrite", "retrieve"]
        elif node == "cite_check":
            path += ["generate", "cite_check"]
        else:
            path.append(node)
    return path + ["__end__"]


def describe(result: dict) -> list[str]:
    """실행 결과를 단계별 한글 설명으로 바꾼다."""
    steps, out, searches = result["steps"], [], iter(result.get("searches", []))
    for i, d in enumerate(steps.get("decisions", []), 1):
        node = d["node"]
        if node == "classify":
            out.append(f"{i}. 질문 유형 분류: {QTYPES.get(d['type'], d['type'])}")
            s = next(searches, None)
            if s:
                query = s["query"] if len(s["query"]) <= 40 else s["query"][:40] + "…"
                out.append(f"   → 문서 검색: \"{query}\" → 청크 {len(s['chunk_ids'])}개")
        elif node in ("diagnose", "grade"):
            if d.get("skipped"):
                out.append(f"{i}. 근거 판단 건너뜀 ({QTYPES.get(d['skipped'], d['skipped'])}: 답변 단계가 처리)")
            elif d.get("sufficient"):
                out.append(f"{i}. 근거 판단: 충분")
            else:
                cause = f", 원인: {CAUSES.get(d.get('cause'), d.get('cause'))}" if "cause" in d else ""
                out.append(f"{i}. 근거 판단: 부족{cause}\n   빠진 정보: {d.get('missing', '')}")
        elif node == "expand_context":
            pages = ", ".join(f"{f} p.{p}" for f, p in d["pages"]) or "없음(글자 수 상한)"
            out.append(f"{i}. 페이지 전체로 확장: {pages} (문맥 {d['chars']:,}자) → 다시 근거 판단")
        elif node == "rewrite":
            s = next(searches, None)
            out.append(f"{i}. 검색어 다시 쓰기: \"{d['query']}\"" + (f" → 청크 {len(s['chunk_ids'])}개" if s else ""))
        elif node == "flag_page":
            out.append(f"{i}. 깨진 페이지 기록: " + ", ".join(f"{f} p.{p}" for f, p in d["pages"]))
        elif node == "cite_check":
            out.append(f"{i}. 답변 작성 → 인용 확인: {'통과' if d['ok'] else '인용 오류, 다시 작성'}")
        else:
            out.append(f"{i}. {NODES.get(node, node)}: {d}")
    return out


def run_question(agent, cfg, question: str, scope: str) -> dict:
    start = time.perf_counter()
    result = agent.run(question, scope)
    result["seconds"] = round(time.perf_counter() - start, 1)
    from rag import cost
    result["usd"] = cost.totals(result["steps"]["calls"], cost.load_prices())["usd"]
    return result


def dev_item(qid: str) -> dict:
    from rag.golden import load_golden
    items = {i["qid"]: i for i in load_golden(split="dev")}
    if qid not in items:
        sys.exit(f"dev 골드셋에 없는 문항입니다: {qid} (test 문항은 실행하지 않습니다)")
    return items[qid]


def report(result: dict, item: dict | None = None) -> str:
    lines = ["", "[진행 과정]", *describe(result), "",
             "[지나간 노드] " + " → ".join(NODES.get(n, n).split("<br>")[0] for n in visited_path(result["steps"])),
             "", f"[결과] {STATUS.get(result['status'], result['status'])}", result["answer"], "",
             f"[사용량] LLM {result['n_llm_calls']}회, 검색 {result['n_searches']}회, "
             f"{result['seconds']}초, {result['usd']:.4f} USD"]
    if result["steps"].get("repair_queue"):
        lines.append(f"[다시 추출할 페이지] {result['steps']['repair_queue']}")
    if item:
        cited = {(c["source"], c["page"]) for c in result["citations"]}
        shown = {(u["source"], p) for u in result["context"] for p in u.get("pages", [u["page"]])}
        lines += ["", f"[정답 비교] 기준 답: {item.get('target_answer', '')}"]
        for t in item.get("targets", []):
            key = (t["file"], t["page"])
            lines.append(f"  정답 페이지 {t['file']} p.{t['page']}: 문맥에 {'있음' if key in shown else '없음'}, "
                         f"인용 {'함' if key in cited else '안 함'}")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("question", nargs="?", help="직접 쓴 질문 (없으면 --qid 또는 예시 문항)")
    p.add_argument("--qid", help="dev 골드셋 문항 ID (예: POS001, ADD-HP09)")
    p.add_argument("--scope", choices=["A", "B"], default="B", help="직접 쓴 질문의 검색 범위 (기본 B: 전체)")
    p.add_argument("--mode", choices=sorted(CONFIGS), default="repair", help="repair: 카드 015, t3: 세린님 T3")
    p.add_argument("--graph", action="store_true", help="실행 없이 한글 흐름도만 저장")
    args = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    agent, cfg = load_agent(args.mode)
    if args.graph:
        from langchain_core.runnables.graph_mermaid import draw_mermaid_png
        mermaid = korean_mermaid(agent)
        out = HERE / "out" / f"agent_flow_{args.mode}.png"
        out.parent.mkdir(exist_ok=True)
        draw_mermaid_png(mermaid, output_file_path=str(out))
        print(mermaid, f"\n-> {out}", sep="\n")
        return
    from rag.env import require_api_key
    from rag.golden import scope_of
    require_api_key()
    item = None
    if args.question:
        question, scope = args.question, args.scope
    else:
        item = dev_item(args.qid or EXAMPLE_QID)
        question, scope = item["question"], scope_of(item, cfg)
    print(f"[에이전트] {cfg['name']} ({'카드 015 복구 에이전트' if args.mode == 'repair' else '세린님 T3 에이전트'})")
    print(f"[질문] {question}  (검색 범위 {scope})")
    print(report(run_question(agent, cfg, question, scope), item))


if __name__ == "__main__":
    main()
