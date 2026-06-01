# Settings Lineage

Status: `draft_data_pending_no_runs`

This document records prior experiment settings that this scaffold may reuse.
It separates existing support from planned TaxoBench-CS-specific work.

## Existing Support

### `baseline_no_taxonomy`

Source experiment:

`experiments/2026-05-26_tree50_round4_baseline_tree_gpt5nano_batch`

Known support:

- round4 A arm
- title plus reference metadata
- no target survey/review abstract
- reference abstracts preserved when available
- `metadata_*` provenance fields stripped

Likely reuse:

- baseline prompt builder behavior
- Batch API request shape
- prompt hygiene validation

### `tree_only_guarded`

Source experiment:

`experiments/2026-05-26_tree50_round4_baseline_tree_gpt5nano_batch`

Known support:

- round4 B arm
- title plus reference metadata
- exact tree payload in guarded prompt template
- no target survey/review abstract

TaxoBench-CS change:

- source payload will be structured `taxo_tree` JSON, not round4
  `manual_tree_only_payload.txt`

### `flat_concepts`

Source experiment:

`experiments/2026-05-30_tree50_round4_hierarchy_sanity_gpt5nano_batch`

Known support:

- hierarchy sanity C arm
- deterministic projection
- removes parent-child concept hierarchy
- preserves labels and descendant citation leaves
- does not use another LLM pass

TaxoBench-CS change:

- projection should operate on structured `taxo_tree` rather than parsing
  rendered Tree50 text.

### `random_hierarchy`

Source experiment:

`experiments/2026-05-30_tree50_round4_hierarchy_sanity_gpt5nano_batch`

Known support:

- hierarchy sanity D arm
- deterministic projection
- preserves labels, citation leaves, and concept edge count where possible
- randomizes non-root concept parent assignment

TaxoBench-CS change:

- seed should change from the Tree50 seed to this experiment's seed base:
  `taxobench_cs_outline_payload_v1`

## Planned New Support

### `tree_with_papers`

Current support status:

`not_implemented`

Do not describe this arm as supported by existing Tree50 code.

Related but non-reusable lane:

`engineering_validation/2026-05-30_tree50_classified_paper_attachment_separation`

That lane separates paper/citation/method-example attachments for audit. Its
attachment ledger is audit-only and should not be injected into an
outline-generation prompt.

TaxoBench-CS must define a new formal arm if it wants taxonomy leaves rendered
with paper metadata. Required decisions:

- allowed paper fields
- whether abstracts are forbidden or allowed
- token-budget policy
- prompt label
- evaluator label
- tests proving `tree_with_papers` does not collapse into a hidden reference
  metadata duplication ablation

Initial policy in this scaffold:

- include paper id, title, year, and stable external ids at taxonomy leaves
- do not duplicate abstracts inside taxonomy payloads by default

## Shared Generation Settings

Planned settings inherited from recent Tree50 batches:

- transport: OpenAI Batch API
- endpoint: `/v1/responses`
- model: `gpt-5-nano`
- reasoning effort: `high`
- max output tokens: `32768`
- retry escape hatch max output tokens: `65536`

These settings are documented for future use only. No request payloads or batch
files were created by this scaffold.

## Shared Evaluation Settings

Planned evaluation lineage:

- structural metric: `structural_distance`
- judge backend: `codex`
- judge model: `gpt-5.5`
- judge reasoning effort: `high`
- judge dimensions:
  - `结构_信息快速定位`
  - `结构_详略得当`
  - `内容_章节互斥性`
  - `内容_逻辑深度`
  - `内容_学术价值`
  - `语用_描述性与简洁性`

TaxoBench-CS evaluator must still document how it handles original-paper
citation keys versus TaxoBench `paperId` leaves.
