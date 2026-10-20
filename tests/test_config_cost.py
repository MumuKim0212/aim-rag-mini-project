import pytest

from rag.config import BASELINE, experiment_name, load_config
from rag.cost import PRICING, call_usd, load_prices, totals
from rag.llm import record_call


def write(path, text):
    path.write_text(text, encoding="utf-8")
    return path


def test_baseline_has_no_changes():
    cfg = load_config(BASELINE)
    assert cfg["changed"] == {}
    assert experiment_name(cfg, "dev") == "dev_000_baseline"
    assert experiment_name(cfg, "dev", retrieval_only=True) == "dev_000_baseline_retrieval"


def test_variant_records_only_its_change(tmp_path):
    base = write(tmp_path / "baseline.yaml", (BASELINE.read_text(encoding="utf-8")))
    v1 = write(tmp_path / "001-chunk400.yaml", "base: baseline.yaml\nname: 001_chunk400\nchunking: {chunk_size: 400}\n")
    v2 = write(tmp_path / "004-hybrid.yaml", "base: 001-chunk400.yaml\nname: 004_hybrid\nretrieval: {method: hybrid}\n")
    cfg1, cfg2 = load_config(v1, baseline=base), load_config(v2, baseline=base)
    assert cfg1["changed"] == {"chunking.chunk_size": {"from": 800, "to": 400}}
    assert set(cfg2["changed"]) == {"chunking.chunk_size", "retrieval.method"}
    assert cfg2["chunking"]["chunk_overlap"] == 100          # untouched keys inherited
    assert cfg1["config_hash"] != cfg2["config_hash"]
    assert load_config(v1, baseline=base)["config_hash"] == cfg1["config_hash"]


def test_every_configured_model_has_a_price():
    prices, cfg = load_prices(PRICING), load_config(BASELINE)
    for model in (cfg["answer"]["model"], cfg["judge"]["model"], cfg["embedding"]["model"],
                  "gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-embedding-001"):
        assert model in prices


def test_cost_totals():
    prices = {"m": {"input": 1.0, "output": 4.0}, "e": {"input": 0.2}}
    steps = {}
    record_call(steps, node="generate", model="m", input_tokens=1_000_000, output_tokens=500_000, thinking_tokens=200_000)
    record_call(steps, node="embed", model="e", kind="embedding", input_tokens=1_000_000)
    t = totals(steps["calls"], prices)
    assert t["usd"] == pytest.approx(1.0 + 2.0 + 0.2)
    assert (t["llm_calls"], t["embedding_calls"], t["thinking_tokens"]) == (1, 1, 200_000)
    with pytest.raises(KeyError):
        call_usd({"model": "unknown"}, prices)
