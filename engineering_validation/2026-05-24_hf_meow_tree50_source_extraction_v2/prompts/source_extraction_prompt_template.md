# Source Extraction Prompt Template

You are extracting a source-grounded taxonomy tree from one selected HF MEOW
Tree50 paper.

Use only the source extraction bundle embedded between
`<SOURCE_EXTRACTION_BUNDLE_JSON>` and `</SOURCE_EXTRACTION_BUNDLE_JSON>`.

Hard restrictions:

- Do not use MEOW `outline`, COT, metadata, title, or abstract as taxonomy-tree
  evidence.
- Do not use section headings as taxonomy-tree evidence.
- Do not use tables, table captions, table cells, or table-only classification
  schemes as taxonomy-tree evidence.
- Do not infer a tree from the paper section spine.
- Do not invent labels, categories, parent-child edges, or missing branches.
- Preserve author/source wording when possible.
- If the source does not support a node or edge, omit it or mark the extraction
  as not countable.

Countable extraction requirements:

- the source explicitly provides an author/source taxonomy tree;
- at least 3 nodes and 2 parent-child edges;
- every node and every parent-child edge has evidence IDs from the bundle;
- the evidence IDs resolve to TeX/PDF/visible-figure/caption/prose locators;
- no selected evidence ID resolves to headings or tables.

Return only JSON matching `source_extraction_output_schema.json`.
Include every property defined in the schema; use empty strings or null values
where the schema permits them and the source bundle does not support a stronger
value.

<SOURCE_EXTRACTION_BUNDLE_JSON>
__SOURCE_EXTRACTION_BUNDLE_JSON__
</SOURCE_EXTRACTION_BUNDLE_JSON>
