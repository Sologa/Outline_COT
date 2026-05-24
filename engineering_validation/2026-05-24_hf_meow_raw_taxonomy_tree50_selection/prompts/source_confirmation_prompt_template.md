# Source Confirmation Prompt Template

You are reviewing one MEOW raw paper for strict taxonomy-tree eligibility.

Use only the provided source-confirmation bundle. Do not use MEOW `outline`,
`cot`, title, abstract, or metadata as taxonomy evidence. Those fields may
explain why the candidate was selected, but they cannot prove a taxonomy tree.

Count the paper only if source evidence supports:

- `taxonomy_status: explicit`
- `taxonomy_kind: tree`
- `source_boundary: author_taxonomy_tree`
- at least 3 nodes and 2 parent-child edges
- every node and edge has evidence IDs that resolve to TeX/PDF/figure/table/prose
- `evidence_source_types` contains at least one source-confirmed type such as
  `tex_line`, `pdf_page`, `visible_figure_text`, `table_cell`, `caption`, or
  `surrounding_prose`
- `uses_prohibited_evidence_as_sole_basis: false`

Reject as countable evidence:

- whole MEOW outline
- section headings alone
- COT
- metadata-only claims
- OCR-only labels without visual/source confirmation
- caption-only hints when the figure or table body contains the taxonomy

If any rejected evidence type is mentioned while reviewing, list it in
`prohibited_evidence_types_used`. If the countable decision would depend only
on rejected evidence, set `uses_prohibited_evidence_as_sole_basis: true`,
`countable_for_tree50: false`, and `audit_status: fail` or `revise`.

Return JSON matching `source_confirmation_output_schema.json`.

For countable positives, fill `taxonomy_nodes` and `taxonomy_edges`. Every
node and every parent-child edge must carry at least one evidence ID from the
bundle. Use stable local node IDs such as `n1`, `n2`, and reference those IDs in
edges.
