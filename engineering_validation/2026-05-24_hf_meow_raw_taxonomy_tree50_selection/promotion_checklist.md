# Promotion Checklist

Before using Tree50 in downstream outline generation:

- [ ] Raw split fingerprint matches the pinned SHA256.
- [ ] Candidate inventory was regenerated from the pinned raw split.
- [ ] Source assets for selected papers are cached under `.local/`, not this folder.
- [ ] Every selected paper has strict source-confirmed taxonomy tree evidence.
- [ ] Every selected paper has second-review status `pass` or `pass_with_notes`.
- [ ] `selected_tree50_manifest.jsonl` has exactly 50 unique IDs.
- [ ] `validation_report.json` has `selection_ready: true`.
- [ ] `exclusion_ledger.jsonl` records all non-counted candidates.
- [ ] No outline/COT/metadata/section-heading/table evidence was counted.
- [ ] Downstream experiments use a new experiment id and do not overwrite taxonomy22.
