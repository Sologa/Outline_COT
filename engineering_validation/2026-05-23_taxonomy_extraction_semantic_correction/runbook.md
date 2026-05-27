# Runbook

This runbook is for the next conversation. It intentionally contains no command that performs correction.

## Start Here

1. Read the snapshot:

```bash
sed -n '1,220p' results/engineering_validation/2026-05-23_taxonomy_extraction_snapshot/snapshot_summary.md
```

2. Verify the snapshot:

```bash
cd results/engineering_validation/2026-05-23_taxonomy_extraction_snapshot
shasum -a 256 -c sha256.txt
```

3. Read this validation spec:

```bash
sed -n '1,260p' engineering_validation/2026-05-23_taxonomy_extraction_semantic_correction/spec.md
```

4. Read ChatGPT's TaxoAdapt-style audit report:

```bash
sed -n '1,220p' results/engineering_validation/2026-05-23_taxonomy_extraction_snapshot/external_context/taxoadapt_style_multifaceted_taxonomy_audit_meow_samples_zh_TW.md
```

5. Read TaxoAdapt's own definition:

```bash
sed -n '1,180p' /Users/xjp/Desktop/Taxonomy/external/paper_repos/taxoadapt/README.md
pdftotext /Users/xjp/Desktop/Taxonomy/docs/papers/pdf/TaxoAdapt_Aligning_LLM_Based_Multidimensional_Taxonomy_Construction.pdf - | rg -n -i 'multidimensional|multi-faceted|dimension|hierarchical classification|width|depth|density|paper'
```

## Suggested Planning Commands

Inventory current extraction files:

```bash
find results/experiments/2026-05-19_meow_taxonomy_extraction -name taxonomy_extraction.json | sort
```

Summarize current top-level statuses:

```bash
for f in $(find results/experiments/2026-05-19_meow_taxonomy_extraction -name taxonomy_extraction.json | sort); do
  jq -r '[.paper_id, .taxonomy_status, .taxonomy_kind, (.taxonomies|length), ((.taxonomies[]?.nodes // [])|length)] | @tsv' "$f"
done
```

Inspect high-risk sample papers:

```bash
jq '{paper_id,title,taxonomy_status,taxonomy_kind,taxonomies:[.taxonomies[]|{taxonomy_id,name,taxonomy_kind,source_boundary,scope_note,nodes:(.nodes|length),edges:(.edges|length),classified_items:(.classified_items|length)}]}' \
  results/experiments/2026-05-19_meow_taxonomy_extraction/smoke/096_2502.03108/taxonomy_extraction.json
```

## Do Not Run Without Explicit User Approval

- Do not write `taxonomy_extraction.corrected.json`.
- Do not mutate any file under `results/experiments/2026-05-19_meow_taxonomy_extraction/`.
- Do not overwrite files under `results/engineering_validation/2026-05-23_taxonomy_extraction_snapshot/`.
- Do not submit OpenAI Batch or Responses API work.
- Do not rerun taxonomy22.

## Expected Future Commands

The next conversation may create a correction script or manual correction process, but only after proposing the exact write targets. Expected future write targets, if approved:

- `results/engineering_validation/2026-05-23_taxonomy_extraction_semantic_correction/<paper_id>/taxonomy_extraction.corrected.json`
- `results/engineering_validation/2026-05-23_taxonomy_extraction_semantic_correction/<paper_id>/semantic_diff.md`
- `results/engineering_validation/2026-05-23_taxonomy_extraction_semantic_correction/<paper_id>/correction_manifest.json`
- `results/engineering_validation/2026-05-23_taxonomy_extraction_semantic_correction/correction_summary.md`
- `results/engineering_validation/2026-05-23_taxonomy_extraction_semantic_correction/validation_report.json`
