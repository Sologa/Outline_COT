# TaxoBench-CS Adapter And Smoke Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the TaxoBench-CS staged input package, deterministic taxonomy payloads, and non-LLM smoke tests needed before any generation run can be approved.

**Architecture:** Dataset-specific normalization lives under `data/taxobench-cs/scripts/` and writes reusable staged inputs under `data/taxobench-cs/`. Experiment prototype code under this directory only consumes staged inputs and may render requests in dry-run or render-only mode. Smoke tests write scratch artifacts under `.local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/` and must never submit model jobs.

**Tech Stack:** Python 3 standard library, JSON/JSONL, pytest, ripgrep, existing Outline_COT prompt/runtime helpers where they match the `title_ref_meta_no_target_abstract` contract.

---

## Current State

- `data/taxobench-cs/reference_outlines/*.outline.json` exists for `156` papers.
- Canonical staging exists under `data/taxobench-cs/` after explicit approval.
- Adapter, payload renderer, staging validator, render-only runner, and focused
  tests exist.
- Payloads were regenerated after the 2026-06-02 visibility correction:
  `tree_only_guarded`, `flat_concepts`, and `random_hierarchy` are concept-only
  prompt payloads; `tree_with_papers` keeps title-only paper leaves.
- Prompt-template comparability was corrected in the render-only prototype:
  baseline uses the released MEOW prompt skeleton, taxonomy arms append a
  neutral auxiliary taxonomy block, and instruction-guided taxonomy remains a
  separate explicit ablation.
- The previous planned judge setting, `judge backend: codex`, is now treated as
  a contract issue to correct before any live run. Generation and judging should
  both use OpenAI Batch API transport, with separate generation and judge batch
  lifecycles.
- A three-row live `human_written` judge smoke completed on 2026-06-02.
- A 780-row live generation Batch completed on 2026-06-02, but only `388 / 780`
  rows normalized into usable generated-outline JSON; the remaining rows were
  incomplete due to `max_output_tokens`.
- No full generated-arm judge output, `results/` publication, or Google Sheet
  update exists for this experiment.

## Hard Guardrails

- Do not write into `/Users/xjp/Desktop/TaxoBench-CS`.
- Do not call further OpenAI generation, Batch, or judge APIs without explicit
  approval for the next spending step.
- Do not update Google Sheets.
- Do not write model-run artifacts into `results/`.
- Smoke-test scratch must go under `.local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/`.
- Do not submit any live OpenAI Batch generation or judge job until Task 15
  render-only judge-batch smoke passes and Task 16 receives explicit user
  approval.
- Prompt-visible fields must not include local absolute paths, adapter debug fields, downloader provenance, Google metadata, or target paper abstracts.
- Do not run live model generation unless the prompt-template comparability checks from Task 12 remain passing. The current prototype is approved only for render-only request building, not for live model submission.
- Do not run live model generation unless the taxonomy-payload visibility checks from Task 13 remain passing on the current payload files.
- Do not add usage-guidance instructions such as "use the taxonomy to organize
  the outline" to the current `tree_only_guarded` or `tree_with_papers` arms.
  If instruction-guided taxonomy is tested, it must be an explicit separate
  ablation with its own arm labels, request counts, docs, and tests.

## Files To Create Or Modify

- Create `data/taxobench-cs/scripts/prepare_taxobench_cs_inputs.py`: read upstream TaxoBench-CS, validate records, normalize metadata/taxonomy, build manifest and payload sources.
- Create `data/taxobench-cs/scripts/generate_taxobench_cs_payloads.py`: render deterministic `tree_only_guarded`, `tree_with_papers`, `flat_concepts`, and `random_hierarchy` payloads from staged inputs.
- Create `data/taxobench-cs/scripts/validate_taxobench_cs_staging.py`: verify staged counts, joins, prompt hygiene, payload existence, random seed stability, and manifest readiness.
- Create `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prototype/run_taxobench_cs_outline_batch.py`: render request JSONL from staged inputs in render-only mode; keep live submission absent or fail-closed.
- Create `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prototype/evaluate_taxobench_cs_outlines_batch.py`: evaluate generated outlines and `human_written` calibration rows using OpenAI Batch API judge transport.
- Create or modify shared Batch helper code only if it reduces duplication with
  existing generation Batch lifecycle code. Keep existing direct `codex`,
  `openai`, and `gemini` judge paths backward-compatible.
- Keep `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prototype/run_taxobench_cs_outline_batch.py`, `prompts/taxobench_cs_outline_payload_prompt_template.txt`, and prompt-contract tests aligned with Task 12 before any model run.
- Modify `data/taxobench-cs/scripts/generate_taxobench_cs_payloads.py`, payload rendering tests, docs, and regenerated payload files before any model run if Task 13 confirms prompt-visible taxonomy payloads still expose `paperId` strings or over-rich leaf metadata.
- Create `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/tests/conftest.py`: load adapter scripts from the hyphenated `data/taxobench-cs/scripts/` path for pytest.
- Create `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/tests/test_taxobench_cs_adapter_contract.py`: unit/contract tests for parser, normalizer, membership preservation, and prompt hygiene.
- Create `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/tests/test_taxobench_cs_payload_rendering.py`: deterministic payload renderer tests, including `tree_with_papers`.
- Create or modify evaluator tests for OpenAI Batch judge request rendering,
  batch-output parsing, `human_written` self-evaluation, and structural-distance
  zero checks.
