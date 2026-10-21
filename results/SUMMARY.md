# 실험 결과 요약

생성: 2026-10-21T13:58:20 · `python scripts/report.py`로 다시 만든다. 괄호는 기준(compare_to) 대비 차이.

| 실험 | 카드 | 변경 | n | 정답 점수 | 완전 정답 | 대응 일치 | 인용 정확 | page_hit@5 | evid@5 | gold@5 | USD/문항 | 토큰/문항 | LLM 호출/문항 | p50 s | p90 s | 비용 USD | 기준 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dev_000_baseline | – | 기준 설정 | 90 | 0.722 | 56.7% | 82.2% | 81.1% | 0.878 | 0.697 | 1.92 | 0.00116 | 2916 | 1.00 | 1.58 | 2.07 | 0.1045 | dev_000_baseline |
| dev_000_baseline_r2 | – | 기준 설정 | 90 | 0.667 (-0.055) | 51.1% (-5.6%) | 80.0% (-2.2%) | 81.1% | 0.878 | 0.697 | 1.92 | 0.00117 (+0.00001) | 2921 (+5) | 1.00 | 1.54 (-0.04) | 1.98 (-0.09) | 0.1056 | dev_000_baseline |
| dev_001_chunk1000_retrieval | experiments/001-chunk-size.md | chunking.chunk_overlap: 100 → 125, chunking.chunk_size: 800 → 1000 | 90 | – | – | – | – | 0.932 (+0.054) | 0.763 (+0.066) | 2.00 (+0.08) | 0.00002 (-0.00115) | 77 (-2839) | 0.00 (-1.00) | 0.47 (-1.11) | 0.52 (-1.54) | 0.0014 | dev_000_baseline |
| dev_001_chunk1200_retrieval | experiments/001-chunk-size.md | chunking.chunk_overlap: 100 → 150, chunking.chunk_size: 800 → 1200 | 90 | – | – | – | – | 0.905 (+0.027) | 0.748 (+0.050) | 1.80 (-0.12) | 0.00002 (-0.00115) | 77 (-2839) | 0.00 (-1.00) | 0.49 (-1.09) | 0.62 (-1.45) | 0.0014 | dev_000_baseline |
| dev_001_chunk300_retrieval | experiments/001-chunk-size.md | chunking.chunk_overlap: 100 → 40, chunking.chunk_size: 800 → 300 | 90 | – | – | – | – | 0.932 (+0.054) | 0.671 (-0.026) | 2.55 (+0.64) | 0.00002 (-0.00115) | 76 (-2840) | 0.00 (-1.00) | 0.48 (-1.10) | 0.54 (-1.53) | 0.0014 | dev_000_baseline |
| dev_001_chunk400_retrieval | experiments/001-chunk-size.md | chunking.chunk_overlap: 100 → 50, chunking.chunk_size: 800 → 400 | 90 | – | – | – | – | 0.905 (+0.027) | 0.675 (-0.022) | 2.49 (+0.57) | 0.00002 (-0.00115) | 77 (-2840) | 0.00 (-1.00) | 0.48 (-1.10) | 0.53 (-1.54) | 0.0014 | dev_000_baseline |
| dev_001_chunk600_retrieval | experiments/001-chunk-size.md | chunking.chunk_overlap: 100 → 75, chunking.chunk_size: 800 → 600 | 90 | – | – | – | – | 0.946 (+0.068) | 0.706 (+0.008) | 2.14 (+0.22) | 0.00002 (-0.00115) | 77 (-2839) | 0.00 (-1.00) | 0.48 (-1.10) | 0.54 (-1.52) | 0.0014 | dev_000_baseline |
| dev_002_structure | experiments/002-structure.md | chunking.method: recursive → structure | 50 | 0.830 (+0.108) | 74.0% (+17.3%) | 86.0% (+3.8%) | 94.1% (+13.0%) | 1.000 (+0.122) | 0.950 (+0.253) | 1.88 (-0.04) | 0.00083 (-0.00033) | 1931 (-986) | 1.00 | 1.64 (+0.06) | 2.23 (+0.17) | 0.0415 | dev_000_baseline |
| dev_002_structure_retrieval | experiments/002-structure.md | chunking.method: recursive → structure | 50 | – | – | – | – | 1.000 (+0.122) | 0.950 (+0.253) | 1.88 (-0.04) | 0.00001 (-0.00115) | 60 (-2856) | 0.00 (-1.00) | 0.48 (-1.10) | 0.54 (-1.53) | 0.0006 | dev_000_baseline |
