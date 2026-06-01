# TaxoBench-CS Outline_COT Format

Status: `reference_outlines_copied_no_payloads`

This file defines how TaxoBench-CS data should be normalized for Outline_COT.

The `reference_outlines/` copy has been run. Taxonomy/reference metadata and
payload conversion have not been run.

## Source Shape

Each source record in `/Users/xjp/Desktop/TaxoBench-CS/data/ground_new/*.json`
has:

- `arxiv_id`
- `title`
- `taxo_tree`
- `papers`
- `papers_index`

`taxo_tree` is a nested dict:

- internal taxonomy node: key with a non-empty dict value
- reference-paper leaf: 40-character Semantic Scholar `paperId` key with `{}`
  value

`papers` is a dict keyed by local numeric string index. `papers_index` maps
Semantic Scholar `paperId` to that local index.

Reference resolution rule:

```text
taxo_tree leaf paperId
  -> papers_index[paperId]
  -> papers[local_index]
  -> normalized reference row
```

Repeated leaf mentions must be preserved as taxonomy membership events. Do not
collapse the tree into only a unique paper set unless a future spec explicitly
changes that policy.

Recommended conceptual split:

- target paper row
- reference metadata rows keyed by Semantic Scholar `paperId`
- taxonomy label tree
- paper membership edges from taxonomy paths to `paperId`
- human-written outline nodes keyed by source citation keys

Do not merge outline citation keys with taxonomy `paperId` keys unless a future
resolver artifact explicitly maps them.

## Canonical Versus Derived Layers

Do not treat rendered payload text as the only transferred taxonomy data.

Canonical source-like layers:

- `manifests/input_manifest.jsonl`
- `manifests/source_provenance.json`
- `metadata/ref_meta.jsonl`
- `taxonomies/<arxiv_id>.taxonomy_source.json`
- `taxonomies/<arxiv_id>.taxonomy_membership.jsonl`
- `reference_outlines/<arxiv_id>.outline.json`

Canonical deterministic intermediate:

- `payload_sources/<arxiv_id>.payload_source.json`

Derived prompt payloads:

- `payloads/<arxiv_id>/tree_only_guarded.txt`
- `payloads/<arxiv_id>/tree_with_papers.txt`
- `payloads/<arxiv_id>/flat_concepts.txt`
- `payloads/<arxiv_id>/random_hierarchy.txt`

The payload files are prompt-safe projections of the canonical taxonomy, not
raw source-faithful renderings. `tree_only_guarded`, `flat_concepts`, and
`random_hierarchy` omit Semantic Scholar `paperId` membership leaves.
`tree_with_papers` renders reference paper titles only. None of the four payload
files should be treated as the canonical taxonomy source.

## Normalized Manifest

Future file:

`manifests/input_manifest.jsonl`

One row per selected target survey/review paper:

```json
{
  "paper_id": "2409.18786",
  "arxiv_id": "2409.18786",
  "title": "A Survey on the Honesty of Large Language Models",
  "source_ground_path": "/Users/xjp/Desktop/TaxoBench-CS/data/ground_new/2409.18786.json",
  "human_written_outline_path": "reference_outlines/2409.18786.outline.json",
  "taxonomy_source_path": "taxonomies/2409.18786.taxonomy_source.json",
  "taxonomy_membership_path": "taxonomies/2409.18786.taxonomy_membership.jsonl",
  "payload_source_path": "payload_sources/2409.18786.payload_source.json",
  "reference_count": 109,
  "reference_abstract_count": 109,
  "taxonomy_leaf_mention_count": 0,
  "taxonomy_unique_leaf_paper_count": 0,
  "taxonomy_multi_membership_extra_mentions": 0,
  "unreferenced_papers_count": 0,
  "taxonomy_unresolved_leaf_count": 0,
  "ready_for_generation": false,
  "readiness_notes": []
}
```

The example count values are illustrative except for fields copied from a
typical source record. The adapter must compute all counts from disk.

## Normalized Reference Metadata

Future file:

`metadata/ref_meta.jsonl`

One row per target-reference pair:

