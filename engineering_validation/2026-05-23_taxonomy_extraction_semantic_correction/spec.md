# Taxonomy Extraction Semantic Correction Spec

## Identity

- Validation id: `2026-05-23_taxonomy_extraction_semantic_correction`
- Status: scaffold only
- Created: 2026-05-23
- Owner: xjp / Codex

This is an engineering validation lane, not a direct rerun. The next conversation should decide and execute the work after reading this spec and the snapshot.

## Background

The MEOW taxonomy extraction work produced 23 extraction files for 22 unique papers under:

- `results/experiments/2026-05-19_meow_taxonomy_extraction/smoke/`
- `results/experiments/2026-05-19_meow_taxonomy_extraction/selected18_2026-05-21/`

These artifacts were then projected into tree-only payloads for:

`results/experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch_taxonomy22/2026-05-22T1241_taipei/`

The core semantic problem is not simply experimental performance. The current artifacts can be read as saying that the extracted trees are "multifaceted taxonomy trees" because node records contain `facet`. That wording is misleading. In most current artifacts, `facet` is a local split axis, branch criterion, table column, or visual grouping label. It is not a TaxoAdapt-style independent dimension tree.

## Mandatory Snapshot

Before this scaffold was created, the first-version artifacts were snapshotted at:

`results/engineering_validation/2026-05-23_taxonomy_extraction_snapshot/`

The snapshot includes:

- original 2026-05-19 extraction experiment scaffold;
- original 2026-05-19 extraction outputs;
- first taxonomy22 downstream input manifest, prompts, tree payloads, and run manifests;
- ChatGPT's TaxoAdapt-style multifaceted taxonomy audit report from `~/Downloads`, if present;
- local audit reports and OMX/subagent planning context, if present.

Integrity files:

- `results/engineering_validation/2026-05-23_taxonomy_extraction_snapshot/MANIFEST.tsv`
- `results/engineering_validation/2026-05-23_taxonomy_extraction_snapshot/sha256.txt`
- `results/engineering_validation/2026-05-23_taxonomy_extraction_snapshot/snapshot_summary.md`

Do not mutate the snapshot. If the next conversation needs to compare old and new states, use the snapshot as the old state.

## Required Context For The Next Conversation

The next conversation must read the following before proposing corrections:

1. Snapshot summary:
   - `results/engineering_validation/2026-05-23_taxonomy_extraction_snapshot/snapshot_summary.md`
2. Original extraction protocol:
   - `experiments/2026-05-19_meow_taxonomy_extraction/spec.md`
   - `experiments/2026-05-19_meow_taxonomy_extraction/runbook.md`
   - `experiments/2026-05-19_meow_taxonomy_extraction/config.yaml`
3. Original extraction summaries:
   - `results/experiments/2026-05-19_meow_taxonomy_extraction/smoke/smoke_summary.md`
   - `results/experiments/2026-05-19_meow_taxonomy_extraction/selected18_2026-05-21/selected18_summary.md`
4. First taxonomy22 downstream input record:
   - `results/experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch_taxonomy22/2026-05-22T1241_taipei/_inputs/taxonomy22_input_manifest.json`
   - `results/experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch_taxonomy22/2026-05-22T1241_taipei/_summaries/prompt_rendering_validation.json`
5. ChatGPT's TaxoAdapt-style audit report:
   - `results/engineering_validation/2026-05-23_taxonomy_extraction_snapshot/external_context/taxoadapt_style_multifaceted_taxonomy_audit_meow_samples_zh_TW.md`
   - If absent in the snapshot, check `~/Downloads/taxoadapt_style_multifaceted_taxonomy_audit_meow_samples_zh_TW.md`.
6. TaxoAdapt definition sources:
   - `/Users/xjp/Desktop/Taxonomy/external/paper_repos/taxoadapt/README.md`
   - `/Users/xjp/Desktop/Taxonomy/docs/papers/pdf/TaxoAdapt_Aligning_LLM_Based_Multidimensional_Taxonomy_Construction.pdf`
7. Prior OMX/subagent planning context:
   - `results/engineering_validation/2026-05-23_taxonomy_extraction_snapshot/omx_context/turns-2026-05-19.jsonl`
   - `results/engineering_validation/2026-05-23_taxonomy_extraction_snapshot/omx_context/2026-05-23_10-12-28Z-skill-omx.md`

## Strict Definition To Preserve

The next conversation must not treat a taxonomy as TaxoAdapt-style merely because a JSON node has a `facet` field.

