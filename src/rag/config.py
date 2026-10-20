"""Experiment configs: configs/baseline.yaml plus variants that override only what they change.

    cfg = load_config("configs/004-hybrid.yaml")
    cfg["changed"]      # {"retrieval.method": {"from": "vector", "to": "hybrid"}}
    cfg["config_hash"]  # hash of the merged settings (meta keys excluded)

A variant names its parent with `base:` (relative to the variant's folder); chains are merged top-down.
See configs/README.md.
"""

import copy
import hashlib
import json
from pathlib import Path

import yaml

from . import ROOT

CONFIG_DIR = ROOT / "configs"
BASELINE = CONFIG_DIR / "baseline.yaml"
META_KEYS = ("base", "name", "card", "description", "compare_to", "changed", "config_hash", "config_file")


def _read(path: Path) -> dict:
    with Path(path).open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def _resolve(path: Path, seen: frozenset = frozenset()) -> dict:
    path = Path(path).resolve()
    if path in seen:
        raise ValueError(f"config inheritance loop at {path}")
    raw = _read(path)
    parent = raw.get("base")
    merged = deep_merge(_resolve(path.parent / parent, seen | {path}), raw) if parent else raw
    merged.pop("base", None)
    return merged


def settings(cfg: dict) -> dict:
    """The config without meta keys: what actually determines a run."""
    return {k: v for k, v in cfg.items() if k not in META_KEYS}


def flatten(d: dict, prefix: str = "") -> dict:
    out = {}
    for key, value in d.items():
        dotted = f"{prefix}{key}"
        if isinstance(value, dict) and value:
            out.update(flatten(value, dotted + "."))
        else:
            out[dotted] = value
    return out


def changed_keys(cfg: dict, baseline: dict) -> dict:
    a, b = flatten(settings(baseline)), flatten(settings(cfg))
    return {k: {"from": a.get(k), "to": b.get(k)} for k in sorted(a.keys() | b.keys()) if a.get(k) != b.get(k)}


def config_hash(cfg: dict) -> str:
    blob = json.dumps(settings(cfg), sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:10]


def load_config(path, baseline: Path = BASELINE) -> dict:
    path = Path(path)
    cfg = _resolve(path)
    cfg.setdefault("name", path.stem)
    cfg["changed"] = changed_keys(cfg, _resolve(baseline))
    cfg["config_hash"] = config_hash(cfg)
    try:
        cfg["config_file"] = path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        cfg["config_file"] = str(path)
    return cfg


def experiment_name(cfg: dict, split: str, retrieval_only: bool = False) -> str:
    """<split>_<config name>; retrieval-only runs (LLM-free comparisons) get a `_retrieval` suffix."""
    return f"{split}_{cfg['name']}" + ("_retrieval" if retrieval_only else "")
