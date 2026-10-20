"""End-to-end run -> grade -> evaluate -> report with a fake system, in temp folders (no LLM, no network)."""

import json

import pytest

from rag.config import BASELINE, load_config
from rag.cost import load_prices
from rag.harness import SplitLocked, build_report, evaluate_experiment, grade_experiment, run_experiment
from rag.llm import record_call

PAGE = {"chunk_id": "c1", "source": "a.pdf", "page": 3, "content": "휴면성 증권계좌는 6개월 이상 매매가 없는 계좌"}
OTHER = {"chunk_id": "c2", "source": "b.pdf", "page": 1, "content": "관련 없는 내용"}
GOLDEN = [
    {"qid": "POS001", "set": "base_positive", "split": "dev", "question": "휴면성 증권계좌는?", "answerable": True,
     "expected_behavior": "answer_with_citation", "targets": [{"file": "a.pdf", "page": 3}],
     "evidence": ["휴면성 증권계좌는 6개월 이상 매매가 없는 계좌"]},
    {"qid": "NEG001", "set": "base_negative", "split": "dev", "question": "오늘 최고금리는?", "answerable": False,
     "expected_behavior": "abstain_and_redirect", "targets": [], "evidence": []},
    {"qid": "POS002", "set": "base_positive", "split": "test", "question": "test question", "answerable": True,
     "expected_behavior": "answer_with_citation", "targets": [{"file": "a.pdf", "page": 3}], "evidence": []},
]


class FakeSystem:
    def retrieve(self, question, scope, steps=None):
        return [PAGE, OTHER] if "휴면" in question else [OTHER]

    def run(self, question, scope):
        steps = {}
        record_call(steps, node="generate", model="gemini-3.8-flash", input_tokens=1000, output_tokens=200)
        context = self.retrieve(question, scope)
        if "휴면" in question:
            return {"status": "answered", "answer": "6개월 [1]", "context": context, "steps": steps, "n_searches": 1,
                    "citations": [{"chunk_id": "c1", "source": "a.pdf", "page": 3}]}
        return {"status": "abstained", "answer": "자료 없음", "context": context, "steps": steps, "n_searches": 1,
                "citations": []}


def fake_grade(item, run, cfg):
    calls = []
    record_call({"calls": calls}, node="judge", model="gemini-3.6-flash", input_tokens=500, output_tokens=50)
    return {"correctness": 2 if run["status"] == "answered" else 1, "reason": "fake", "calls": calls}


@pytest.fixture
def dirs(tmp_path):
    golden = tmp_path / "golden"
    golden.mkdir()
    (golden / "provided.jsonl").write_text("".join(json.dumps(g, ensure_ascii=False) + "\n" for g in GOLDEN),
                                           encoding="utf-8")
    return {"db": tmp_path / "runs.db", "golden_dir": golden, "grades_dir": tmp_path / "grades",
            "results_dir": tmp_path / "results"}


def test_full_loop(dirs):
    cfg = load_config(BASELINE)
    exp = "dev_000_baseline"
    r = run_experiment(cfg, "dev", experiment=exp, system=FakeSystem(), db=dirs["db"], golden_dir=dirs["golden_dir"])
    assert r["ran"] == 2 and r["statuses"] == {"answered": 1, "abstained": 1}
    again = run_experiment(cfg, "dev", experiment=exp, system=FakeSystem(), db=dirs["db"], golden_dir=dirs["golden_dir"])
    assert again["ran"] == 0 and again["skipped_done"] == 2            # resume skips finished questions

    g = grade_experiment(exp, grade_fn=fake_grade, db=dirs["db"], golden_dir=dirs["golden_dir"],
                         grades_dir=dirs["grades_dir"])
    assert g["graded_now"] == 2

    s = evaluate_experiment(exp, with_runs=True, db=dirs["db"], golden_dir=dirs["golden_dir"],
                            grades_dir=dirs["grades_dir"], results_dir=dirs["results_dir"], prices=load_prices())
    assert s["scores"]["status_ok"] == 1.0
    assert s["scores"]["correctness_mean"] == pytest.approx((1.0 + 0.5) / 2)
    assert s["retrieval"]["page_hit@5"] == 1 and s["retrieval"]["evid@5"] == 1.0
    assert s["scores"]["citation_on_target"] == 1.0
    assert s["cost"]["usd"] == pytest.approx(2 * (1000 * 0.75 + 200 * 3.75) / 1e6)
    assert s["cost"]["judge_usd"] > 0 and s["calls"]["llm_per_question"] == 1
    out = dirs["results_dir"] / exp
    assert {p.name for p in out.iterdir()} == {"summary.json", "metrics.jsonl", "grades.jsonl", "runs.jsonl"}
    with pytest.raises(FileExistsError):                                 # results are not overwritten silently
        evaluate_experiment(exp, db=dirs["db"], golden_dir=dirs["golden_dir"], grades_dir=dirs["grades_dir"],
                            results_dir=dirs["results_dir"])

    ret = "dev_000_baseline_retrieval"
    run_experiment(cfg, "dev", experiment=ret, retrieval_only=True, system=FakeSystem(), db=dirs["db"],
                   golden_dir=dirs["golden_dir"])
    sr = evaluate_experiment(ret, db=dirs["db"], golden_dir=dirs["golden_dir"], grades_dir=dirs["grades_dir"],
                             results_dir=dirs["results_dir"])
    assert sr["n_graded"] == 0 and sr["calls"]["llm"] == 0 and sr["retrieval"]["gold@5"] == 1

    rep = build_report(results_dir=dirs["results_dir"], html_path=dirs["results_dir"] / "report.html")
    assert rep["experiments"] == 2
    md = (dirs["results_dir"] / "SUMMARY.md").read_text(encoding="utf-8")
    assert "dev_000_baseline_retrieval" in md and "<table" in (dirs["results_dir"] / "report.html").read_text(encoding="utf-8")


def test_test_split_is_locked(dirs):
    cfg = load_config(BASELINE)
    with pytest.raises(SplitLocked):
        run_experiment(cfg, "test", experiment="test_000_baseline", system=FakeSystem(), db=dirs["db"],
                       golden_dir=dirs["golden_dir"])
    with pytest.raises(SplitLocked):
        build_report(results_dir=dirs["results_dir"], include_test=True)
    r = run_experiment(cfg, "test", experiment="test_000_baseline", final=True, system=FakeSystem(), db=dirs["db"],
                       golden_dir=dirs["golden_dir"])
    assert r["ran"] == 1