- Modify `data/taxobench-cs/README.md`, `FORMAT.md`, and `CONVERSION_PLAN.md` only if implementation reveals a real contract mismatch.

---

### Task 1: Add Contract Tests For Ground Record Parsing

**Files:**
- Create: `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/tests/conftest.py`
- Create: `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/tests/test_taxobench_cs_adapter_contract.py`
- Create later in this plan: `data/taxobench-cs/scripts/prepare_taxobench_cs_inputs.py`

- [ ] **Step 1: Add pytest script loader**

Test helper content to add:

```python
import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def load_taxobench_script(module_name: str):
    script_path = REPO_ROOT / "data" / "taxobench-cs" / "scripts" / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
```

- [ ] **Step 2: Write tests for required field validation**

Test content to add:

```python
from pathlib import Path

import pytest

from conftest import load_taxobench_script


adapter = load_taxobench_script("prepare_taxobench_cs_inputs")


def make_ground_record():
    return {
        "arxiv_id": "2401.00001",
        "title": "A Survey Of Example Systems",
        "taxo_tree": {
            "Representation": {
                "Graphs": {
                    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa": {}
                }
            }
        },
        "papers": {
            "0": {
                "paperId": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "title": "Graph Representations",
                "year": 2024,
                "abstract": "A reference abstract.",
                "externalIds": {"ArXiv": "2401.11111", "DOI": "10.0000/example"},
            }
        },
        "papers_index": {"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa": "0"},
    }


def test_normalize_ground_record_requires_core_fields():
    record = make_ground_record()
    del record["papers_index"]

    with pytest.raises(adapter.GroundRecordError, match="papers_index"):
        adapter.normalize_ground_record(record, source_path=Path("ground.json"))
```

- [ ] **Step 3: Write tests for taxonomy multi-membership preservation**

Append:

```python
def test_iter_taxonomy_memberships_preserves_repeated_paper_leaf():
    paper_id = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    taxo_tree = {
        "Branch A": {"Concept 1": {paper_id: {}}},
        "Branch B": {"Concept 2": {paper_id: {}}},
    }

    rows = list(adapter.iter_taxonomy_memberships(taxo_tree))

    assert len(rows) == 2
    assert rows[0]["paperId"] == paper_id
    assert rows[1]["paperId"] == paper_id
    assert rows[0]["path"] == ["Branch A", "Concept 1"]
    assert rows[1]["path"] == ["Branch B", "Concept 2"]
```

- [ ] **Step 4: Run the tests and verify they fail for missing implementation**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest \
  experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/tests/test_taxobench_cs_adapter_contract.py \
  -q
```

Expected: fails because `data/taxobench-cs/scripts/prepare_taxobench_cs_inputs.py` does not exist yet.

---

### Task 2: Add Script Entrypoint Skeleton

**Files:**
- Create: `data/taxobench-cs/scripts/prepare_taxobench_cs_inputs.py`

- [ ] **Step 1: Create the canonical script file**

Create:

```python
#!/usr/bin/env python3
"""Prepare normalized TaxoBench-CS staged inputs for Outline_COT."""

from __future__ import annotations


class GroundRecordError(ValueError):
    """Raised when a TaxoBench-CS ground record violates the expected schema."""


def normalize_ground_record(record: dict, source_path):
    raise NotImplementedError("normalize_ground_record is implemented in Task 3")


def iter_taxonomy_memberships(taxo_tree: dict):
    raise NotImplementedError("iter_taxonomy_memberships is implemented in Task 3")


if __name__ == "__main__":
    raise SystemExit("CLI is implemented in Task 4")
```

- [ ] **Step 2: Re-run the contract test**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest \
  experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/tests/test_taxobench_cs_adapter_contract.py \
  -q
```

Expected: fails with `NotImplementedError`, proving pytest is loading the canonical hyphen-path script.

---

### Task 3: Implement Ground Normalization And Membership Traversal

**Files:**
- Modify: `data/taxobench-cs/scripts/prepare_taxobench_cs_inputs.py`

- [ ] **Step 1: Implement core parser functions**

Implementation must expose:

```python
class GroundRecordError(ValueError):
    pass


def normalize_ground_record(record: dict, source_path: Path) -> dict:
    ...


def iter_taxonomy_memberships(taxo_tree: dict) -> Iterator[dict]:
    ...
```

Required behavior:

- validate `arxiv_id`, `title`, `taxo_tree`, `papers`, and `papers_index`
- detect paper leaves as 40-character lowercase or uppercase hex keys whose value is `{}`
- emit one membership row per leaf mention
- preserve repeated `paperId` appearances under different paths
- resolve each leaf through `papers_index[paperId] -> papers[index]`
- report unreferenced `papers` rows without treating them as fatal

- [ ] **Step 2: Re-run the contract test**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest \
  experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/tests/test_taxobench_cs_adapter_contract.py \
  -q
