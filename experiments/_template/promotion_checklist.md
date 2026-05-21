# Promotion Checklist

Before promoting this experiment into the stable pipeline:

- [ ] The experiment has a clear baseline comparison.
- [ ] The result is reproduced from a clean command in `runbook.md`.
- [ ] Outputs are stored under `results/<experiment_id>/...`, not inside `experiments/`.
- [ ] Large local scratch files are under `.local/`.
- [ ] Prompt provenance is clear.
- [ ] Evaluation metrics match the intended contract.
- [ ] Focused tests exist for reusable code or prompt formatting.
- [ ] Reusable code has been moved from `prototype/` to a stable code location.
- [ ] Reusable direct-payload prompts have been moved to `prompts/` if they are now stable.
- [ ] Durable docs or reports have been moved to `docs/`.
- [ ] The experiment folder points to the promoted artifacts.
- [ ] The user and Codex agree that the result is stable enough for the official ledger.
