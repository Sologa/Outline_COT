# Settings Lineage

Status: `prompt_contract_corrected_no_model_runs`

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
- preserves labels
- does not use another LLM pass

TaxoBench-CS change:

- projection should operate on structured `taxo_tree` rather than parsing
  rendered Tree50 text.
- descendant Semantic Scholar `paperId` leaves are source membership links, not
  prompt-visible concept labels; the TaxoBench-CS projection omits them.

### `random_hierarchy`

Source experiment:

`experiments/2026-05-30_tree50_round4_hierarchy_sanity_gpt5nano_batch`

Known support:

- hierarchy sanity D arm
- deterministic projection
- preserves labels and concept edge count where possible
- randomizes non-root concept parent assignment

TaxoBench-CS change:

- seed should change from the Tree50 seed to this experiment's seed base:
  `taxobench_cs_outline_payload_v1`
- descendant Semantic Scholar `paperId` leaves are omitted from the
  prompt-visible randomized hierarchy.

## Planned New Support

### `tree_with_papers`

Current support status:

`implemented_title_only_payload_no_model_runs`

Do not describe this arm as supported by existing Tree50 code.

Related but non-reusable lane:

`engineering_validation/2026-05-30_tree50_classified_paper_attachment_separation`

That lane separates paper/citation/method-example attachments for audit. Its
attachment ledger is audit-only and should not be injected into an
outline-generation prompt.

TaxoBench-CS defines a new formal arm for readable paper-title leaves. Current
decisions:

- title-only leaf rendering
- abstracts, paper ids, years, and external ids are forbidden in the taxonomy
  payload
- token-budget policy remains bounded by future render-only smoke checks
- prompt-visible arm labels are forbidden in the main prompt contract
- evaluator label remains the arm id in metadata, not prompt text
- tests proving `tree_with_papers` does not collapse into a hidden reference
  metadata duplication ablation

Initial policy in this scaffold:

- include reference paper titles only at taxonomy leaves
- do not expose Semantic Scholar `paperId`, year, external ids, or abstracts
  inside taxonomy payloads

## Deferred Prompt-Steering Ablation

`instruction-guided taxonomy` is not part of the current main matrix. In the
reviewer-facing design, current taxonomy arms should be neutral auxiliary
payload appends. A guided version would tell the model to use the taxonomy as an
organizational signal, so it measures a different effect: taxonomy content plus
prompt steering.

If reopened, add guided variants as explicit separate arms and compare each
guided arm against its neutral counterpart. Do not rewrite `tree_only_guarded`
or `tree_with_papers` in place.

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