```json
{
  "paper_id": "2409.18786",
  "ref_index": "0",
  "ref_key": "S2:<paperId>",
  "paperId": "<paperId>",
  "title": "<reference title>",
  "year": 2024,
  "abstract": "<reference abstract>",
  "externalIds": {},
  "arxiv_id": null,
  "doi": null,
  "corpus_id": null
}
```

`ref_key` should be stable. `paperId` should be preserved in canonical metadata
so taxonomy leaves can be joined back to metadata, but raw `paperId` values are
not automatically prompt-visible taxonomy payload content.

The adapter must tolerate:

- `year = null`
- `arxiv_id = null`
- missing DOI
- missing `externalIds.Arxiv`

## Normalized Taxonomy Source

Future file:

`taxonomies/<arxiv_id>.taxonomy_source.json`

Recommended shape:

```json
{
  "paper_id": "2409.18786",
  "arxiv_id": "2409.18786",
  "title": "A Survey on the Honesty of Large Language Models",
  "source": "TaxoBench-CS ground_new taxo_tree",
  "tree": {}
}
```

Keep the original nested taxonomy structure in `tree`, but do not include
prompt-unsafe local provenance inside the tree.

## Taxonomy Membership

Future file:

`taxonomies/<arxiv_id>.taxonomy_membership.jsonl`

One row per leaf mention, not one row per unique paper:

```json
{
  "paper_id": "2409.18786",
  "leaf_mention_id": "2409.18786::000001",
  "paperId": "<leaf paperId>",
  "ref_index": "0",
  "path": ["Top Level", "Subtopic", "<leaf paperId>"],
  "depth": 3,
  "resolved": true
}
```

This preserves multi-membership when the same `paperId` appears under multiple
branches.

Membership rows must be emitted for every leaf mention, even when the same
`paperId` has already appeared elsewhere in the same taxonomy.

## Human-Written Reference Outline

Future file:

`reference_outlines/<arxiv_id>.outline.json`

Source:

`/Users/xjp/Desktop/TaxoBench-CS/data/taxobench_outline_exact_2026-06-01/per_paper/<arxiv_id>/outline.json`

Stored shape is a root-level flat list copied directly from the exact extractor.
Do not wrap these files as `{ "outline": [...] }` unless a future runner
requires a wrapper-specific adapter.

```json
[
  {
    "level": 1,
    "numbering": "1",
    "title": "Introduction",
    "ref": []
  }
]
```

This is an extracted human-written source outline from the paper's section
hierarchy. It is the `human_written` reference arm, not a model output and not a
hand-curated official `ground_outline`.

The source outline is a flat list, not a nested tree. Parent numbers can be
derived from `numbering` when needed, but parent ids are not present in the raw
artifact.

The raw field name is `ref`; keep its values unchanged. These are citation keys,
not Semantic Scholar paper ids.

Copy provenance, source manifest, validation, and checksums are stored under
`manifests/`, not inside each outline file.

## Payload Source

Future file:

`payload_sources/<arxiv_id>.payload_source.json`

Recommended contents:

- target `paper_id`, `arxiv_id`, `title`
- sanitized `ref_meta`
- normalized taxonomy source pointer
- taxonomy membership summary
- human-written outline pointer
- ref-key namespace and resolver status

Prompt rendering should use this file or downstream payloads, not raw
TaxoBench-CS records.

## Generated Payloads

Future payload files:

- `tree_only_guarded.txt`
- `tree_with_papers.txt`
- `flat_concepts.txt`
- `random_hierarchy.txt`

Generated payloads are prompt-visible projections. Source `taxo_tree` paper
membership leaves are internal join identifiers and must not be exposed as raw
40-character `paperId` strings in prompt payloads.

Default visibility policy:

- `tree_only_guarded`: taxonomy/concept labels only
- `flat_concepts`: flat concept labels only
- `random_hierarchy`: randomized concept labels only
- `tree_with_papers`: taxonomy/concept labels plus reference paper titles only
- forbidden in `tree_with_papers`: raw `paperId`, year, external ids, abstracts

## Output Boundary

This directory stores input data and deterministic prompt payloads only.

Do not store:

- model responses
- normalized generated outlines
- judge scores
- batch input/output JSONL
- retry logs
- Google Sheet exports
