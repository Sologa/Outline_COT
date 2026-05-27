# Taxonomy Payload Completeness Smoke Test

## Purpose

Compare outline-generation behavior when the taxonomy payload is:

- `tree_only_guarded`: the same compact tree style used by the existing batch payloads.
- `structural_complete_guarded`: a compact structural projection of the original taxonomy artifact.

This smoke test intentionally uses only paper `096_2502.03108` to keep cost and runtime low. The remaining taxonomy22 papers are out of scope until the user explicitly resumes the larger batch.

## Question

Does preserving the complete structural information from the original taxonomy artifact improve the taxonomy-to-outline prompt compared with the prior incomplete tree-only payload?

## Scope

- Paper: `096_2502.03108`
- Input condition for the first smoke run: `no_abstract`
- Prompt wording: guarded taxonomy prompt wording for both arms
- Model target for prepared batch input: `gpt-5-nano`
- No Google Sheet update unless explicitly requested later
- No paid API submission by default from this experiment-local runner

## Payload Definitions

### `tree_only_guarded`

This is the previous payload style:

- taxonomy name / root-to-leaf label tree
- parent-child structure represented only by indentation
- no node ids
- no facet labels
- no qualifiers
- no non-parent relations
- no evidence, audit, source-pack, or classified-item fields

### `structural_complete_guarded`

This is not the raw `taxonomy_extraction.json`. It is a prompt-safe structural projection:

- paper id and title
- taxonomy id, taxonomy name, kind, source boundary, and scope note
- every node with id, raw label, normalized label, depth, facet, and qualifiers
- every structural edge with source, target, and relation
- explicit exclusion policy inside the payload

It excludes:

- `classified_items`
- `evidence_ledger`
- node `evidence_ids`
- node free-form notes
- source-pack paths
- visual table review details
- audit fields
- rejected candidates
- citation assignment details
- PDF/TeX locators and local filesystem paths

## Success Criteria

- Render exactly two prompt arms for paper `096_2502.03108` by default.
- Save each prompt, payload, and manifest under `results/experiments/2026-05-23_taxonomy_payload_completeness_smoke/`.
- Save a local OpenAI Batch API input file for the two prepared smoke-test requests, without submitting it.
- Validate that the structural payload includes all 22 nodes and 21 structural edges from the original paper-096 taxonomy.
- Validate that prompt payloads do not include the excluded leakage fields.
