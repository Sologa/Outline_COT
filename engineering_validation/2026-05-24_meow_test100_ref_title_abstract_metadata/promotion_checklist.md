# Promotion Checklist

Do not promote this validation until every required item is checked.

- [ ] Source inventory preserves all 100 MEOW target papers.
- [ ] Source inventory preserves all 12661 upstream reference rows.
- [ ] Every target paper has a separate per-paper output folder.
- [ ] Duplicate keys are preserved as separate rows.
- [ ] Resolved rows include provider, provider id or URL, title match status, year match status, confidence, and decision reason.
- [ ] Rows without reliable title identity remain `unresolved` or `low`, not silently filled.
- [ ] Sample manual review passes before full 100-paper resolution.
- [ ] Full run summary reports abstract coverage by confidence level.
- [ ] Durable dataset destination is approved before copying outputs into `_gdrive_sync_outline_cot/datasets/derived/`.
- [ ] Downstream batch-rendering scripts are updated only after frozen local metadata inputs exist.
- [ ] Downstream batch-rendering scripts no longer call arXiv or external resolvers during prompt rendering.
