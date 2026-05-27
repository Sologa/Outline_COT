# Edge-Level Taxonomy Audit SOP

1. Locate the exact user-specified figure(s).
2. Extract node labels with TeX source, vector text, OCR, or `pdftotext`; mark this as inventory only.
3. Determine every edge from authoritative structure:
   - Prefer TeX `forest`, TikZ node/edge commands, or Graphviz/source graph when present.
   - Otherwise inspect the rendered image/PDF directly at sufficient zoom/crops and trace arrow start/end.
   - Use paper prose only to confirm or disambiguate, not to invent missing branches.
4. For each leaf or paper/method attachment, verify its parent.
5. Write `edge_evidence` in status.json. If any edge cannot be verified, keep `edge_audit_status=needs_edge_audit_not_confirmed` or `edge_audit_status=partial_edge_audit`.
6. `pdftotext` row alignment must never determine parent-child links.
7. Skipped/excluded papers do not get per-paper folders.
