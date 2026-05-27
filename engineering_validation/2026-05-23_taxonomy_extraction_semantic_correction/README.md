# Taxonomy Extraction Semantic Correction

Status: scaffold only. Do not perform correction in this directory until a new conversation explicitly starts the work.

This validation lane exists to correct the semantics of the existing MEOW taxonomy extraction artifacts without destroying the first-version record. The immediate issue is that current artifacts use `facet` in ways that can be confused with TaxoAdapt-style multifaceted taxonomy trees. Most current `facet` values are local node/branch split criteria, not independent multidimensional taxonomy trees.

The immutable snapshot for the old state is:

`results/engineering_validation/2026-05-23_taxonomy_extraction_snapshot/`

Start by reading `spec.md` and `handoff_prompt_for_new_thread.md`.