```

Expected: the tests in Task 1 pass.

---

### Task 4: Implement Staging CLI With Dry-Run And Scratch Output

**Files:**
- Modify: `data/taxobench-cs/scripts/prepare_taxobench_cs_inputs.py`

- [ ] **Step 1: Add CLI flags**

The CLI must accept:

```text
--source-root /Users/xjp/Desktop/TaxoBench-CS
--output-root data/taxobench-cs
--dry-run
--write-staging
--limit N
--report PATH
--force
```

Fail closed if neither `--dry-run` nor `--write-staging` is provided.

- [ ] **Step 2: Implement dry-run behavior**

Dry-run may write only the explicit `--report` path. It must not create or modify staged artifacts under `data/taxobench-cs/`.

- [ ] **Step 3: Implement write-staging behavior**

When `--write-staging` is used, write:

```text
<output-root>/manifests/input_manifest.jsonl
<output-root>/manifests/source_provenance.json
<output-root>/metadata/papers.jsonl
<output-root>/metadata/ref_meta.jsonl
<output-root>/taxonomies/<arxiv_id>.taxonomy_source.json
<output-root>/taxonomies/<arxiv_id>.taxonomy_membership.jsonl
<output-root>/payload_sources/<arxiv_id>.payload_source.json
```

Use atomic temp-file replacement for final writes.

- [ ] **Step 4: Run non-writing dry-run smoke**

Run:

```bash
rm -rf .local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/smoke
mkdir -p .local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/smoke
PYTHONDONTWRITEBYTECODE=1 python3 data/taxobench-cs/scripts/prepare_taxobench_cs_inputs.py \
  --source-root /Users/xjp/Desktop/TaxoBench-CS \
  --output-root data/taxobench-cs \
  --dry-run \
  --limit 2 \
  --report .local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/smoke/adapter_dry_run_limit2.json
```

Expected:

- exit code `0`
- report file exists
- selected paper count is `2`
- no new staged files are written except the report under `.local`

---

### Task 5: Implement Staging Validator

**Files:**
- Create: `data/taxobench-cs/scripts/validate_taxobench_cs_staging.py`

- [ ] **Step 1: Add validation CLI**

The CLI must accept:

```text
--staging-root PATH
--expect-papers N
--require-payloads
--report PATH
```

- [ ] **Step 2: Validate staged source artifacts**

Required checks:

- manifest row count equals `--expect-papers`
- every manifest row has `paper_id`, `arxiv_id`, `title`, `human_written_outline_path`, `payload_source_path`, and `ready_for_generation`
- every referenced outline exists
- every taxonomy source exists
- every taxonomy membership file exists
- every membership row has `path`, `depth`, `paperId`, `resolved`, and `ref_index`
- unresolved leaf count is reported
- prompt-visible payload source fields contain no `/Users/xjp`, `TaxoBench-CS`, `Target Paper Abstract:`, `metadata_`, `source_ground_path`, or `human_written_outline_path`

- [ ] **Step 3: Run validator on scratch staging after Task 4 write-staging is available**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 data/taxobench-cs/scripts/validate_taxobench_cs_staging.py \
  --staging-root .local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/smoke/staging \
  --expect-papers 2 \
  --report .local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/smoke/validate_staging_limit2.json
```

Expected: exit code `0`; report records `2` papers and zero fatal errors.

---

### Task 6: Implement Deterministic Payload Rendering

**Files:**
- Create: `data/taxobench-cs/scripts/generate_taxobench_cs_payloads.py`
- Create: `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/tests/test_taxobench_cs_payload_rendering.py`

- [x] **Step 1: Write renderer tests**

Tests must verify:

- `tree_only_guarded` preserves taxonomy/concept labels and removes prompt-visible paper membership leaves
- `tree_only_guarded` does not contain 40-character Semantic Scholar `paperId` strings
- `tree_with_papers` includes reference paper titles at taxonomy leaves
- `tree_with_papers` does not include Semantic Scholar `paperId`, year, external ids, or abstracts
- `flat_concepts` removes parent-child nesting while preserving concept labels only
- `random_hierarchy` is deterministic for the same experiment id and paper id and preserves concept labels only
- no renderer inserts generated definitions

- [x] **Step 2: Implement payload rendering CLI**

The CLI must accept:

```text
--staging-root PATH
--output-root PATH
--experiment-id 2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch
--limit N
--force
```

Write for each selected paper:

```text
<output-root>/payloads/<arxiv_id>/tree_only_guarded.txt
<output-root>/payloads/<arxiv_id>/tree_with_papers.txt
<output-root>/payloads/<arxiv_id>/flat_concepts.txt
<output-root>/payloads/<arxiv_id>/random_hierarchy.txt
<output-root>/projection_reports/<arxiv_id>.projection_report.json
```

- [x] **Step 3: Run renderer tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest \
  experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/tests/test_taxobench_cs_payload_rendering.py \
  -q
```

Expected: all renderer tests pass.

---

### Task 7: Run Scratch Staging And Payload Smoke

**Files:**
- Uses: `data/taxobench-cs/scripts/prepare_taxobench_cs_inputs.py`
- Uses: `data/taxobench-cs/scripts/generate_taxobench_cs_payloads.py`
- Uses: `data/taxobench-cs/scripts/validate_taxobench_cs_staging.py`

- [ ] **Step 1: Create scratch staging for two papers**

Run:

```bash
rm -rf .local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/smoke/staging
PYTHONDONTWRITEBYTECODE=1 python3 data/taxobench-cs/scripts/prepare_taxobench_cs_inputs.py \
  --source-root /Users/xjp/Desktop/TaxoBench-CS \
  --output-root .local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/smoke/staging \
  --write-staging \
  --limit 2 \
  --force
