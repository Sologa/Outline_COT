# Runbook

This scaffold is for the next execution thread. It intentionally contains no
command that runs the full 50-paper extraction.

## Start Here

1. Confirm the selected Tree50 manifest exists:

```bash
test -f results/engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/_summaries/selected_tree50_manifest.jsonl
```

2. Confirm the current no-heading/no-table Tree50 validation:

```bash
cat results/engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/_summaries/validation_report.json
cat results/engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/_summaries/high261_post_validation.json
```

3. Read the semantic-correction contract:

```bash
sed -n '1,220p' engineering_validation/2026-05-23_taxonomy_extraction_semantic_correction/prompts/semantic_correction_prompt_template.md
sed -n '1,260p' engineering_validation/2026-05-23_taxonomy_extraction_semantic_correction/prototype/run_shared_prompt_clean_codex_correction.py
```

4. Read this lane's spec:

```bash
sed -n '1,260p' engineering_validation/2026-05-24_hf_meow_tree50_source_extraction_v2/spec.md
```

## Recommended Execution Shape

1. Build a per-paper extraction input bundle from:
   - selected Tree50 manifest;
   - source-confirmation bundle;
   - final source confirmation;
   - PDF/TeX source paths from `data/paper_sets/hf_meow_raw_taxonomy_high261/`.
2. Dispatch first-pass source extraction in batches of 10.
3. Validate JSON syntax, schema, evidence ID resolution, and no-heading/no-table
   evidence usage.
4. Dispatch second review for every successful or ambiguous extraction.
5. Merge final extraction only when first pass and second review agree.
6. Render v2 tree-only payload using the same renderer semantics as
   `run_shared_prompt_clean_codex_correction.py`.
7. Apply the 2026-05-23 semantic-correction contract to the new extraction
   artifact, but write outputs under this lane's result root.

## Do Not Do

- Do not use MEOW outline as taxonomy evidence.
- Do not use paper headings as taxonomy evidence.
- Do not use tables, table captions, table cells, or table-only classifications
  as taxonomy-tree evidence.
- Do not overwrite the 2026-05-23 semantic-correction outputs.
- Do not overwrite the 2026-05-24 Tree50 selection outputs.
- Do not create or update a Google Sheet.
- Do not run downstream outline generation from this lane until the user
  approves promotion.

## Suggested Smoke First

Before running all 50 papers, run a 2-paper smoke:

- one selected paper whose source evidence is mostly figure/prose;
- one selected paper with many pruned heading/table locators.

The smoke is acceptable only if both outputs include:

- `taxonomy_extraction.json`;
- evidence-resolved nodes and edges;
- no heading/table evidence in selected nodes or edges;
- second-review result;
- v2 tree-only payload;
- semantic-correction layer.
