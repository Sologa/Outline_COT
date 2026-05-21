# Outline_COT

This repository is a MEOW outline-analysis workspace. It keeps prompt payloads, paper reference sets, experiment outputs, and human-readable reports separate so evaluations can be traced without mixing source data and generated runs.

## Layout

- `data/paper_sets/`: stable paper-side inputs and reference artifacts.
  - `meow_refs/`: the earlier MEOW reference paper set.
  - `meow_test100/`: the 100-paper MEOW test set package with manifests, PDFs, TeX source, and released outlines.
- `third_party/`: upstream repositories and archives mirrored for provenance.
- `prompts/`: direct LLM prompt payloads.
- `scripts/`: local runners, extractors, and evaluation utilities.
- `tests/`: focused regression tests for scripts.
- `experiments/`: incubating experiment specs, prototype code, prompt variants, and promotion notes.
- `results/`: experiment outputs and run-scoped evaluation artifacts.
- `docs/`: human-readable reports, guides, prompt notes, figures, and audits.
- `graphify-out/`: rebuildable local graphify output.
- `.local/`: ignored scratch space, logs, temporary exports, and local-only intermediates.

The repo-level workflow rules live in `AGENTS.md`.