```

Expected:

- exit code `0`
- scratch manifest has `2` rows
- scratch metadata and taxonomy files exist
- no files are written to `/Users/xjp/Desktop/TaxoBench-CS`

- [ ] **Step 2: Render four payloads for each smoke paper**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 data/taxobench-cs/scripts/generate_taxobench_cs_payloads.py \
  --staging-root .local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/smoke/staging \
  --output-root .local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/smoke/staging \
  --experiment-id 2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch \
  --limit 2 \
  --force
```

Expected:

- exit code `0`
- each of 2 papers has 4 payload files
- projection reports exist for both papers

- [ ] **Step 3: Validate scratch staging with payload requirement**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 data/taxobench-cs/scripts/validate_taxobench_cs_staging.py \
  --staging-root .local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/smoke/staging \
  --expect-papers 2 \
  --require-payloads \
  --report .local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/smoke/validate_payloads_limit2.json
```

Expected:

- exit code `0`
- report confirms `2` ready papers
- report confirms `8` payload files
- report confirms zero prompt-hygiene violations

---

### Task 8: Implement Render-Only Experiment Request Builder

**Files:**
- Create: `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prototype/run_taxobench_cs_outline_batch.py`
- Modify only if needed: `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prompts/taxobench_cs_outline_payload_prompt_template.txt`

- [ ] **Step 1: Add render-only CLI**

The CLI must accept:

```text
--staging-root PATH
--output-root PATH
--render-only
--write-batch-input
--limit N
--force
```

Fail closed unless `--render-only` is present. Do not implement live submission in this task.

- [ ] **Step 2: Render generated-arm requests**

For each selected paper, render exactly five generated arms:

```text
baseline_no_taxonomy
flat_concepts
random_hierarchy
tree_only_guarded
tree_with_papers
```

For `--limit 2`, write exactly `10` JSONL request rows.

- [ ] **Step 3: Keep `human_written` out of generation requests**

The request builder may write a manifest row for `human_written` reference identity, but it must not create an LLM request for that arm.

---

### Task 9: Run Full Non-LLM Smoke Test

**Files:**
- Uses all files from Tasks 4 through 8.

- [ ] **Step 1: Render request JSONL into `.local`**

Run:

```bash
rm -rf .local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/smoke/render
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prototype/run_taxobench_cs_outline_batch.py \
  --staging-root .local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/smoke/staging \
  --output-root .local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/smoke/render \
  --render-only \
  --write-batch-input \
  --limit 2 \
  --force
```

Expected:

- exit code `0`
- `batch_input.jsonl` exists under `.local`
- row count is `10`
- no network call is made
- no file is written under `results/`

- [ ] **Step 2: Verify request count**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
path = Path(".local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/smoke/render/batch_input.jsonl")
rows = path.read_text(encoding="utf-8").splitlines()
print(len(rows))
raise SystemExit(0 if len(rows) == 10 else 1)
PY
```

Expected output:

```text
10
```

- [ ] **Step 3: Run prompt hygiene scan**

Run:

```bash
rg -n "Target Paper Abstract:|with_abstract|no_abstract|structural_complete_guarded|metadata_|/Users/xjp|TaxoBench-CS" \
  .local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/smoke/render \
  -g 'prompt.txt' -g 'batch_input.jsonl'
```

Expected: no matches and exit code `1` from `rg`.

- [ ] **Step 4: Run full smoke test command bundle**

Run all smoke commands from Tasks 7 and 9 in a clean `.local` smoke directory. Record command output paths in:

```text
.local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/smoke/SMOKE_TEST_LOG.md
```

Expected final state:

- adapter dry-run report exists
- scratch staging report exists
- payload validation report exists
- render-only batch input exists
- request count is `10`
- hygiene scan has no matches

---

### Task 10: Promote From Scratch Smoke To Canonical Staging Only After Approval

**Files:**
- Writes after approval: `data/taxobench-cs/manifests/input_manifest.jsonl`
- Writes after approval: `data/taxobench-cs/manifests/source_provenance.json`
- Writes after approval: `data/taxobench-cs/metadata/papers.jsonl`
- Writes after approval: `data/taxobench-cs/metadata/ref_meta.jsonl`
- Writes after approval: `data/taxobench-cs/taxonomies/*.taxonomy_source.json`
- Writes after approval: `data/taxobench-cs/taxonomies/*.taxonomy_membership.jsonl`
- Writes after approval: `data/taxobench-cs/payload_sources/*.payload_source.json`
- Writes after approval: `data/taxobench-cs/payloads/*/*.txt`
- Writes after approval: `data/taxobench-cs/projection_reports/*.projection_report.json`

- [ ] **Step 1: Stop and report smoke evidence**

Before canonical writes, report:

- exact command lines run
- source paper count
- scratch staged paper count
- scratch payload count
- unresolved taxonomy leaf count
- prompt hygiene result
- row count for render-only JSONL

- [ ] **Step 2: Wait for explicit user approval**

Required approval phrase in chat:

```text
可以寫入 canonical data/taxobench-cs staging
```

- [ ] **Step 3: Write canonical staging**

After approval, rerun staging and payload generation with:

```text
--output-root data/taxobench-cs
```

- [ ] **Step 4: Validate canonical staging**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 data/taxobench-cs/scripts/validate_taxobench_cs_staging.py \
  --staging-root data/taxobench-cs \
  --expect-papers 156 \
  --require-payloads \
  --report data/taxobench-cs/manifests/readiness_report.json
