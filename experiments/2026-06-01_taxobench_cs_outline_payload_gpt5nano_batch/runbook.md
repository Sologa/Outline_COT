# Runbook

Status: `live_human_written_judge_smoke_passed_no_generation`

This runbook records completed local data-readiness work and remaining
execution gates. Canonical staging and deterministic payloads were written after
explicit approval on 2026-06-01. Do not submit generation or judge Batch jobs,
run live evaluation, write model artifacts into `results/`, or update Google
Sheets without a separate explicit approval.

## Phase 0: Scaffold

Completed:

- create experiment directories
- document source data contracts
- document prompt and arm matrix
- document future adapter/runner/evaluator hooks

Still forbidden without separate explicit approval:

- no submitted OpenAI Batch jobs
- no batch submission
- no live Batch output parsing or publication into `results/`
- no live judge/evaluation run
- no Google Sheet update
- no mutation inside `/Users/xjp/Desktop/TaxoBench-CS`

## Intended Artifact Roots

Experiment docs and future prototype code:

```text
experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/
```

Future staged derived data package:

```text
data/taxobench-cs/
```

Future active scratch:

```text
.local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/
```

Future run outputs:

```text
results/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/<run_id>/
```

`results/` is expected to be the repo symlink into
`_gdrive_sync_outline_cot/results/`. Avoid high-frequency scratch and unverified
collector output there.

## Phase 1: Adapter Dry Run

Completed on 2026-06-01.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 data/taxobench-cs/scripts/prepare_taxobench_cs_inputs.py \
  --source-root /Users/xjp/Desktop/TaxoBench-CS \
  --output-root data/taxobench-cs \
  --dry-run \
  --limit 2 \
  --report .local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/smoke/adapter_dry_run_limit2.json
```

Verified checks:

- reads TaxoBench-CS as read-only
- discovers ground JSON records
- discovers matching human-written outline files
- normalizes reference metadata without local paths
- verifies taxonomy leaves resolve to `papers_index` or reports unresolved leaves
- writes no staged package in dry-run mode
- selected papers: `2`
- ready papers: `2`
- unresolved taxonomy leaf mentions: `0`

## Phase 2: Full Staging

Completed after explicit approval on 2026-06-01.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 data/taxobench-cs/scripts/prepare_taxobench_cs_inputs.py \
  --source-root /Users/xjp/Desktop/TaxoBench-CS \
  --output-root data/taxobench-cs \
  --write-staging \
  --force \
  --report data/taxobench-cs/manifests/canonical_staging_write_report.json
```

Staged files:

```text
data/taxobench-cs/
  README.md
  manifests/input_manifest.jsonl
  manifests/source_provenance.json
  metadata/ref_meta.jsonl
  reference_outlines/
  payload_sources/
```

Verified count checks:

- `156` staged manifest rows
- `156` human-written outline files
- `156` taxonomy source payloads
- `11609` normalized reference rows
- `13205` taxonomy leaf paper-id mentions
- `0` unresolved taxonomy leaf mentions
- `2283` multi-membership extra leaf mentions reported
- `687` `papers` rows not represented by taxonomy leaves measured
- zero missing target titles
- zero missing `taxo_tree`
- zero missing `papers`

## Phase 3: Payload Projection

Completed on 2026-06-01.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 data/taxobench-cs/scripts/generate_taxobench_cs_payloads.py \
  --staging-root data/taxobench-cs \
  --output-root data/taxobench-cs \
  --experiment-id 2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch \
  --force
```

Expected future payloads per paper:

- `tree_only_guarded`
- `tree_with_papers`
- `flat_concepts`
- `random_hierarchy`

Payload visibility contract corrected on 2026-06-02:

- `tree_only_guarded` omits raw Semantic Scholar `paperId` membership leaves.
- `flat_concepts` and `random_hierarchy` omit descendant paper evidence.
- `tree_with_papers` renders reference paper titles only, without raw `paperId`,
  year, external ids, or abstracts.

Regeneration command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 data/taxobench-cs/scripts/generate_taxobench_cs_payloads.py \
  --staging-root data/taxobench-cs \
  --output-root data/taxobench-cs \
  --experiment-id 2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch \
  --force
```

Validation command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 data/taxobench-cs/scripts/validate_taxobench_cs_staging.py \
  --staging-root data/taxobench-cs \
  --expect-papers 156 \
  --require-payloads \
  --report data/taxobench-cs/manifests/readiness_report.json
