"""Draw the agent's node structure from the compiled LangGraph graph (no API calls).

    python scripts/show_graph.py                              # configs/015-context-repair.yaml
    python scripts/show_graph.py --config configs/015-context-repair.yaml

Prints the mermaid text and writes out/agent_graph_<name>.mmd and
out/agent_graph_<name>.html (open in a browser; renders the mermaid with mermaid.js).
"""

import argparse
import html

import _paths  # noqa: F401
from rag import ROOT
from rag.systems import build_system
from rag.config import load_config

HTML = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>Agent graph</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{{font-family:sans-serif;margin:24px;background:#fff;color:#111}}</style></head>
<body><h1>Agent graph ({name})</h1><pre class="mermaid">
{mermaid}
</pre>
<script type="module">
import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.esm.min.mjs";
mermaid.initialize({{startOnLoad: true}});
</script></body></html>
"""


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", default="configs/015-context-repair.yaml")
    args = p.parse_args()
    cfg = load_config(args.config)
    mermaid = build_system(cfg).graph.get_graph().draw_mermaid()
    print(mermaid)
    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    (out / f"agent_graph_{cfg['name']}.mmd").write_text(mermaid, encoding="utf-8")
    (out / f"agent_graph_{cfg['name']}.html").write_text(HTML.format(name=cfg["name"], mermaid=html.escape(mermaid)), encoding="utf-8")
    print(f"-> {out}/agent_graph_{cfg['name']}.html")


if __name__ == "__main__":
    main()
