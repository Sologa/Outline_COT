# Subagent Manual Extraction Prompt

You are working read-only in:

`/Users/xjp/Desktop/Outline_COT`

Do not modify files.

Your task is to manually reconstruct complete taxonomy draft trees for the
assigned paper IDs. The existing v2 payloads are known to be incomplete because
the old source-extraction worker saw only text bundles, not the actual figure
pixels or full figure text.

For each assigned paper:

1. Open the existing payload and extraction artifact:
   - `results/engineering_validation/2026-05-24_hf_meow_tree50_source_extraction_v2/per_paper/<paper_id>/payloads/v2_tree_only_payload.txt`
   - `results/engineering_validation/2026-05-24_hf_meow_tree50_source_extraction_v2/per_paper/<paper_id>/taxonomy_extraction.json`
   - if no payload exists, open `failure.json`, first pass, and second review.
2. Locate the source corpus directory under:
   - `data/paper_sets/hf_meow_raw_taxonomy_high261/tex_src/`
   - `data/paper_sets/hf_meow_raw_taxonomy_high261/pdf/`
3. Inspect the user-specified figures directly. Use TeX, `pdftotext -layout`,
   rendered figure images, and direct visual reading as needed.
4. Return a complete draft tree or forest in markdown.

For each paper, return this structure:

```markdown
## <paper_id>

Status: strict_tree | multifaceted_forest | outline_like_taxonomy | exclude_or_unclear

Source figures inspected:
- ...

Draft taxonomy:
```text
...
```

Evidence:
- ...

Original v2 issue:
- ...

Uncertainties:
- ...
```

Evidence restrictions:

- Do not use MEOW outline, COT, metadata, title, or abstract as taxonomy evidence.
- Section headings can help navigation but should not be the only taxonomy
  evidence.
- If the figure is outline-like rather than a taxonomy, say so explicitly.
- Preserve author/source labels as literally as possible.
