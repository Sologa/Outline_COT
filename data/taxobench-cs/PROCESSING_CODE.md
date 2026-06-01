# TaxoBench-CS Processing Code Policy

Status: `policy_only_no_adapter_code_yet`

TaxoBench-CS normalization code should be recorded and versioned with the
dataset staging store, because it materializes reusable input data under
`data/taxobench-cs/`.

## Code Location

Preferred location for dataset-specific adapter code:

```text
data/taxobench-cs/scripts/
```

Planned scripts:

```text
data/taxobench-cs/scripts/prepare_taxobench_cs_inputs.py
data/taxobench-cs/scripts/generate_taxobench_cs_payloads.py
data/taxobench-cs/scripts/validate_taxobench_cs_staging.py
```

Do not put the canonical TaxoBench-CS data adapter only under an experiment
prototype directory. Experiment prototypes should consume staged inputs, not
re-normalize upstream source data.

## Responsibility Split

`data/taxobench-cs/scripts/` should own:

- reading `/Users/xjp/Desktop/TaxoBench-CS` as read-only upstream data
- validating `ground_new/*.json`
- normalizing target paper metadata
- normalizing `ref_meta`
- preserving structured `taxo_tree`
- emitting taxonomy membership rows
- copying or validating `reference_outlines`
- building `payload_sources`
- rendering deterministic prompt payloads
- writing readiness reports, source provenance, and checksums

`experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prototype/`
should own:

- reading staged files under `data/taxobench-cs/`
- rendering model requests from staged payloads
- writing Batch API JSONL only when explicitly approved
- collecting model outputs
- evaluating generated outlines against `human_written`

`scripts/` at repo root should be used only if a helper becomes genuinely
cross-dataset or cross-experiment reusable.

`engineering_validation/` is appropriate for early proof-of-correctness work,
but not as the final long-term location for the canonical adapter.

## Provenance And Run Records

Every adapter run that writes data should record:

- command line
- producer script path
- source root
- source snapshot date
- output root
- selected paper count
- taxonomy leaf/membership counts
- unresolved leaf count
- checksum manifest
- any anomaly list

Local canonical records belong under:

```text
data/taxobench-cs/manifests/
```

If the data package is promoted into a Drive-backed durable dataset, also record
the package in:

```text
_gdrive_sync_outline_cot/MANIFEST.tsv
_gdrive_sync_outline_cot/manifests/provenance/
_gdrive_sync_outline_cot/manifests/checksums/
```

## Current Status

Only exact reference outlines have been copied. No taxonomy/ref metadata
adapter, payload renderer, or validation script has been implemented yet.
