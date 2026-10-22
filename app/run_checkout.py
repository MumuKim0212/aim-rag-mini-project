"""Run one question through a system in another checkout of this repo (a teammate's branch), with that
checkout's own code, prompts, and index. Used by the live page for versions whose code is not on this branch.

    python app/run_checkout.py <checkout dir> <config> <scope> < question.txt   # prints the result dict as JSON

The checkout must have its index built (scripts/build_index.py there) and an .env with the API key.
"""

import json
import os
import sys
from pathlib import Path

checkout, config, scope = Path(sys.argv[1]).resolve(), sys.argv[2], sys.argv[3]
os.chdir(checkout)
sys.path.insert(0, str(checkout / "src"))

from rag import env  # noqa: E402

env.setup()  # tracing off before any call
from rag.config import load_config  # noqa: E402
from rag.systems import build_system  # noqa: E402

result = build_system(load_config(checkout / config)).run(sys.stdin.read().strip(), scope)
print(json.dumps(result, ensure_ascii=False))
