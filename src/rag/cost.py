"""USD and token totals from recorded calls, using configs/pricing.yaml.

A call (see llm.record_call) is {"node", "kind", "model", "input_tokens", "output_tokens",
"thinking_tokens", "seconds"}; `output_tokens` includes thinking tokens, which are billed as output.
"""

from pathlib import Path

import yaml

from . import ROOT

PRICING = ROOT / "configs" / "pricing.yaml"


def load_prices(path: Path = PRICING) -> dict:
    with Path(path).open(encoding="utf-8") as f:
        return yaml.safe_load(f)["models"]


def call_usd(call: dict, prices: dict) -> float:
    model = call["model"]
    if model not in prices:
        raise KeyError(f"no price for {model!r}: add it to configs/pricing.yaml")
    p = prices[model]
    return (call.get("input_tokens", 0) * p["input"] + call.get("output_tokens", 0) * p.get("output", 0)) / 1e6


def calls_of(steps) -> list[dict]:
    """Recorded calls in a run's `steps` ({"calls": [...], ...}); empty when nothing was recorded."""
    return list((steps or {}).get("calls", [])) if isinstance(steps, dict) else []


def totals(calls: list[dict], prices: dict) -> dict:
    out = {"usd": 0.0, "usd_by_model": {}, "input_tokens": 0, "output_tokens": 0, "thinking_tokens": 0,
           "llm_calls": 0, "embedding_calls": 0}
    for call in calls:
        usd = call_usd(call, prices)
        out["usd"] += usd
        out["usd_by_model"][call["model"]] = out["usd_by_model"].get(call["model"], 0.0) + usd
        for field in ("input_tokens", "output_tokens", "thinking_tokens"):
            out[field] += call.get(field, 0) or 0
        out["embedding_calls" if call.get("kind") == "embedding" else "llm_calls"] += 1
    return out