```

Verified on 2026-06-02:

- `156` ready papers
- `624` payload files
- `624` payload visibility checks
- `0` fatal validation errors

Projection report per paper includes:

- taxonomy node count
- concept count
- taxonomy leaf count
- unresolved taxonomy leaf count
- flat concept count
- random hierarchy seed

Verified payload files: `624`.

## Phase 4: Render Smoke

Completed locally under `.local/` on 2026-06-01. This render smoke did not
submit any model job and did not write `results/`.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prototype/run_taxobench_cs_outline_batch.py \
  --staging-root .local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/smoke/staging \
  --output-root .local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/smoke/render \
  --render-only \
  --write-batch-input \
  --limit 2 \
  --force
```

Expected future request count for `--limit 2`:

`2 papers * 5 generated arms = 10`

Verified request count for `--limit 2`: `10`.

Prompt hygiene check:

```bash
rg -n "Target Paper Abstract:|with_abstract|no_abstract|structural_complete_guarded|metadata_|/Users/xjp|TaxoBench-CS|meow_reconstructed_blind" \
  .local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/smoke/render \
  -g 'prompt.txt' -g 'batch_input.jsonl'
```

Expected output: no matches.

Prompt-template comparability check completed on 2026-06-02:

- baseline prompt must be the released MEOW baseline with no outer wrapper
- taxonomy prompts must preserve the same baseline skeleton and append only a
  neutral auxiliary taxonomy block after `References:`
- rendered prompts must not contain `Payload mode:`, arm labels, or
  treatment-only usage guidance
- instruction-guided taxonomy must remain absent from this main matrix unless it
  is introduced as explicit new guided arms with updated request counts

This render smoke is not approval for live generation. It only proves request
rendering, hygiene, and prompt-contract comparability in `.local` render-only
artifacts.

Payload visibility check:

```bash
rg -n "\\b[0-9a-fA-F]{40}\\b|papers:|paperId|year:|ids:|ArXiv=|DOI=|DBLP=|CorpusId|MAG=|abstract:" \
  data/taxobench-cs/payloads \
  -g '*.txt'
```

Expected output: no matches.

Fresh Task 16 rerun on 2026-06-02 against canonical staging:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prototype/run_taxobench_cs_outline_batch.py \
  --staging-root data/taxobench-cs \
  --output-root .local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/task16_generation_render_smoke \
  --render-only \
  --write-batch-input \
  --limit 2 \
  --force
```

Verified:

- output root:
  `.local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/task16_generation_render_smoke`
- request count: `10`
- generated arms:
  `baseline_no_taxonomy`, `flat_concepts`, `random_hierarchy`,
  `tree_only_guarded`, `tree_with_papers`
- `human_written` generation requests: `0`
- prompt hygiene grep: no matches
- payload visibility grep: no matches
- artifact size: `2.4M`

## Phase 5: Judge Batch Render/Parse Preparation

Task 15 local evaluator support is implemented for OpenAI Batch API judge
transport without calling the API.

Implemented local operations:

- render judge Batch JSONL for `/v1/responses`
- include stable `custom_id` values in `<paper_id>__<arm>` format
- map `human_written` to source outline = reference outline
- precompute `human_written` structural distance as `0`
- parse downloaded Batch output JSONL fixtures into `.eval.json` and
  `.eval.debug.json` artifacts under the chosen local output root

Still not implemented or approved:

- upload Batch input files
- create OpenAI Batch jobs
- poll/retrieve live Batch metadata
- download live Batch output/error files
- write model-run artifacts into `results/`

Render-only three-paper judge smoke command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prototype/evaluate_taxobench_cs_outlines_batch.py \
  --staging-root data/taxobench-cs \
  --output-root .local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/judge_human_written_smoke \
  --render-only \
  --write-batch-input \
  --arm human_written \
  --paper-id 2309.06794 \
  --paper-id 2311.09008 \
  --paper-id 2212.10535 \
  --force
```

Expected:

- `3` Batch JSONL rows
- every row is `human_written`
- every precomputed structural distance is `0`
- no OpenAI API call
- no `results/` write

Verified on 2026-06-02:

- output root:
  `.local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/judge_human_written_smoke`
- `batch_input.jsonl`: `3` rows
- `precomputed_structural.jsonl`: `3` rows
- custom ids:
  `2309.06794__human_written`, `2311.09008__human_written`,
  `2212.10535__human_written`
- request URL set: `/v1/responses`
- manifest arms: all `human_written`
- `source_equals_reference`: all `true`
- precomputed structural distances: all `0.0`
- prompt/body hygiene grep for local paths and adapter/debug/provenance fields:
  no matches
