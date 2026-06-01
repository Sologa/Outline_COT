# TaxoBench-CS Scripts

Status: `placeholder_no_adapter_code_yet`

This folder is reserved for dataset-specific TaxoBench-CS normalization and
payload-rendering scripts.

Planned scripts:

- `prepare_taxobench_cs_inputs.py`
- `generate_taxobench_cs_payloads.py`
- `validate_taxobench_cs_staging.py`

These scripts should read `/Users/xjp/Desktop/TaxoBench-CS` as read-only and
write deterministic staged inputs under `data/taxobench-cs/`.

They must not submit model jobs, write experiment outputs, or mutate the
upstream TaxoBench-CS workspace.
