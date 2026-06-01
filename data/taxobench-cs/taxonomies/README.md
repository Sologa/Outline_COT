# Taxonomies

Status: `schema_only_no_data_conversion`

Future files:

- `<arxiv_id>.taxonomy_source.json`
- `<arxiv_id>.taxonomy_membership.jsonl`

`taxonomy_source.json` should preserve the structured TaxoBench `taxo_tree`.

`taxonomy_membership.jsonl` should have one row per leaf mention. This preserves
multi-membership when one `paperId` appears under multiple branches.
