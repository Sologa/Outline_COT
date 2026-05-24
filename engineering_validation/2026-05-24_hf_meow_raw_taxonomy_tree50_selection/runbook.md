# Runbook

## Setup

Required local tools for full execution:

- `python3`
- `curl`
- `tar`
- `pdftotext`
- `pdftoppm` or `pdftocairo`
- `tesseract` for locator aid only

The existing raw cache can be reused only if its SHA256 matches the pinned
dataset fingerprint.

## Phase 1: Pin Raw Split

```bash
python3 engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/prototype/materialize_hf_meow_raw_split.py \
  --raw-path temp_artifacts/hf_meow_raw_check_2026-05-24/raw.jsonl \
  --force
```

Expected:

- `_inputs/dataset_fingerprint.json`
- `_inputs/hf_raw_split_manifest.jsonl`

## Phase 2: Build Candidate Inventory

```bash
python3 engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/prototype/build_taxonomy_signal_inventory.py \
  --raw-path temp_artifacts/hf_meow_raw_check_2026-05-24/raw.jsonl \
  --force
```

Expected:

- `candidate_inventory/all_candidates.jsonl`
- `candidate_inventory/high_candidates_ranked.jsonl`
- `candidate_inventory/wave1_top120.jsonl`
- `candidate_inventory/keyword_signal_summary.csv`
- `_summaries/selection_pool_status.json`

## Phase 3: Download Source Assets

Dry-run first:

```bash
python3 engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/prototype/download_source_assets.py \
  --candidate-file results/engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/candidate_inventory/wave1_top120.jsonl \
  --limit 5 \
  --dry-run
```

Real wave:

```bash
python3 engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/prototype/download_source_assets.py \
  --candidate-file results/engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/candidate_inventory/wave1_top120.jsonl
```

All PDFs, e-print archives, extracted TeX, and logs are written under `.local/`.
Only small per-paper inventories are mirrored under `results/.../per_paper/`.

## Phase 4: Prepare Source Confirmation Bundles

```bash
python3 engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/prototype/prepare_source_confirmation_bundles.py \
  --candidate-file results/engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/candidate_inventory/wave1_top120.jsonl \
  --force
```

This packages locator windows only. It does not confirm a taxonomy tree.

## Phase 5: Worker Confirmation

```bash
python3 engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/prototype/run_source_confirmation_workers.py \
  --candidate-file results/engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/candidate_inventory/wave1_top120.jsonl \
  --batch-size 10 \
  --force
```

The script prepares review batches. Human or subagent reviews must write
`per_paper/<paper_id>/source_confirmation.json`.

## Phase 6: Select And Validate Tree50

```bash
python3 engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/prototype/select_tree50.py --force
python3 engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/prototype/summarize_tree50_selection.py --force
python3 engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/prototype/validate_tree50_selection.py
```

Use `--allow-insufficient` for in-progress validation before 50 positives exist.

