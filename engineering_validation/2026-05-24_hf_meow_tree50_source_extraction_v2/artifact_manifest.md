# Artifact Manifest

This file describes intended artifacts. It is not a run log.

## Repo-Tracked Scaffold

- `README.md`: lane purpose and boundaries.
- `spec.md`: task contract and exit criteria.
- `config.yaml`: stable path and policy settings.
- `runbook.md`: execution guidance for the next thread.
- `implementation_plan.md`: phase plan.
- `validation_plan.md`: validation checklist.
- `promotion_checklist.md`: downstream-use checklist.
- `handoff_prompt_for_new_thread.md`: copy-ready new-thread prompt.
- `prompts/source_extraction_prompt_template.md`: extraction worker prompt.
- `prompts/source_extraction_output_schema.json`: expected extraction output
  schema.
- `prompts/README.md`: prompt notes.
- `prototype/README.md`: placeholder for future scripts.

## Runtime Outputs

Runtime outputs must be written under:

- `results/engineering_validation/2026-05-24_hf_meow_tree50_source_extraction_v2/`

Large scratch must be written under:

- `.local/engineering_validation/2026-05-24_hf_meow_tree50_source_extraction_v2/`
