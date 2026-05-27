You are auditing Tree50 manual taxonomy payloads after a confirmed edge-topology error. Work in /Users/xjp/Desktop/Outline_COT.

Critical rule: pdftotext/OCR is node-label inventory only. It must not determine parent-child edges. Edges must come from TeX forest/TikZ/source graph structure, rendered figure arrow tracing, or explicit paper prose that names the relation. For image-only figures, inspect rendered images/PDFs directly at sufficient zoom/crops. If you cannot verify every edge, mark the paper partial or needs_human_visual_review; do not call it verified.

Output only under your assigned folder:
engineering_validation/2026-05-25_tree50_edge_verified_reextract_round4_audit/agent_outputs/agent_1_round1_a/

For each assigned paper, create:
- <paper_id>.md: concise audit report with source figure(s), correction summary, and edge evidence.
- <paper_id>.payload.txt: corrected tree-only payload if fully or partially verified.
- <paper_id>.status.json: machine-readable status with keys: paper_id, edge_audit_status, correction_action, source_figures, edge_evidence, unresolved_edges, payload_path.

Statuses:
- edge_verified_unchanged: prior payload matches edge evidence.
- edge_verified_corrected: you corrected one or more edges/nodes and verified the result.
- partial_edge_audit: some edges verified but unresolved remains.
- needs_human_visual_review: figure/image too ambiguous or you cannot verify topology.
- exclude_no_taxonomy_tree: only if source confirms no taxonomy/tree should be counted.

Do not modify old v2, round1, round2, round3, or round4 per_paper folders. Your job is source audit + corrected payloads in agent_outputs only. Preserve user skip/exclude instructions.

For every leaf with method/paper attachments, explicitly verify its parent. For multi-figure papers, keep separate figure sections unless the source explicitly unifies them.

Assigned papers:
- 1703.06118
- 1805.10511
- 1910.04656
- 1910.08252
- 2001.09957
- 2006.00093
- 2008.07235
- 2009.12153
- 2010.00713
- 2010.12742

Useful paths:
- Current draft package: _gdrive_sync_outline_cot/results/engineering_validation/2026-05-25_tree50_edge_verified_reextract_round4/per_paper/<paper_id>/payloads/manual_tree_only_payload.txt
- Prior draft/status copied in the same per_paper folder as prior_manual_draft.md and prior_status.json.
- Source TeX/PDF roots: data/paper_sets/hf_meow_raw_taxonomy_high261/tex_src/*_<paper_id>/ and data/paper_sets/hf_meow_raw_taxonomy_high261/pdf/*_<paper_id>.pdf

Create your output folder if needed: /Users/xjp/Desktop/Outline_COT/engineering_validation/2026-05-25_tree50_edge_verified_reextract_round4_audit/agent_outputs/agent_1_round1_a
