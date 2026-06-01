# Manifests

Status: `schema_only_no_data_conversion`

Future files:

- `input_manifest.jsonl`
- `source_provenance.json`
- `readiness_report.json`

`input_manifest.jsonl` should be the adapter's durable list of selected
TaxoBench-CS target papers. Each row should point to normalized local inputs
under `data/taxobench-cs/`, not to prompt-visible local source paths.
