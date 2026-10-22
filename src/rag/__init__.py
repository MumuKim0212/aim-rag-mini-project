"""Financial-document RAG agent: shared pipeline code.

Implemented here (shared infrastructure, do not fork per experiment):
- config   : load baseline + variant configs, record what changed
- env      : load .env, force tracing off
- golden   : load golden items, index scope per set, expected status per behavior
- cost     : USD and token totals from recorded calls (configs/pricing.yaml)
- llm      : Gemini calls (generate_json, embed, count_tokens) and record_call — every call is recorded
- repro    : git commit, dirty flag, package versions for every run
- harness  : batch run / grade / evaluate / report used by scripts/

Baseline pipeline (implemented, tested; frozen: dev_000_baseline ran 2026-10-21):
- ingest     : PDF -> pages (PyMuPDF text layer + VLM supplement for scope-B pages, configs/extraction.yaml)
- prompts    : prompt-file loading shared by rag and ingest
- chunking   : "recursive", "structure" (card 002: glossary term, terms article; rest recursive)
- retrieval  : index build, "vector" search (Chroma, gemini-embedding-2 with its text prefixes)
- rag        : BaselineRAG and the shared answer step (generate_answer, map_citations, format_answer)
- judge      : grade() with prompts/judge_v1.md (frozen 2026-10-21), status_ok, citation_check

Added by the experiments (implemented, tested):
- retrieval "bm25" (Kiwi) / "hybrid" (card 004), rerank: LLM rerank of a larger pool (card 013)
- agent : LangGraph agent (card 008; v2 options memo / check, card 014)

Not built (stubs raise NotImplementedError; no experiment used them):
- chunking add_header (003), retrieval mmr (005)

Data contracts are in each module's docstring and in evalkit/README.md.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
