# Promotion Checklist

This validation lane is not ready for downstream reruns until all items are complete.

- [ ] New conversation read the immutable snapshot summary.
- [ ] New conversation verified or at least inspected snapshot manifests.
- [ ] New conversation read ChatGPT's TaxoAdapt-style audit report.
- [ ] New conversation read TaxoAdapt README and/or paper PDF.
- [ ] `node.facet` semantics are explicitly redefined.
- [ ] A v2 correction schema is proposed and reviewed.
- [ ] High-risk sample papers are manually inspected: `096`, `074`, `077`, `097`, `037`, `094`.
- [ ] No original `taxonomy_extraction.json` was overwritten.
- [ ] Corrected artifacts, if produced, are written under `results/engineering_validation/2026-05-23_taxonomy_extraction_semantic_correction/`.
- [ ] Every corrected artifact has a semantic diff and correction manifest.
- [ ] Every paper has an explicit TaxoAdapt-style verdict.
- [ ] User approves any downstream taxonomy22 rerun.
