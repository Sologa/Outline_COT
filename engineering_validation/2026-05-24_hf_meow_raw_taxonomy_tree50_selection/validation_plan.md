# Validation Plan

## Smoke Checks

```bash
python3 -m py_compile engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/prototype/*.py
```

```bash
python3 -m unittest discover -s engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/tests -p 'test_*.py'
```

## Dataset Checks

```bash
python3 engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/prototype/materialize_hf_meow_raw_split.py \
  --raw-path temp_artifacts/hf_meow_raw_check_2026-05-24/raw.jsonl \
  --force
```

Expected:

- SHA256 equals `5938812a35aabe85f8b2a08d0408d70cdab1627ceeb008b93d82e3f76a01eca5`
- rows parsed: `2159`
- unique IDs: `2159`
- parse errors: `0`

## Candidate Inventory Checks

```bash
python3 engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/prototype/build_taxonomy_signal_inventory.py \
  --raw-path temp_artifacts/hf_meow_raw_check_2026-05-24/raw.jsonl \
  --force
```

Expected:

- `all_candidates.jsonl` has 2159 rows.
- `wave1_top120.jsonl` has 120 rows.
- every wave1 row has `taxonomy_signal_bucket == "high"`.

## Final Selection Checks

Before downstream use:

- selected manifest has exactly 50 unique IDs;
- every selected ID has `source_confirmation.json`;
- every selected confirmation is source-confirmed strict tree;
- every selected confirmation has second review status `pass` or
  `pass_with_notes`;
- no selected record uses outline/COT/metadata/section headings as sole
  evidence.

