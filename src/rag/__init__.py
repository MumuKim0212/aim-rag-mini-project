"""Financial-document RAG agent: shared pipeline code.

Implemented here (shared infrastructure, do not fork per experiment):
- config   : load baseline + variant configs, record what changed
- env      : load .env, force tracing off
- golden   : load golden items, index scope per set, expected status per behavior
- cost     : USD and token totals from recorded calls (configs/pricing.yaml)
- llm      : Gemini calls (generate_json, embed, count_tokens) and record_call — every call is recorded
- repro    : git commit, dirty flag, package versions for every run
- harness  : batch run / grade / evaluate / report used by scripts/

Baseline pipeline (implemented, tested; frozen once the baseline has run):
- ingest     : PDF -> pages (PyMuPDF text layer + VLM supplement for scope-B pages, configs/extraction.yaml)
- prompts    : prompt-file loading shared by rag and ingest
- chunking   : "recursive"
- retrieval  : index build, "vector" search (Chroma, gemini-embedding-2 with its text prefixes)
- rag        : BaselineRAG and the shared answer step (generate_answer, map_citations, format_answer)

To implement (stubs raise NotImplementedError; keep the signatures):
- chunking "structure" (card 002), add_header (003), retrieval "bm25" / "hybrid" (004), mmr (005)
- agent (008), judge.grade (workflow step 1)

Data contracts are in each module's docstring and in evalkit/README.md.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
