# Promotion Checklist

Before promoting this engineering change into the stable pipeline:

- [ ] The problem and intended behavior are explicit in `spec.md`.
- [ ] The implementation plan identifies touched files and non-goals.
- [ ] The change is reproduced from clean commands in `runbook.md`.
- [ ] Smoke checks pass.
- [ ] Focused regression checks pass.
- [ ] Full validation is complete or explicitly waived with a reason.
- [ ] Outputs are stored under `results/engineering_validation/<change_id>/...`, not inside `engineering_validation/`.
- [ ] Large local scratch files are under `.local/engineering_validation/<change_id>/...`.
- [ ] Any Drive-backed artifacts are recorded in `artifact_manifest.md`.
- [ ] Stable scripts do not import from `engineering_validation/*/prototype`.
- [ ] Reusable code has been moved from `prototype/` to a stable code location.
- [ ] Durable regression tests have been moved to repo-level `tests/`.
- [ ] Stable direct-payload prompts have been moved to `prompts/` if applicable.
- [ ] Durable docs or reports have been moved to `docs/`.
- [ ] The validation folder points to promoted artifacts and final evidence.
