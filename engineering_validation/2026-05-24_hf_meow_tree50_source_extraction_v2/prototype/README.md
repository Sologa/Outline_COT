# Prototype

No execution scripts have been added yet.

Future scripts should be scoped to this lane and should not write into:

- `results/engineering_validation/2026-05-23_taxonomy_extraction_semantic_correction/`
- `results/engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/`

Recommended script names:

- `build_tree50_source_extraction_bundles.py`
- `run_tree50_source_extraction_workers.py`
- `merge_tree50_source_extractions.py`
- `apply_semantic_correction_bridge.py`
- `validate_tree50_source_extraction_v2.py`
