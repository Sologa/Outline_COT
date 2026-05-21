# Promotion Checklist

Before promoting this experiment into the stable pipeline:

- [ ] The experiment has a clear paired baseline comparison.
- [ ] The minimal taxonomy prompt is evaluated as the primary variant.
- [ ] The guarded taxonomy prompt is evaluated only as an ablation unless explicitly promoted.
- [ ] Baseline and taxonomy arms use the same paper inputs, model, effort, abstract setting, and evaluator.
- [ ] Taxonomy prompt rendering is deterministic.
- [ ] Taxonomy rendering excludes gold outline content.
- [ ] Prompt provenance is clear and the stable `prompts/` directory is untouched during the provisional phase.
- [ ] Outputs are stored under `results/2026-05-20_taxonomy_augmented_outline_prompt/...`, not inside `experiments/`.
- [ ] Large local scratch files are under `.local/`.
- [ ] Focused tests exist for reusable rendering code if code is added.
- [ ] Smoke results are reviewed paper by paper, not only as an aggregate.
- [ ] Failure cases are inspected for taxonomy overexpansion or scaffold suppression.
- [ ] Reusable code has been moved from `prototype/` to a stable code location only after approval.
- [ ] Reusable direct-payload prompts have been moved to `prompts/` only after approval.
- [ ] The user and Codex agree that the result is stable enough for the official ledger.