```

Expected:

- exit code `0`
- `156` ready papers if source count remains unchanged
- `624` payload files if all four payloads are generated for all 156 papers
- zero prompt-hygiene violations

---

### Task 11: Update Experiment Status Without Running Models

**Files:**
- Modify: `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/spec.md`
- Modify: `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/runbook.md`
- Modify: `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/promotion_checklist.md`
- Modify: `data/taxobench-cs/README.md`

- [ ] **Step 1: Update status after canonical staging passes**

Use status:

```text
payload_contract_corrected_no_model_runs
```

- [ ] **Step 2: Check off only verified promotion items**

Only mark items that have command evidence from this task list. Leave live generation, evaluation, and Google Sheet items unchecked.

- [ ] **Step 3: Final verification commands**

Run:

```bash
git status --short -- data/taxobench-cs experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch
find data/taxobench-cs/payloads -name '*.txt' -type f | wc -l
find data/taxobench-cs/reference_outlines -name '*.outline.json' -type f | wc -l
```

Expected if canonical staging was approved and completed:

```text
624
156
```

---

### Task 12: Resolve Prompt-Template Comparability Before Any Model Run

**Files:**
- Inspect: `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prototype/run_taxobench_cs_outline_batch.py`
- Inspect: `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prompts/taxobench_cs_outline_payload_prompt_template.txt`
- Modify if needed: `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prototype/run_taxobench_cs_outline_batch.py`
- Modify if needed: `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prompts/taxobench_cs_outline_payload_prompt_template.txt`
- Modify if needed: prompt/rendering tests under `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/tests/`
- Modify if needed: `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/spec.md`, `runbook.md`, and `promotion_checklist.md`

- [x] **Step 1: Treat the previous taxonomy prompt template as a design risk**

Resolved risk:

- `baseline_no_taxonomy` uses the faithful released MEOW user prompt from `codex_meow_outline_blind_lib.USER_PROMPT_TEMPLATE`.
- taxonomy payload arms use the experiment-local `taxobench_cs_outline_payload_prompt_template.txt` instead of the same faithful MEOW user prompt.
- taxonomy arms also expose arm framing through fields such as `Payload mode:` and `Taxonomy-derived payload:`.

Before the fix, a live run would have compared:

```text
faithful MEOW baseline
vs
experiment-local taxonomy prompt wording + taxonomy payload
```

That would not have cleanly isolated the effect of taxonomy payload presence or
payload representation.

- [x] **Step 2: Decide and document the prompt contract**

Chosen contract, documented in `spec.md` and `runbook.md`:

- main comparison: use the released MEOW baseline prompt as the base skeleton
  and append one neutral auxiliary taxonomy block after the original
  `References:` field for taxonomy arms
- the neutral block may describe what the payload is, but must not tell the model
  how to use it
- baseline remains the released MEOW prompt with no taxonomy block
- taxonomy arms must not expose `Payload mode:` or arm labels in prompt text
- instruction-guided taxonomy is not part of the current main matrix

The runner/template implementation and tests now enforce this decision in
render-only mode.

- [x] **Step 3: Remove or justify arm-identity leakage**

For payload-only comparisons, avoid prompt-visible labels that tell the model which condition it is in, such as:

```text
Payload mode:
tree_with_papers
flat_concepts
random_hierarchy
tree_only_guarded
```

The current render-only runner removes these labels from prompt-visible model
input.

- [x] **Step 4: Preserve the MEOW input contract**

Any replacement prompt contract must preserve:

- target paper title is prompt-visible
- reference metadata is prompt-visible
- target paper abstract is not prompt-visible
- local paths, adapter metadata, downloader provenance, and Google metadata are not prompt-visible
- output format requirements are as comparable as possible across arms

- [x] **Step 5: Add render-only prompt-diff checks**

Add or update tests/smoke checks so render-only prompts prove:

- baseline and taxonomy arms use the intended shared envelope or explicitly documented divergent envelope
- taxonomy arms differ only in the allowed payload block when using the preferred clean comparison
- no `Payload mode:` or arm-id leak appears
- prompt hygiene still has no target abstract, local paths, or adapter/debug metadata

- [x] **Step 6: Re-run non-LLM verification only**

After prompt-contract changes, rerun the local render-only smoke and hygiene checks. This task does not approve OpenAI generation, Batch submission, judging, result writes, or Google Sheet updates.

Verified on 2026-06-02:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest \
  experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/tests \
  -q

PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prototype/run_taxobench_cs_outline_batch.py \
  --staging-root data/taxobench-cs \
  --output-root .local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/smoke/prompt_contract_fix \
  --render-only \
  --write-batch-input \
  --limit 2 \
  --force
```

Results: `10` pytest tests passed, render-only smoke produced `10` request rows
for `2` papers, and the prompt hygiene scan found no wrapper, arm-label, target
abstract, local path, or instruction-guided taxonomy leakage.

---

### Task 13: Correct Taxonomy Payload Visibility And Regenerate Payloads

