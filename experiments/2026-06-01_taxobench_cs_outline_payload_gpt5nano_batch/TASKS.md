# TaxoBench-CS Adapter And Smoke Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the TaxoBench-CS staged input package, deterministic taxonomy payloads, and non-LLM smoke tests needed before any generation run can be approved.

**Architecture:** Dataset-specific normalization lives under `data/taxobench-cs/scripts/` and writes reusable staged inputs under `data/taxobench-cs/`. Experiment prototype code under this directory only consumes staged inputs and may render requests in dry-run or render-only mode. Smoke tests write scratch artifacts under `.local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/` and must never submit model jobs.

**Tech Stack:** Python 3 standard library, JSON/JSONL, pytest, ripgrep, existing Outline_COT prompt/runtime helpers where they match the `title_ref_meta_no_target_abstract` contract.

---

## Current State

- `data/taxobench-cs/reference_outlines/*.outline.json` exists for `156` papers.
- `data/taxobench-cs/scripts/` contains only documentation.
- `data/taxobench-cs/payloads/` contains only documentation.
- `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prototype/` contains only documentation.
- No taxonomy/ref metadata adapter, payload renderer, validation script, render-only runner, Batch input, model output, judge output, or Google Sheet update exists for this experiment.

## Hard Guardrails

- Do not write into `/Users/xjp/Desktop/TaxoBench-CS`.
- Do not call OpenAI generation, Batch, or judge APIs.
- Do not update Google Sheets.
- Do not write model-run artifacts into `results/`.
- Smoke-test scratch must go under `.local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/`.
- Prompt-visible fields must not include local absolute paths, adapter debug fields, downloader provenance, Google metadata, or target paper abstracts.

## Files To Create Or Modify

- Create `data/taxobench-cs/scripts/prepare_taxobench_cs_inputs.py`: read upstream TaxoBench-CS, validate records, normalize metadata/taxonomy, build manifest and payload sources.
- Create `data/taxobench-cs/scripts/generate_taxobench_cs_payloads.py`: render deterministic `tree_only_guarded`, `tree_with_papers`, `flat_concepts`, and `random_hierarchy` payloads from staged inputs.
- Create `data/taxobench-cs/scripts/validate_taxobench_cs_staging.py`: verify staged counts, joins, prompt hygiene, payload existence, random seed stability, and manifest readiness.
- Create `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prototype/run_taxobench_cs_outline_batch.py`: render request JSONL from staged inputs in render-only mode; keep live submission absent or fail-closed.
- Create `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/tests/conftest.py`: load adapter scripts from the hyphenated `data/taxobench-cs/scripts/` path for pytest.
- Create `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/tests/test_taxobench_cs_adapter_contract.py`: unit/contract tests for parser, normalizer, membership preservation, and prompt hygiene.
- Create `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/tests/test_taxobench_cs_payload_rendering.py`: deterministic payload renderer tests, including `tree_with_papers`.
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

- [ ] **Step 1: Write renderer tests**

Tests must verify:

- `tree_only_guarded` preserves taxonomy labels and paper identity leaves
- `tree_with_papers` includes paper id, title, year, and stable external ids
- `tree_with_papers` does not include abstracts by default
- `flat_concepts` removes parent-child nesting while preserving concept labels
- `random_hierarchy` is deterministic for the same experiment id and paper id
- no renderer inserts generated definitions

- [ ] **Step 2: Implement payload rendering CLI**

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

- [ ] **Step 3: Run renderer tests**

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
data_staged_payloads_ready_no_model_runs
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

## Smoke Test Definition

The first acceptable smoke test is entirely local and non-LLM:

1. Adapter dry-run for `--limit 2`, writing only `.local/.../adapter_dry_run_limit2.json`.
2. Scratch staging for `--limit 2` under `.local/.../smoke/staging`.
3. Payload rendering for the same `2` papers, producing `8` payload files.
4. Staging validation with `--require-payloads`.
5. Render-only request build under `.local/.../smoke/render`.
6. Request count check: `10` generated-arm rows for `2` papers.
7. Prompt hygiene scan: no target abstract axis, no local paths, no adapter metadata, no source workspace string.

Passing this smoke test is a prerequisite for asking approval to write canonical staging under `data/taxobench-cs/`. It is not approval to run live generation.
