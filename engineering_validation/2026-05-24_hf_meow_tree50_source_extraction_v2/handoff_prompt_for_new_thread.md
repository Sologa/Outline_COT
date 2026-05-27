# Handoff Prompt For New Thread

Please continue in `/Users/xjp/Desktop/Outline_COT`.

Goal: implement and run the new engineering-validation lane:

`engineering_validation/2026-05-24_hf_meow_tree50_source_extraction_v2/`

Task summary:

We already selected 50 strict source-confirmed HF MEOW raw papers in:

`results/engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/`

The selected manifest is:

`results/engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/_summaries/selected_tree50_manifest.jsonl`

The current Tree50 gate is strict:

- selected papers must be explicit author/source taxonomy trees;
- do not use MEOW outline, COT, metadata, title, abstract, section headings,
  table environments, table captions, table cells, OCR-only text, or filenames
  as taxonomy-tree evidence;
- table-only classification schemes do not count;
- node and edge evidence IDs must resolve to source locators.

Important distinction:

`engineering_validation/2026-05-23_taxonomy_extraction_semantic_correction/`
has reusable semantic-correction and v2 payload-rendering logic, but it is not
a source extraction pipeline. It assumes `taxonomy_extraction.json` already
exists. For these 50 papers, first produce source-grounded
`taxonomy_extraction.json`; then apply the 2026-05-23 semantic-correction
contract and v2 tree-only payload renderer.

Do not write new outputs into the 2026-05-23 semantic-correction lane or the
2026-05-24 Tree50 selection lane. Use:

`results/engineering_validation/2026-05-24_hf_meow_tree50_source_extraction_v2/`

Use `.local/engineering_validation/2026-05-24_hf_meow_tree50_source_extraction_v2/`
for scratch.

Before implementing, read:

1. `engineering_validation/2026-05-24_hf_meow_tree50_source_extraction_v2/spec.md`
2. `engineering_validation/2026-05-24_hf_meow_tree50_source_extraction_v2/runbook.md`
3. `engineering_validation/2026-05-24_hf_meow_tree50_source_extraction_v2/prompts/source_extraction_prompt_template.md`
4. `engineering_validation/2026-05-24_hf_meow_tree50_source_extraction_v2/prompts/source_extraction_output_schema.json`
5. `engineering_validation/2026-05-23_taxonomy_extraction_semantic_correction/prototype/run_shared_prompt_clean_codex_correction.py`
6. `engineering_validation/2026-05-23_taxonomy_extraction_semantic_correction/prompts/semantic_correction_prompt_template.md`
7. `results/engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/_summaries/audit_summary.md`
8. `results/engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/_summaries/validation_report.json`
9. `results/engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/_summaries/high261_post_validation.json`

Execution expectation:

- first create/review implementation scripts and run a 2-paper smoke;
- only after smoke validation should the full 50-paper extraction be run;
- use subagents or clean workers for paper reading;
- every final success needs second review;
- preserve an auditable failure ledger instead of weakening the standard.