**Files:**
- Modify: `data/taxobench-cs/scripts/generate_taxobench_cs_payloads.py`
- Modify: `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/tests/test_taxobench_cs_payload_rendering.py`
- Modify if needed: `data/taxobench-cs/FORMAT.md`, `data/taxobench-cs/README.md`, `data/taxobench-cs/payloads/README.md`, and experiment docs under `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/docs/`
- Regenerate after tests pass: `data/taxobench-cs/payloads/*/*.txt`
- Regenerate after tests pass if contents change: `data/taxobench-cs/projection_reports/*.projection_report.json`

- [x] **Step 1: Record the source-schema distinction**

TaxoBench `taxo_tree` leaf keys such as:

```text
f37e1b62a767a307c046404ca96bc140b3e68cb5
87f40e6f3022adbc1f1905e3e506abad05a9964f
df2b0e26d0599ce3e70df8a9da02e51594e0e992
```

are Semantic Scholar `paperId` values used as taxonomy membership/reference-paper
identifiers. They are not taxonomy concept labels, arXiv ids, outline citation
keys, or human-readable paper titles.

- [x] **Step 2: Fix `tree_only_guarded`**

`tree_only_guarded` must render only taxonomy/concept structure. It must not
render the 40-character `paperId` membership leaves.

For example, a subtree shaped like:

```json
{
  "Contextual?": {
    "Non-Contextual": {
      "f37e1b62a767a307c046404ca96bc140b3e68cb5": {}
    }
  }
}
```

should render as concept structure only:

```text
- Contextual?
  - Non-Contextual
```

It must not render:

```text
- f37e1b62a767a307c046404ca96bc140b3e68cb5
```

- [x] **Step 3: Fix `tree_with_papers`**

`tree_with_papers` must also be regenerated. The prompt-visible leaf should be
title-only for readability and to avoid exposing join keys or over-rich metadata.

Allowed at paper leaves:

```text
- GloVe: Global Vectors for Word Representation
```

Forbidden at paper leaves:

```text
- f37e1b62a767a307c046404ca96bc140b3e68cb5
- title: GloVe: Global Vectors for Word Representation
- year: 2014
- ids: DOI=10.3115/v1/D14-1162; DBLP=conf/emnlp/PenningtonSM14
- abstract: ...
```

- [x] **Step 4: Audit `flat_concepts` and `random_hierarchy`**

Chosen policy: remove descendant paper evidence entirely for pure concept-only
variants. `flat_concepts` and `random_hierarchy` render concept labels only.

- [x] **Step 5: Add payload visibility tests**

Tests must reject:

- any 40-character hex `paperId` in `tree_only_guarded`
- any `paperId`, `year:`, `ids:`, `DOI=`, `ArXiv=`, `DBLP=`, `CorpusId=`, `MAG=`, or `abstract` field in `tree_with_papers`
- any raw `paperId` or `papers:` descendant evidence field in `flat_concepts` or `random_hierarchy`

Tests must confirm:

- taxonomy/concept labels remain visible
- title-only paper leaves remain visible in `tree_with_papers`
- no generated definitions are introduced

- [x] **Step 6: Regenerate and revalidate canonical payloads**

After renderer/tests/docs are corrected, regenerate payloads under
`data/taxobench-cs/payloads/` and rerun staging validation. The readiness report
must explicitly record that prompt-visible taxonomy payloads no longer contain
raw Semantic Scholar `paperId` leaves in the arms where they are forbidden.

This task does not approve OpenAI generation, Batch submission, judging, result
writes, or Google Sheet updates.

---

### Task 14: Record Instruction-Guided Taxonomy As A Separate Ablation

**Files:**
- Modify: `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/TASKS.md`
- Modify: `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/spec.md`
- Modify: `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/runbook.md`
- Modify: `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/promotion_checklist.md`
- Modify if needed: `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/docs/arm_matrix.md`

- [x] **Step 1: Define the distinction**

Neutral taxonomy append means the prompt only identifies the auxiliary block:

```text
In addition to the references above, the following is an auxiliary taxonomy
representation of the same reference set:
{taxonomy_payload}
```

Instruction-guided taxonomy means the prompt also tells the model how to use the
taxonomy, for example as an organizational signal. That is a prompt-steering
treatment, not just a taxonomy-content treatment.

- [x] **Step 2: Record the reviewer-facing decision**

For the current main experiment, do not add instruction guidance to
`tree_only_guarded` or `tree_with_papers`. A reviewer could otherwise argue that
any improvement comes from treatment-only instructions rather than from the
taxonomy payload representation.

- [x] **Step 3: Specify how to add it if reopened**

If instruction-guided taxonomy is added in this experiment, it must be added as
explicit separate arms, not by rewriting the existing neutral arms. The clean
crossed design is:

```text
tree_only_guarded_neutral
tree_only_guarded_guided
tree_with_papers_neutral
tree_with_papers_guided
```

If budget only permits one guided smoke, `tree_only_guarded_guided` is the
cleaner first ablation because it avoids mixing instruction guidance with the
extra title-leaf evidence in `tree_with_papers`.

- [x] **Step 4: Keep current request counts unchanged**

Because guided arms are deferred, the current main matrix remains:

```text
156 papers * 5 generated arms = 780 generation requests
156 papers * 6 arms including human_written = 936 comparison rows
```

This task does not implement guided arms, approve OpenAI generation, Batch
submission, judging, result writes, or Google Sheet updates.

---

### Task 15: Correct Judge Transport To OpenAI Batch API Before Any Live Run

