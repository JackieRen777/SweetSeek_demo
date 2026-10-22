# SweetSeek Experiments

This directory is the single home for the SweetSeek sweetness-domain study.
Other SweetSeek domains are outside the scope of this experiment.

## Directory layout

- `protocols/`: preregistered methods, inclusion rules, and annotation guidance.
- `benchmark/`: candidate, approved, and frozen benchmark question sets.
- `annotations/`: reviewer worksheets, adjudication records, and agreement results.
- `runs/`: raw outputs from each model and system condition.
- `results/`: cleaned metrics, statistical analyses, and final result tables.
- `figures/`: figures generated from frozen result files.

## Data rules

1. Build and review questions without running the systems being evaluated.
2. Use `candidate` until human domain review is complete. Current review is by one researcher with AI-assisted drafting, not independent multi-expert validation.
3. Tune prompts and retrieval settings only on a separate development set. Freeze the full 200-question benchmark, scoring rules, and system configurations before formal test runs; never tune on test questions or their results.
4. Never overwrite a frozen benchmark or completed run. Create a new version instead.
5. Record the model version, parameters, knowledge-base fingerprint, code commit, and run date for every run.
6. Keep dual-protein, encapsulation, protein-polysaccharide, docking, and molecular-dynamics data out of this directory.

The first 20-question benchmark is frozen in `benchmark/sweet_benchmark_v2.json`.
Its integrity record is `benchmark/sweet_benchmark_v2.freeze.json`. Do not edit
either file in place. Continue future reviewed batches in a new benchmark version.

Authoring and scoring guidance for the remaining 180 candidates is in
`protocols/sweet_benchmark_authoring_scoring_v1.md` (Chinese). It specifies
ABC task requirements, evidence auditing, scoring, and leakage controls.
Its allocation is a working plan, not an empirical validation or completed
preregistration. Frozen batch v2 is unchanged.

## Batch 02 candidates

- Review workbook: `annotations/SweetSeek_第二批20题候选审核表.xlsx`.
- Structured candidate archive: `benchmark/sweet_benchmark_batch02_candidates_v1.json`.
- Status: 20 AI-assisted candidates, human review pending; not part of the frozen benchmark.
- Contents: A 5 / B 8 / C 7, including 4 unanswerable questions; 69 weighted scoring points and 51 evidence rows from 11 papers.
- Review question text, individual scoring criteria, and PDF passages separately. Evidence file pages are one-based PDF page numbers. KB-hit text is unverified and left empty.
- No system runs were performed to select or evaluate these questions. Keep all candidate files out of retrieval indexes and tuning data.
