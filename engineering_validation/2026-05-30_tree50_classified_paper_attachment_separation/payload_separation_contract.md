# Payload Separation Contract

## Model-Facing Cleaned Payload

The cleaned payload may contain:

- taxonomy roots
- taxonomy/category/facet labels
- method labels when the method label is itself a taxonomy leaf
- parent-child hierarchy indentation
- short disambiguating notes only when they describe structure, not paper membership

The cleaned payload must not contain:

- author-year labels such as `Gari et al., 2019`
- raw citation keys such as `shen2017label`
- numeric reference ids such as `[113, 126]`
- `\cite{...}` strings
- `refs:`, `attached papers`, `methods/papers`, `papers/examples`, `annotations: [P...]`
- paper counts used only as attachment metadata, such as `(24 Solutions)` or `[187]`, unless the count is part of a taxonomy label and is explicitly justified in the report
- bibliography titles, DOI, arXiv ids, OpenAlex ids, or Semantic Scholar ids

If removing attachment leaves makes a category empty, keep the category as a leaf. Do not invent replacement children.

## Audit-Only Attachment Ledger

Each `classified_paper_attachment_ledger.jsonl` line must be a JSON object with these fields:

- `paper_id`: target survey/review paper id.
- `category_path`: array of labels from taxonomy root to the category/method node the attachment belongs to.
- `taxonomy_label`: nearest taxonomy label that owns the attachment.
- `raw_attachment_text`: exact local attachment text from the payload/source as far as available.
- `attachment_kind`: one of `citation_key`, `numeric_reference`, `author_year`, `paper_code`, `method_example`, `count_only`, `ambiguous`.
- `citation_key`: TeX/BibTeX key when available, else empty string.
- `resolved_title`: title resolved from BibTeX/ref_meta when available, else empty string.
- `matched_ref_meta_index`: integer index into `ref_meta` when confidently matched, else null.
- `source_locator`: TeX/PDF/table/figure locator proving the attachment, preferably file plus line or table/figure id.
- `confidence`: `high`, `medium`, or `low`.
- `notes`: short reason for unresolved or ambiguous cases.

The ledger is allowed to include unresolved rows. Ambiguous attachment identity must be represented explicitly instead of being silently collapsed into a title.

## Source Resolution Priority

1. TeX source that directly contains `\cite{...}`, forest/TikZ nodes, table rows, or figure overlays.
2. BibTeX entries referenced by those keys.
3. Local `ref_meta` rows for the target paper.
4. Rendered figure/PDF-visible text when TeX keys are unavailable.

If only rendered text such as `Gari et al., 2019` is available, match to BibTeX/ref_meta conservatively and mark ambiguous matches as `confidence: low`.