- artifact size: `92K`

Downloaded/fixture Batch output parser shape:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prototype/evaluate_taxobench_cs_outlines_batch.py \
  --output-root .local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/judge_human_written_smoke \
  --parse-batch-output path/to/downloaded_or_fixture_batch_output.jsonl \
  --force
```

Current price check for planning, not approval: OpenAI's API pricing page
checked on 2026-06-02 lists GPT-5.5 at `$5.00 / 1M` input tokens and
`$30.00 / 1M` output tokens for standard processing, and says Batch API saves
`50%` on inputs and outputs over a 24-hour asynchronous window. Therefore the
current Batch planning rate for GPT-5.5 is `$2.50 / 1M` input tokens and
`$15.00 / 1M` output tokens before any long-context or hidden reasoning-token
effects.

Token planning estimate before live approval:

- human-written judge input mean: about `2.8k-2.9k` tokens/request
- human-written full calibration: `156` requests, about `0.44M` input tokens
- five generated arms: `780` requests, about `2.2M` input tokens by
  human-outline proxy
- all six comparison rows: `936` requests, about `2.6M` input tokens by
  human-outline proxy
- visible judge output from prior Tree50-style artifacts: about `660`
  tokens/request
- high-reasoning judge runs may bill hidden reasoning tokens as output tokens,
  so live approval should be based on the current pricing page plus a tiny
  3-request live judge smoke first

Live three-paper judge smoke completed on 2026-06-02 after explicit user
approval:

```bash
set -a; source .env; set +a
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prototype/evaluate_taxobench_cs_outlines_batch.py \
  --staging-root data/taxobench-cs \
  --output-root .local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/judge_human_written_smoke \
  --render-only \
  --write-batch-input \
  --submit-live \
  --arm human_written \
  --paper-id 2309.06794 \
  --paper-id 2311.09008 \
  --paper-id 2212.10535 \
  --poll-interval-seconds 15 \
  --max-wait-seconds 3600 \
  --force
```

Verified:

- Batch id: `batch_6a1ddfa907a48190b2c71010e2a81c22`
- status: `completed`
- request counts: `3 completed / 0 failed / 3 total`
- `batch_output.jsonl`: `3` rows
- parsed eval summary: `3 / 3` success
- all rows include the six repo-local judge score keys
- average structural distance: `0.0`
- per-row structural distance: all `0.0`
- token usage:
  - `2309.06794__human_written`: `2493` input, `1207` output,
    `516` reasoning output tokens
  - `2311.09008__human_written`: `2812` input, `3017` output,
    `2070` reasoning output tokens
  - `2212.10535__human_written`: `3338` input, `2438` output,
    `1552` reasoning output tokens
  - total: `8643` input, `6662` output, `15305` total tokens
- approximate Batch cost at recorded GPT-5.5 Batch planning rates:
  `$0.122`
- local artifacts:
  - `.local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/judge_human_written_smoke/batch_latest.json`
  - `.local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/judge_human_written_smoke/batch_output.jsonl`
  - `.local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/judge_human_written_smoke/evaluation_summary.json`
  - `.local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/judge_human_written_smoke/evaluations/*/human_written/chatgpt_meow_outline_blind.eval.json`

No full generation, full evaluation, `results/` write, or Google Sheet update
was performed.

## Phase 6: Submit/Collect Generation Batch

Not implemented and not approved.

Planning count only if `156` papers are ready:

`156 papers * 5 generated arms = 780`

## Phase 7: Full Evaluation

Live evaluation is not approved.

The evaluator compares generated outlines against `human_written`. The final
comparison table may include `human_written` as a calibration row, but it is not
generated.

Planning row count only if `156` papers are ready:

`156 papers * 6 arms = 936`

## Promotion Gate

Before this experiment can move to live generation:

- adapter dry-run passes: done
- staged manifest row counts are verified from disk: done
- taxonomy leaves either resolve or unresolved leaves are documented: done, zero unresolved
- prompt hygiene render smoke passes with current prompt and payload contracts
- `tree_with_papers` title-only contract is implemented and tested
- prompt-template comparability checks in `TASKS.md` Task 12 remain passing,
  including removal of prompt-visible arm labels and treatment-only instructions
- instruction-guided taxonomy is either deferred or represented by explicit
  separate guided arms with updated docs, tests, and request counts
- taxonomy-payload visibility blocker in `TASKS.md` Task 13 is resolved
- evaluator explicitly handles the citation-key versus `paperId` namespace issue
- the user approves the first live generation smoke
