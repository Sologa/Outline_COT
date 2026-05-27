# Experiments

`experiments/` is the incubation area for ideas that are not yet part of the stable pipeline.

For larger code changes, bug fixes, refactors, prompt/runtime changes, or regression-validation work, use `engineering_validation/` instead.

Use one directory per experiment family:

```text
experiments/YYYY-MM-DD_short_slug/
  spec.md
  config.yaml
  prompts/
  prototype/
  tests/
  runbook.md
  promotion_checklist.md
```

What belongs here:

- the experiment hypothesis and decision criteria
- small prototype code that is not imported by stable scripts
- prompt variants local to the experiment
- focused tests or format checks for the prototype
- commands needed to rerun the experiment

What does not belong here:

- bulky run outputs
- logs and caches
- downloaded paper corpora
- stable pipeline code after promotion

Put run outputs under `results/experiments/<experiment_code_folder_name>/<run_id>/...` and local scratch under `.local/`.

The `<experiment_code_folder_name>` must match the directory name under `experiments/`. Use `<run_id>` for a timestamp, paper/run label, or batch attempt namespace.

When an experiment is promoted, move reusable code, prompts, tests, and docs into the stable repo locations and leave a short note in the experiment folder that points to the promoted artifacts.
