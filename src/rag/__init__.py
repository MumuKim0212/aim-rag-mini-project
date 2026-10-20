"""Financial-document RAG agent: shared pipeline code.

Implemented here (shared infrastructure, do not fork per experiment):
- config   : load baseline + variant configs, record what changed
- env      : load .env, force tracing off
- golden   : load golden items, index scope per set, expected status per behavior
- cost     : USD and token totals from recorded calls (configs/pricing.yaml)
- llm      : record_call / usage_from_message — every LLM and embedding call goes through record_call
- repro    : git commit, dirty flag, package versions for every run
- harness  : batch run / grade / evaluate / report used by scripts/

To implement (stubs raise NotImplementedError; keep the signatures):
- ingest, chunking, retrieval, rag, agent, judge

Data contracts are in each module's docstring and in evalkit/README.md.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
