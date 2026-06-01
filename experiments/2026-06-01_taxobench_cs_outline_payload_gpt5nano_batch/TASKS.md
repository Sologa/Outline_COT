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
- No OpenAI generation, Batch submission, model output, judge output, or Google
  Sheet update exists for this experiment.

## Hard Guardrails

- Do not write into `/Users/xjp/Desktop/TaxoBench-CS`.
- Do not call OpenAI generation, Batch, or judge APIs.
- Do not update Google Sheets.
- Do not write model-run artifacts into `results/`.
- Smoke-test scratch must go under `.local/experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/`.
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
- Keep `experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prototype/run_taxobench_cs_outline_batch.py`, `prompts/taxobench_cs_outline_payload_prompt_template.txt`, and prompt-contract tests aligned with Task 12 before any model run.
- Modify `data/taxobench-cs/scripts/generate_taxobench_cs_payloads.py`, payload rendering tests, docs, and regenerated payload files before any model run if Task 13 confirms prompt-visible taxonomy payloads still expose `paperId` strings or over-rich leaf metadata.
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

Passing this smoke test is a prerequisite for asking approval to write canonical staging under `data/taxobench-cs/`. It is not approval to run live generation.
