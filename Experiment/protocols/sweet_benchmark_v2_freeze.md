# SweetSeek Benchmark v2 Freeze Record

- Freeze date: 2026-10-22
- Domain: sweetness only
- Review method: single-researcher human review
- Questions: 20 approved
- Answerable questions: 16
- Unanswerable/refusal questions: 4
- Evidence rows: 25 verified
- Difficulty distribution: 7 easy, 5 medium, 8 hard
- Type distribution: 4 fact, 4 comparison, 4 mechanism, 4 summary/application, 4 unanswerable

## Frozen Files

- Benchmark: `Experiment/benchmark/sweet_benchmark_v2.json`
- Benchmark SHA-256: `56296f160c3e6fc5b4120db553a0c4695b655d97029b10984120a9ddedd1857c`
- Review workbook: `Experiment/annotations/SweetSeek_首批20题审核表.xlsx`
- Review workbook SHA-256: `82fcb4121af6c93b4d913e0fe00e2dbe6e99e6f455a4605f3498641592946573`
- Machine-readable manifest: `Experiment/benchmark/sweet_benchmark_v2.freeze.json`

## Leakage Control

The frozen questions must not be used to tune prompts, retrieval parameters,
reranking, model weights, refusal rules, or answer-generation behavior before
the registered evaluation. Author names and publication years are excluded
from question text and retained only in hidden gold evidence metadata.

Any content change requires a new benchmark version and a new freeze manifest.