**Files:**
- Modify: `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/config.yaml`
- Modify: `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/spec.md`
- Modify: `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/runbook.md`
- Modify: `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/promotion_checklist.md`
- Modify: `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/docs/settings_lineage.md`
- Modify: `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prototype/README.md`
- Modify if needed: `docs/guides/meow_evaluation_assets.md`
- Create: `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prototype/evaluate_taxobench_cs_outlines_batch.py`
- Create or modify if useful: shared OpenAI Batch helper code under `scripts/`
- Create or modify: evaluator tests under `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/tests/`

- [x] **Step 1: Replace the planned judge contract**

Change the planned evaluator contract from:

```text
judge backend: codex
judge model: gpt-5.5
judge reasoning effort: high
```

to a transport-explicit contract:

```text
judge transport: OpenAI Batch API
judge endpoint: /v1/responses unless implementation proves /v1/chat/completions is safer
judge model: gpt-5.5 unless the user explicitly changes it
judge reasoning effort: high
completion window: 24h
```

Keep the distinction clear:

- `generation transport` is OpenAI Batch API for outline generation.
- `judge transport` is OpenAI Batch API for the 6D evaluator.
- The judge prompt remains the repo-local upstream 6D judge prompt unless a
  separate judge-prompt task changes it.

- [x] **Step 2: Implement evaluator-level Batch lifecycle**

Do not treat OpenAI Batch as just another immediate `run_judge_attempt()`
backend. The current direct judge API returns one raw response per call, while
Batch judge requires:

1. render judge requests to JSONL
2. upload with `purpose="batch"`
3. create Batch job
4. poll/retrieve job metadata
5. download output/error files
6. parse raw judge text back into `.eval.json` and `.eval.debug.json`
7. rebuild aggregate summaries

Reuse existing parsing utilities where possible:

- `build_judge_messages`
- `parse_judge_response`
- `ensure_outline_list`
- `render_outline_text`
- `compute_structural_distance_debug`

Implementation note: Task 15 implements the non-mutating lifecycle stages that
can be verified before approval: render judge request JSONL, parse downloaded or
fixture Batch output, write local eval/debug artifacts under the chosen output
root, and rebuild an aggregate summary. Live API stages, including upload,
Batch creation, polling, and live download, remain fail-closed until Task 16
gets explicit user approval.

- [x] **Step 3: Add TaxoBench-CS evaluation target builder**

The evaluator must support these target types:

- generated arms:
  - `baseline_no_taxonomy`
  - `flat_concepts`
  - `random_hierarchy`
  - `tree_only_guarded`
  - `tree_with_papers`
- calibration/reference arm:
  - `human_written`

For generated arms:

```text
source outline = generated output outline
reference outline = data/taxobench-cs/reference_outlines/<paper_id>.outline.json
```

For `human_written` calibration:

```text
source outline = reference outline
reference outline = same reference outline
```

Expected `human_written` structural distance: `0`.

- [x] **Step 4: Add render-only and parser tests**

Add tests that prove:

- judge Batch JSONL has stable `custom_id` values that map back to
  `paper_id` and `arm`
- Batch request body contains the 6D judge prompt and rendered outline
- prompt-visible judge input contains no local absolute paths or adapter debug
  fields
- `human_written` self-eval uses the same outline as source and reference
- structural distance for `human_written` is exactly `0`
- fixture Batch output can be parsed into the same score keys used by the
  existing evaluator

- [x] **Step 5: Run offline judge Batch smoke, no API**

Render but do not submit judge requests for three `human_written` targets:

```text
short outline: 2309.06794
median-sized outline: choose one of 2311.09008, 2404.04925, 2404.18231, 2406.10885
long outline: 2212.10535
```

Expected:

- exactly `3` judge Batch request rows
- every request is for `human_written`
- every precomputed structural distance is `0`
- no OpenAI API call is made
- no `results/` write is made unless the user has explicitly approved the
  output location

- [x] **Step 6: Record cost estimate before asking for live approval**

Record token estimates in `runbook.md` or a local smoke report before any live
judge job. Current local estimate from staged human-written outlines:

```text
human_written judge input mean: about 2.8k-2.9k tokens/request
human_written full calibration: 156 requests, about 0.44M input tokens
five generated arms: 780 requests, about 2.2M input tokens by human-outline proxy
all six comparison rows: 936 requests, about 2.6M input tokens by human-outline proxy
```

Visible judge output from prior Tree50-style artifacts is about `660`
tokens/request, but high-reasoning judge runs may bill hidden reasoning tokens
as output tokens. Use current OpenAI pricing at run time, not stale local notes.

This task does not approve live generation, Batch submission, judging, result
writes, or Google Sheet updates.

---

### Task 16: Live Run Approval Gates

This task is the boundary between local preparation and live spending. Do not
check any item here without fresh command evidence.

- [x] **Step 1: Re-run full non-LLM generation render smoke**

Run the current render-only generation smoke against canonical staging:

- all prompt-template comparability checks from Task 12 pass
- all payload visibility checks from Task 13 pass
- request count for a two-paper smoke is `10`
- no `human_written` generation request exists

- [x] **Step 2: Re-run offline judge Batch smoke**

Run Task 15 Step 5 after the latest evaluator code and docs are in place.

- [x] **Step 3: Ask for explicit live judge-smoke approval**

The first live API call should be a tiny OpenAI Batch judge smoke, not the full
generation run:

```text
3 papers * human_written only = 3 judge requests
```

