# Subagent Writeback Prompt Round 3

You previously returned markdown findings for your assigned paper IDs. Now write
only your assigned papers into the round-3 audit/results folders.

Workspace:

`/Users/xjp/Desktop/Outline_COT`

Do not modify the original v2 folder:

`_gdrive_sync_outline_cot/results/engineering_validation/2026-05-24_hf_meow_tree50_source_extraction_v2/`

Do not create folders for excluded papers `2402.01801`, `2402.03082`, or `2504.01491`.

Write scope for each assigned paper `<paper_id>`:

- `engineering_validation/2026-05-25_tree50_visual_taxonomy_reextract_round3_audit/manual_drafts/<paper_id>.md`
- `_gdrive_sync_outline_cot/results/engineering_validation/2026-05-25_tree50_manual_visual_reextract_round3/per_paper/<paper_id>/manual_draft.md`
- `_gdrive_sync_outline_cot/results/engineering_validation/2026-05-25_tree50_manual_visual_reextract_round3/per_paper/<paper_id>/payloads/manual_tree_only_payload.txt`
- `_gdrive_sync_outline_cot/results/engineering_validation/2026-05-25_tree50_manual_visual_reextract_round3/per_paper/<paper_id>/payloads/manual_tree_only_payload.with_labels.txt`
- `_gdrive_sync_outline_cot/results/engineering_validation/2026-05-25_tree50_manual_visual_reextract_round3/per_paper/<paper_id>/status.json`

Also write one group manifest under:

`_gdrive_sync_outline_cot/results/engineering_validation/2026-05-25_tree50_manual_visual_reextract_round3/_summaries/<agent_slot>_manifest.tsv`

Status mapping:

- `strict_tree` -> completeness_label=`round3_complete`, taxonomy_countability_label=`complete_strict_author_taxonomy_tree`, needs_countability_decision=false
- `multifaceted_forest` -> completeness_label=`round3_complete`, taxonomy_countability_label=`complete_multifaceted_author_taxonomy_forest`, needs_countability_decision=false
- `outline_like_taxonomy` -> completeness_label=`round3_complete_but_representation_complex`, taxonomy_countability_label=`outline_like_taxonomy_needs_countability_decision`, needs_countability_decision=true
- `dag_like_taxonomy` -> completeness_label=`round3_complete_but_representation_complex`, taxonomy_countability_label=`dag_like_taxonomy_needs_countability_decision`, needs_countability_decision=true
- `flow_taxonomy_hybrid` -> completeness_label=`round3_complete_but_representation_complex`, taxonomy_countability_label=`flow_taxonomy_hybrid_needs_countability_decision`, needs_countability_decision=true
- `exclude_or_unclear` -> completeness_label=`round3_incomplete_needs_review`, taxonomy_countability_label=`exclude_or_unclear_needs_review`, needs_countability_decision=true

`manual_tree_only_payload.txt` should contain only the text block under `Draft taxonomy`.

`manual_tree_only_payload.with_labels.txt` should include a header with:

```text
# paper_id: <paper_id>
# extraction_round: 2026-05-25_tree50_manual_visual_reextract_round3
# tree_extracted_round3: yes
# completeness_label: <mapped completeness label>
# taxonomy_countability_label: <mapped taxonomy countability label>
# manual_draft_status: <Status value>
# original_v2_payload_modified: no
# source_manual_draft: engineering_validation/2026-05-25_tree50_visual_taxonomy_reextract_round3_audit/manual_drafts/<paper_id>.md
# original_v2_payload: _gdrive_sync_outline_cot/results/engineering_validation/2026-05-24_hf_meow_tree50_source_extraction_v2/per_paper/<paper_id>/payloads/v2_tree_only_payload.txt
```

`status.json` should include the same labels, the payload paths, source figures inspected, and `manual_tree_only_payload_sha256`.

Return a concise list of files written. Do not touch files outside your assigned paper IDs and your single group manifest.
