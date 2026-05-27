# Validation Plan

## Static Checks

```bash
python3 -m json.tool engineering_validation/2026-05-24_hf_meow_tree50_source_extraction_v2/prompts/source_extraction_output_schema.json >/dev/null
```

## Input Checks

- selected Tree50 manifest exists;
- selected Tree50 manifest has exactly 50 rows;
- selected paper IDs are unique;
- every selected paper has a source-confirmation bundle and final confirmation;
- every selected paper has local PDF and TeX source paths.

## Extraction Checks

- every produced `taxonomy_extraction.json` is valid JSON;
- every produced extraction has at least one taxonomy;
- every countable taxonomy has at least 3 nodes and 2 parent-child edges;
- every node and parent-child edge has evidence IDs;
- every evidence ID resolves to a source locator;
- no selected node or edge evidence resolves to:
  - section headings;
  - table environments;
  - table captions;
  - table cells;
  - MEOW outline;
  - COT;
  - metadata;
  - title or abstract;
  - OCR-only text;
  - filenames only.

## Review Checks

- every final success has first-pass and second-review artifacts;
- every final success has second-review status `pass` or `pass_with_notes`;
- disagreements are not promoted until resolved.

## Bridge Checks

- every successful extraction has `taxonomy_extraction.corrected.json`;
- every successful extraction has `v2_tree_only_payload.txt`;
- semantic correction does not alter labels, node IDs, edges, or evidence IDs
  unless explicit embedded evidence supports review-needed status.
