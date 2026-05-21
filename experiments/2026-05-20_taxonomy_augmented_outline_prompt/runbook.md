# Runbook

This experiment is provisional. Do not update the official stable Google Sheet until the result is stable and explicitly approved.

## Scope

- Paper: `096_2502.03108`
- Input conditions: `no_abstract`, `with_abstract`
- Variants:
  - `baseline_no_taxonomy`
  - `taxonomy_augmented_v1_minimal`
  - `taxonomy_augmented_v2_guarded`
- Generation model: `gpt-5.4-mini`
- Generation reasoning effort: `medium`
- Judge backend: `codex`
- Judge model: `gpt-5.5`
- Judge reasoning effort: `high`
- Taxonomy payload: tree only; no status/kind/source boundary/qualifiers/evidence/audit/citation assignments.

## Inputs

- title and 51 references: `third_party/repos/Survey-Outline-Evaluation-Benckmark/datasets/test_prompts.json`, item index `95`
- with-abstract source: `data/paper_sets/meow_test100/tex_src/096_2502.03108/main.tex`
- reference outline wrapper: `data/paper_sets/meow_test100/outlines/096_2502.03108.outline.json`
- evaluator reference outline list adapter: `results/2026-05-20_taxonomy_augmented_outline_prompt/_inputs/096_2502.03108.reference_outline.list.json`
- taxonomy source: `results/2026-05-19_meow_taxonomy_extraction/smoke/096_2502.03108/taxonomy_extraction.json`
- primary prompt template: `experiments/2026-05-20_taxonomy_augmented_outline_prompt/prompts/taxonomy_augmented_outline_prompt_template.txt`
- guarded prompt template: `experiments/2026-05-20_taxonomy_augmented_outline_prompt/prompts/taxonomy_augmented_outline_prompt_guarded_template.txt`

## Google Drive Record

Per `AGENTS.md`, this fresh experiment uses a provisional Google Sheet first, not the stable ledger.

- Target folder: `https://drive.google.com/drive/folders/1l1bINVVStjrVuhpp6AoS_KPnwpvH0h5W?usp=drive_link`
- Official native folder: `https://drive.google.com/drive/u/0/folders/1l1bINVVStjrVuhpp6AoS_KPnwpvH0h5W`
- Official native subfolder: `02_experiments/2026-05-20_taxonomy_augmented_outline_prompt/`
- Provisional sheet name: `Outline_COT provisional taxonomy augmented outline prompt 2026-05-20`
- Provisional sheet URL: `https://docs.google.com/spreadsheets/d/1T6Rtniq9EVH_sCUp0pJ_oZLciKDWECkAYUq-lLB8IZg/edit?gid=1708901450#gid=1708901450`
- Local table package: `_gdrive_sync_outline_cot/artifacts/tables/experiments/2026-05-20_taxonomy_augmented_outline_prompt/`
- Workbook snapshot path: `_gdrive_sync_outline_cot/artifacts/tables/experiments/2026-05-20_taxonomy_augmented_outline_prompt/snapshots/Outline_COT provisional taxonomy augmented outline prompt 2026-05-20.xlsx`
- Creation route: Google Drive connector timed out during startup, so the workbook was imported through the user's logged-in Chrome Google Sheets UI and verified in the target Drive folder UI.
- Future refresh route: build the `.xlsx` plus source package locally, convert/import it into the official native experiment subfolder with `scripts/import_experiment_workbook_to_google_sheet.py`, and update `_gdrive_sync_outline_cot/MANIFEST.tsv`. Do not ask the user to manually import, and do not copy `.gsheet` pointers into `_gdrive_sync_outline_cot/` as the normal reference workflow.
- Tabs:
  - `README`
  - `Run Matrix`
  - `Prompt Variants`
  - `Taxonomy Payload`
  - `Generation Results`
  - `Judge Results`
  - `Pairwise Comparison`
  - `Manual Notes`

## Prompt Rendering

```bash
python3 experiments/2026-05-20_taxonomy_augmented_outline_prompt/prototype/run_taxonomy_augmented_outline_prompt.py --render-only
```

Expected output:

- 6 prompts rendered under `results/2026-05-20_taxonomy_augmented_outline_prompt/096_2502.03108/<input_condition>/<variant>/prompt.txt`
- `results/2026-05-20_taxonomy_augmented_outline_prompt/_summaries/prompt_rendering_validation.json`
- baseline prompts do not contain a taxonomy block
- taxonomy prompts contain only compact tree labels

## Generation

```bash
python3 experiments/2026-05-20_taxonomy_augmented_outline_prompt/prototype/run_taxonomy_augmented_outline_prompt.py --force
```

Expected per-arm outputs:

- `prompt.txt`
- `raw_response.txt`
- `chatgpt_meow_outline_blind.json`
- `codex_exec.log`
- `run_manifest.json`
- taxonomy arms only: `taxonomy_tree_payload.txt`

## Evaluation

Run each arm with explicit source/reference/output paths:

```bash
for condition in no_abstract with_abstract; do
  for variant in baseline_no_taxonomy taxonomy_augmented_v1_minimal taxonomy_augmented_v2_guarded; do
    out="results/2026-05-20_taxonomy_augmented_outline_prompt/096_2502.03108/${condition}/${variant}"
    python3 scripts/evaluate_chatgpt_meow_blind_batch.py \
      --paper 096_2502.03108 \
      --source-outline "${out}/chatgpt_meow_outline_blind.json" \
      --reference-outline results/2026-05-20_taxonomy_augmented_outline_prompt/_inputs/096_2502.03108.reference_outline.list.json \
      --output-dir "${out}" \
      --summary-path "${out}/chatgpt_meow_outline_blind.eval.summary.json" \
      --judge-backend codex \
      --model gpt-5.5 \
      --judge-reasoning-effort high \
      --concurrency 1 \
      --timeout 600 \
      --max-retries 2
  done
done
```

Expected per-arm outputs:

- `chatgpt_meow_outline_blind.eval.json`
- `chatgpt_meow_outline_blind.eval.debug.json`
- `chatgpt_meow_outline_blind.eval.summary.json`

The adapter is needed because the `meow_test100` gold file is a metadata wrapper dict whose outline list is stored under `outline`, while `scripts/evaluate_chatgpt_meow_blind_batch.py --reference-outline` expects a direct list.

## Summary

```bash
python3 experiments/2026-05-20_taxonomy_augmented_outline_prompt/prototype/summarize_taxonomy_augmented_results.py
```

Expected summary outputs:

- `results/2026-05-20_taxonomy_augmented_outline_prompt/_summaries/run_matrix.json`
- `results/2026-05-20_taxonomy_augmented_outline_prompt/_summaries/paired_comparison.json`
- `results/2026-05-20_taxonomy_augmented_outline_prompt/_summaries/paired_comparison.csv`
- `results/2026-05-20_taxonomy_augmented_outline_prompt/_summaries/manual_audit_096.md`

## Verification

- Validate every generated outline is parseable by the same parser used for baseline blind outputs.
- Confirm all normalized outline items contain `level`, `numbering`, `title`, and `ref`.
- Confirm taxonomy prompts do not include gold outline content, classified items, evidence, audit, or citation assignments.
- Compare `no_abstract` and `with_abstract` separately.
- Manually inspect `096_2502.03108` for taxonomy overexpansion and scaffold suppression before making any stable claim.
