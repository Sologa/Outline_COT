# Runbook

This experiment is a paper-096 smoke test for payload completeness, not a full taxonomy22 rerun.

## Render And Validate

```bash
python3 experiments/2026-05-23_taxonomy_payload_completeness_smoke/prototype/run_payload_completeness_smoke.py \
  --render-only \
  --write-batch-input
```

Default output:

```text
results/experiments/2026-05-23_taxonomy_payload_completeness_smoke/
  2026-05-23_paper096_smoke/
    096_2502.03108/
      no_abstract/
        tree_only_guarded/
        structural_complete_guarded/
    _batch/batch_input.jsonl
    _summaries/
```

## Optional: Include Abstract

Use this only if the first smoke run suggests the payload comparison is worth extending.

```bash
python3 experiments/2026-05-23_taxonomy_payload_completeness_smoke/prototype/run_payload_completeness_smoke.py \
  --render-only \
  --write-batch-input \
  --input-condition no_abstract \
  --input-condition with_abstract
```

## Optional: Submit Later

The runner writes a local Batch API JSONL input but does not upload or submit it. This is intentional for the first smoke pass so prompt contents and leakage checks can be inspected before spending model calls.

## Direct 096 Smoke Generation

Use this only after inspecting the rendered payloads. It runs exactly the configured paper-096 comparison arms through the Responses API and writes normalized outlines.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-05-23_taxonomy_payload_completeness_smoke/prototype/run_payload_completeness_smoke.py \
  --direct-run \
  --write-batch-input
```

## V2 Corrected Artifact Smoke

Use this path after the semantic-correction lane has produced:

```text
results/engineering_validation/2026-05-23_taxonomy_extraction_semantic_correction/096_2502.03108/taxonomy_extraction.corrected.json
```

Render-only:

```bash
TAXONOMY_PAYLOAD_SMOKE_RUN_ID=2026-05-23_paper096_v2_corrected_smoke \
TAXONOMY_PAYLOAD_SMOKE_TAXONOMY_PATH=results/engineering_validation/2026-05-23_taxonomy_extraction_semantic_correction/096_2502.03108/taxonomy_extraction.corrected.json \
TAXONOMY_PAYLOAD_SMOKE_TAXONOMY_SOURCE_LABEL=v2_semantic_corrected_2026-05-23 \
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-05-23_taxonomy_payload_completeness_smoke/prototype/run_payload_completeness_smoke.py \
  --render-only \
  --write-batch-input
```

Direct generation:

```bash
TAXONOMY_PAYLOAD_SMOKE_RUN_ID=2026-05-23_paper096_v2_corrected_smoke \
TAXONOMY_PAYLOAD_SMOKE_TAXONOMY_PATH=results/engineering_validation/2026-05-23_taxonomy_extraction_semantic_correction/096_2502.03108/taxonomy_extraction.corrected.json \
TAXONOMY_PAYLOAD_SMOKE_TAXONOMY_SOURCE_LABEL=v2_semantic_corrected_2026-05-23 \
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-05-23_taxonomy_payload_completeness_smoke/prototype/run_payload_completeness_smoke.py \
  --direct-run \
  --write-batch-input \
  --force
```

Dry-run structural evaluation:

```bash
TAXONOMY_PAYLOAD_SMOKE_RUN_ID=2026-05-23_paper096_v2_corrected_smoke \
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-05-23_taxonomy_payload_completeness_smoke/prototype/evaluate_payload_completeness_smoke.py \
  --dry-run
```

## Verification Checks

```bash
python3 -m py_compile experiments/2026-05-23_taxonomy_payload_completeness_smoke/prototype/run_payload_completeness_smoke.py
python3 -m py_compile experiments/2026-05-23_taxonomy_payload_completeness_smoke/prototype/evaluate_payload_completeness_smoke.py

python3 experiments/2026-05-23_taxonomy_payload_completeness_smoke/prototype/run_payload_completeness_smoke.py \
  --render-only \
  --write-batch-input

rg -n "evidence_ledger|evidence_ids|classified_items|assigned_node_ids|audit|visual_table_review|source_pack|rejected_candidates|/Users/" \
  results/experiments/2026-05-23_taxonomy_payload_completeness_smoke/2026-05-23_paper096_smoke/096_2502.03108/no_abstract/*/taxonomy_payload.txt
```

The final `rg` should return no matches.

## Structural-Distance Evaluation

```bash
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-05-23_taxonomy_payload_completeness_smoke/prototype/evaluate_payload_completeness_smoke.py \
  --dry-run
```
