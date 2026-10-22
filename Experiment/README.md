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
2. Use `candidate` until independent domain review is complete.
3. Freeze the 200-question benchmark before tuning prompts or retrieval settings.
4. Never overwrite a frozen benchmark or completed run. Create a new version instead.
5. Record the model version, parameters, knowledge-base fingerprint, code commit, and run date for every run.
6. Keep dual-protein, encapsulation, protein-polysaccharide, docking, and molecular-dynamics data out of this directory.

The active draft benchmark is `benchmark/sweet_benchmark_v2.json`.
