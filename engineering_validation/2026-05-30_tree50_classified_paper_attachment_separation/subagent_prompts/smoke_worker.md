# Smoke Worker Prompt

You are working in `/Users/xjp/Desktop/Outline_COT`.

Task: choose exactly one paper from `engineering_validation/2026-05-30_tree50_classified_paper_attachment_separation/target_papers.tsv` and perform a smoke test for classified-paper attachment separation.

Strict scope:

- Write only under `engineering_validation/2026-05-30_tree50_classified_paper_attachment_separation/per_paper/<chosen_paper_id>/`.
- Do not edit round4 payloads, experiment outputs, source data, metadata, or Google Drive artifacts.
- Do not process more than one paper.

Required outputs:

```text
per_paper/<chosen_paper_id>/
  cleaned_tree_payload.txt
  classified_paper_attachment_ledger.jsonl
  smoke_report.md
```

Use `payload_separation_contract.md` as the contract.

Procedure:

1. Pick one scoped paper that can demonstrate the separation clearly. State why in `smoke_report.md`.
2. Read its current round4 payload from `target_papers.tsv`.
3. Produce `cleaned_tree_payload.txt` by removing paper/citation/method-example attachments from the model-facing taxonomy payload while preserving taxonomy structure.
4. Build `classified_paper_attachment_ledger.jsonl` with one JSON object per attachment or attachment group. Prefer TeX citation keys and BibTeX/ref_meta resolution when available. If the source files are not locally present, record the exact missing source and use available source-confirmation/edge-audit artifacts only as fallback evidence.
5. In `smoke_report.md`, explicitly list:
   - chosen paper
   - source files inspected
   - whether original TeX source was locally available
   - how many ledger rows were produced
   - what was removed from the cleaned payload
   - unresolved/ambiguous identity matches

Return final status as one of:

- `DONE`: all outputs produced and self-checked.
- `DONE_WITH_CONCERNS`: outputs produced but source/metadata resolution was incomplete.
- `BLOCKED`: cannot produce a valid smoke.