The goal is to verify Batch submission, collection, response parsing, artifact
writing, and score shape before spending on generated-arm judging.

- [x] **Step 4: Run and collect live `human_written` judge smoke after approval**

Expected:

- Batch status is `completed`
- output rows equal input rows
- every row has all six judge score keys
- `human_written` structural distance remains `0`
- score values are compared against the previous judge path only as a sanity
  check, not as an exact-equality requirement

Verified 2026-06-02 after user approval:

- Batch id: `batch_6a1ddfa907a48190b2c71010e2a81c22`
- status: `completed`
- request counts: `3 completed / 0 failed / 3 total`
- output rows parsed: `3`
- all rows have the six repo-local judge score keys
- `human_written` structural distance: `0.0` for all three rows
- token usage: `8643` input tokens, `6662` output tokens
- local artifact root:
  `.local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/judge_human_written_smoke`
- no full generation, full judging, `results/` write, or Google Sheet update was
  performed

- [x] **Step 5: Ask for explicit full live generation approval**

Only after the live judge smoke passes, ask for approval to submit:

```text
156 papers * 5 generated arms = 780 generation requests
```

Approved by user on 2026-06-02 for generation only. Full Batch judge
evaluation remains explicitly deferred until the user reviews the result.

- [ ] **Step 6: Run full live generation, then full Batch judge evaluation**

After generation outputs exist and are validated, run:

```text
156 papers * 6 arms including human_written = 936 comparison rows
```

Then produce aggregate summaries and a Google-Sheet-ready table package. Native
Google Sheet creation/update still requires separate explicit approval.

Generation attempt evidence from 2026-06-02:

- Batch id: `batch_6a1de4a4eb788190afc5e88b63d2067f`
- request counts: `780 completed / 0 failed / 780 total`
- output rows downloaded: `780`
- output artifact root:
  `.local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/full_generation_live_20260602`
- generated-root for later judge input:
  `.local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/full_generation_live_20260602/generated_outlines`
- normalized outline success after offline parser salvage: `388 / 780`
- remaining unusable rows: `392 / 780`, all due to Responses API
  `status=incomplete` with `incomplete_details.reason=max_output_tokens`
- normalized outline success by arm:
  - `baseline_no_taxonomy`: `82 / 156`
  - `flat_concepts`: `72 / 156`
  - `random_hierarchy`: `75 / 156`
  - `tree_only_guarded`: `86 / 156`
  - `tree_with_papers`: `73 / 156`
- actual usage recorded by `api_usage_cost_summary.json`: `27,251,216`
  input tokens, `19,325,056` cached input tokens, `23,544,421` output
  tokens, `22,797,559` reasoning output tokens
- approximate Batch cost at GPT-5 nano rates and 50% Batch discount:
  `$4.95535084`
- full Batch judge evaluation was not run

Generation retry evidence from 2026-06-02:

- only the `392` unusable rows from the first generation Batch were retried;
  the original `388` usable rows were not resubmitted
- retry Batch id: `batch_6a1e5107792c8190b9b32eee90267d9e`
- retry request counts: `392 completed / 0 failed / 392 total`
- retry output rows downloaded and parsed: `392`
- retry normalized outline success: `392 / 392`
- retry artifact root:
  `.local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/full_generation_retry_unusable_20260602_65536`
- retry generated-root target:
  `.local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/full_generation_live_20260602/generated_outlines`
- retry overlap with original usable custom_ids: `0`
- combined normalized outline count: `780 / 780`
- combined normalized outline success by arm:
  - `baseline_no_taxonomy`: `156 / 156`
  - `flat_concepts`: `156 / 156`
  - `random_hierarchy`: `156 / 156`
  - `tree_only_guarded`: `156 / 156`
  - `tree_with_papers`: `156 / 156`
- retry usage recorded by `api_usage_cost_summary.json`: `12,364,012`
  input tokens, `6,785,792` cached input tokens, `13,648,970` output tokens,
  `12,913,866` reasoning output tokens
- retry approximate Batch cost: `$2.88621398`
- combined generation approximate Batch cost: `$7.84156482`
- full Batch judge evaluation was not run

This still does not complete Step 6 because full Batch judge evaluation remains
explicitly deferred. The next decision is whether to run full generated-arm
judge evaluation over the now-complete generated-root.

---

## Smoke Test Definition

The first acceptable smoke test is entirely local and non-LLM:

1. Adapter dry-run for `--limit 2`, writing only `.local/.../adapter_dry_run_limit2.json`.
2. Scratch staging for `--limit 2` under `.local/.../smoke/staging`.
3. Payload rendering for the same `2` papers, producing `8` payload files.
4. Staging validation with `--require-payloads`.
5. Render-only request build under `.local/.../smoke/render`.
6. Request count check: `10` generated-arm rows for `2` papers.
7. Prompt hygiene scan: no target abstract axis, no local paths, no adapter metadata, no source workspace string.
8. Prompt comparability scan: no outer wrapper, no `Payload mode:`, no
   prompt-visible arm labels, and no instruction-guided taxonomy wording in the
   main arms.

Passing this smoke test was the prerequisite for canonical staging. Canonical
staging now exists, so the next required smoke is Task 15 Step 5: render-only
OpenAI Batch judge JSONL over `human_written` self-evaluation targets. Passing
that judge smoke is still not approval to run live generation.
