"""What produced a result: git commit, uncommitted changes, Python and package versions.
Stored in every run's config and in summary.json, so numbers can be traced to code."""

import platform
import re
import subprocess
from importlib import metadata

from . import ROOT


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def git_info() -> dict:
    status = _git("status", "--porcelain", "--", "src", "scripts", "configs", "prompts", "evalkit", "golden")
    return {"commit": _git("rev-parse", "--short", "HEAD"), "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty": None if status is None else bool(status)}


def requirement_names() -> list[str]:
    names = []
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            names.append(re.split(r"[=<>!~\[ ]", line, maxsplit=1)[0])
    return names


def package_versions() -> dict:
    versions = {}
    for name in requirement_names():
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def environment() -> dict:
    return {"python": platform.python_version(), "git": git_info(), "packages": package_versions()}