A TaxoAdapt-style multifaceted taxonomy forest requires all or most of the following:

- Multiple independent dimensions, such as `tasks`, `datasets`, `methodologies`, `evaluation_methods`, and `real_world_domains`.
- A separate taxonomy tree or DAG per dimension.
- Paper-to-dimension classification, where a paper may contribute to multiple dimensions.
- Paper-to-node assignments inside each dimension tree.
- Corpus-grounded expansion logic based on paper density, unmapped papers, width expansion, and depth expansion.
- Iterative hierarchical classification and expansion, not only static author-provided categories.

By contrast:

- a single author taxonomy tree with many branch-level split criteria is not multifaceted;
- shallow facets such as `Stage / Problem / Aim / Solution` are faceted classification, not automatically TaxoAdapt-style;
- multiple independent author figures are a forest, but not TaxoAdapt-style unless they are aligned by corpus/paper assignments and expansion logic;
- table columns, visual groupings, or branch labels should not be called independent facet trees.

## Problem Statement

Current `taxonomy_extraction.json` records need semantic correction because:

- `node.facet` often means local split axis, not a true independent facet;
- `taxonomy_kind=faceted_taxonomy` can mix shallow coding schemes, table facets, and stronger faceted frameworks;
- the artifacts do not clearly state `is_taxoadapt_style_multifaceted=false`;
- downstream readers may infer that the existing trees are multifaceted taxonomy trees when they are not.

This is a correctness issue independent of whether a downstream outline-generation result improves or worsens.

## Proposed Correction Strategy

Do not overwrite original artifacts in place unless the user explicitly approves after reviewing the v2 output. Prefer a correction layer.

Recommended output location:

`results/engineering_validation/2026-05-23_taxonomy_extraction_semantic_correction/`

Recommended per-paper output:

- `taxonomy_extraction.corrected.json`
- `semantic_diff.md`
- `correction_manifest.json`

Recommended aggregate output:

- `correction_summary.md`
- `validation_report.json`
- `taxoadapt_style_verdicts.tsv`

## Proposed Schema Changes

At minimum, corrected artifacts should distinguish:

- `local_split_axis`: replacement or projection for most current `node.facet` values.
- `artifact_type`: one of `single_author_tree`, `faceted_classification_scheme`, `multiple_independent_taxonomies`, `taxonomy_like_dag`, `operational_rule_taxonomy`, `review_outline_like_taxonomy`, or another explicitly defined value.
- `is_taxoadapt_style_multifaceted`: boolean, expected `false` for current 22 papers unless a strict re-audit proves otherwise.
- `taxoadapt_style_verdict`: short categorical verdict such as `no`, `partial_near_miss`, or `insufficient_evidence`.
- `taxoadapt_style_rationale`: concise evidence-backed rationale.
- `correction_basis`: `deterministic_field_rename`, `semantic_relabel`, `sample_reaudit`, or `full_reextraction`.

Do not delete useful source-grounded information. The goal is semantic precision, not information loss.

## Initial Sample Set

Start with high-risk edge cases:

- `096_2502.03108`: single rigorous tree with many local split axes; not multifaceted.
- `074_2501.10168`: true shallow faceted classification with partial paper assignment evidence; closest near-miss but not TaxoAdapt-style.
- `077_2501.13443`: explicit faceted framework plus Sankey cross-facet flow; near-miss but no paper-to-node assignments.
- `097_2502.03668`: multiple independent taxonomy trees; not a corpus-aligned multidimensional forest.
- `037_2202.07170`: taxonomy-like DAG plus table facets; not per-dimension deep trees.
- `094_2502.02459`: mixed taxonomy/review outline, flow, and tables; high risk for overclaiming.

## Non-Goals

- Do not re-run the 22-paper extraction immediately.
- Do not mutate the original snapshot.
- Do not update Google Sheets.
- Do not rerun taxonomy22 downstream generation until semantic correction is reviewed.
- Do not claim that current artifacts are TaxoAdapt-style multifaceted trees.

## Exit Criteria For This Validation Lane

The validation lane is successful when:

- every one of the 22 unique papers has a clear artifact-level type;
- every paper has an explicit TaxoAdapt-style verdict;
- node-level `facet` has either been renamed/projection-mapped or explained as a local split axis;
- correction outputs are generated separately from the original artifacts;
- a diff/manifest makes every semantic correction auditable;
- the user can decide whether to run corrected downstream payload experiments.
