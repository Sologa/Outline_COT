# Metadata

Status: `schema_only_no_data_conversion`

Future files:

- `papers.jsonl`: one target survey/review paper row per selected `arxiv_id`
- `ref_meta.jsonl`: one target-reference row per `papers` record

Reference rows must preserve Semantic Scholar `paperId` so taxonomy leaves can
join back to paper metadata.
