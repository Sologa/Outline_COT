# Promotion Checklist

Before using the new Tree50 extraction artifacts downstream:

- [ ] exactly 50 selected paper IDs were loaded from the Tree50 manifest;
- [ ] all successful papers have `taxonomy_extraction.json`;
- [ ] all successful papers have first-pass and second-review extraction audits;
- [ ] no selected node or edge uses headings or tables as evidence;
- [ ] no selected node or edge uses MEOW outline/COT/metadata/title/abstract as
      evidence;
- [ ] every evidence ID resolves to a source locator;
- [ ] every successful paper has `taxonomy_extraction.corrected.json`;
- [ ] every successful paper has `v2_tree_only_payload.txt`;
- [ ] aggregate validation report has `error_count: 0`;
- [ ] user has explicitly approved downstream outline-generation experiments.
