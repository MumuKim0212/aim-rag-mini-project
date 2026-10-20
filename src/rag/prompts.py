"""Prompt files: a GUIDE comment, then `## <section>` headings (system, user, ...). Placeholders are filled
with str.replace, so braces elsewhere in a prompt (JSON examples) need no escaping."""

import re
from functools import lru_cache

from . import ROOT


@lru_cache(maxsize=None)
def load_prompt(path: str, required: tuple = ("system", "user")) -> dict:
    text = re.sub(r"<!--.*?-->", "", (ROOT / path).read_text(encoding="utf-8"), flags=re.S)
    sections = dict(re.findall(r"^## (\w+)\s*\n(.*?)(?=^## |\Z)", text, flags=re.S | re.M))
    missing = set(required) - sections.keys()
    if missing:
        raise ValueError(f"{path}: missing sections {sorted(missing)}")
    return {k: v.strip() for k, v in sections.items()}


def fill(template: str, **values: str) -> str:
    for key, value in values.items():
        template = template.replace("{" + key + "}", value)
    return template
