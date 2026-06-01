# Payloads

Status: `payload_contract_corrected_no_model_runs`

Layout:

```text
payloads/<arxiv_id>/
  tree_only_guarded.txt
  tree_with_papers.txt
  flat_concepts.txt
  random_hierarchy.txt
```

These are deterministic prompt payloads, not model outputs.

Visibility policy:

- `tree_only_guarded`: taxonomy/concept labels only
- `flat_concepts`: flat concept labels only
- `random_hierarchy`: randomized concept labels only
- `tree_with_papers`: taxonomy/concept labels plus reference paper titles only

Raw Semantic Scholar `paperId` values, years, external ids, and abstracts must
not be rendered into prompt-visible taxonomy payload leaves.
