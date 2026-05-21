# Engineering Validation

`engineering_validation/` is the incubation area for larger code changes that need a temporary spec, prototype, and validation surface before promotion into the stable pipeline.

Use one directory per change:

```text
engineering_validation/YYYY-MM-DD_change_slug/
  spec.md
  implementation_plan.md
  validation_plan.md
  runbook.md
  promotion_checklist.md
  artifact_manifest.md
  prompts/
  prototype/
  tests/
  fixtures/
```

What belongs here:

- the code-change problem statement and intended behavior
- implementation plans, risk notes, and rollback notes
- small prototype code that is not imported by stable scripts
- focused tests and small fixtures for validating the change
- prompt variants local to the change, when the change is prompt-facing
- pointers to validation artifacts stored elsewhere

What does not belong here:

- bulky run outputs
- logs and caches
- full model responses or debug dumps
- downloaded corpora
- stable pipeline code after promotion

Put code-change run outputs under `results/engineering_validation/<change_id>/...`, local scratch under `.local/engineering_validation/<change_id>/...`, and Drive-backed snapshots under `_gdrive_sync_outline_cot/results/engineering_validation/<change_id>/...` or `_gdrive_sync_outline_cot/artifacts/tables/engineering_validation/<change_id>/...`.

When a change is promoted, move reusable code, tests, prompts, and docs into stable repo locations and leave a short note in the change folder that points to the promoted artifacts and validation evidence.
