"""Make `rag` (src/) and `evalkit` (repo root) importable when a script is run as `python scripts/<name>.py`."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
