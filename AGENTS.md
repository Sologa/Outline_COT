# Outline_COT Repo Guide

This file is the repo-level guide for future conversations and agents working in this repository.

Read this file before inferring workflow from scattered prompt files, helper HTML, or older notes.

## 0. Default Codex Operating Guardrails
These guardrails are the default behavior for Codex work in this tree. Keep them prominent and apply them unless a direct user, system, developer, or more specific repository rule says otherwise.

**Think before coding.** Do not silently assume missing requirements. State important assumptions, surface ambiguity, present tradeoffs when they matter, and stop to ask when uncertainty could send the work in the wrong direction.

**Simplicity first.** Use the minimum change that solves the requested problem. Do not add speculative features, unnecessary abstractions, new configurability, or defensive handling for scenarios with no evidence they matter.

**Surgical changes.** Touch only files and lines required for the task. Match existing style. Do not refactor, reformat, rename, or clean adjacent code opportunistically. Remove only dead imports, variables, or code that your own change made unused.

**Goal-driven execution.** Convert vague requests into concrete success criteria before acting. Prefer tests, builds, focused repro steps, file comparisons, or documented checks over confidence. Do not claim a change is complete without fresh verification evidence.

For trivial, low-risk one-line work, keep the process lightweight, but keep the same bias toward explicit assumptions, small diffs, and verified outcomes.

## 0.1 Experiment Data Ledger

The official stable experiment ledger for this repository is the native Google Sheet:

- [Outline_COT 實驗總表 2026-05-18](https://docs.google.com/spreadsheets/d/1qoyrAI2NCos6RXHVcK5cbOrH0h8ONDCqs7Vy6aLfxVM/edit?gid=389765809#gid=389765809)

All stable experiment settings, artifact descriptions, and final experiment results should be preserved in this sheet, not only in chat, ad hoc notes, or local-only summaries.

Staging rule for fresh or unstable experiments:

- Do not write newly produced, unstable, provisional, or still-being-debugged results directly into the official stable ledger.
- First create a separate new Google Sheet in Google Drive for the provisional experiment data.
- Record and report the provisional sheet's exact name and URL so later agents can find it.
- Keep using that provisional sheet until the result is stable and both the user and Codex agree it is ready for formal recordkeeping.
- Only after that explicit agreement should the provisional data be merged into the official stable ledger above.

## 1. Repo purpose

This repository is primarily used to inspect, reconstruct, compare, and extract:

- MEOW-style literature review outlines
- outline-generation prompts
- CoT / reasoning prompts tied to outline generation
- prompt provenance across paper, repo code, and dataset artifacts

Current working artifacts include:

- `refs/<paper_id>/outline.json`
- `results/<paper_id>/...`
- `prompts/*.txt`
- `docs/meow_prompt_copy_helper.html`
- `scripts/extract_meow_outline.py`

## 2. Working assumptions

- Treat this repo as a prompt-analysis and outline-analysis workspace, not a prompt-packaging repo by default.
- Distinguish carefully between:
  - confirmed prompt text from released code
  - auxiliary prompt text present in repo but not clearly on the main runtime path
  - inferred or reconstructed prompts
- When discussing a prompt, preserve provenance clearly instead of merging confirmed and inferred versions.

## 3. `prompts/` directory contract

The `prompts/` directory contains plain-text prompt files intended to be read directly and sent to an LLM API.

Treat these files as prompt payloads, not as prose documentation.

Operational rules:

- The normal usage pattern is: read file content -> optionally replace explicit placeholders -> send directly to the model.
- Do not treat `prompts/*.txt` as notes, drafts, or summaries unless a file explicitly says otherwise.
- Do not rewrite, paraphrase, translate, or "clean up" these prompt files before sending them to the model unless the user explicitly asks for that.
- In the normal path, the only allowed transformation is replacing explicit placeholders such as `{Var}` with the corresponding runtime values.
- If a prompt file has no explicit placeholder, feed it as-is.

Current file roles:

- `prompts/meow_outline_extraction_system.txt`
  - System prompt for deterministic MEOW-style outline extraction from a paper source.
  - Sets parser-like behavior and forbids invented sections, numbering, or references.
- `prompts/meow_outline_extraction_user.txt`
  - User prompt template paired with the extraction system prompt.
  - Supplies the extraction task, output schema, and paper-specific inputs.
  - Current runtime placeholders: `{title}`, `{references}`, `{paper_source}`.
- `prompts/meow_outline_full_review_system.txt`
  - System prompt for full-audit review of stored outline extraction outputs.
  - Instructs the model to behave as a careful reviewer/auditor rather than as a creative writer.
- `prompts/meow_outline_full_review_user.txt`
  - User prompt for the full-review workflow over local `refs/` papers and their stored `outline.json`.
  - Defines the workspace context, review scope, correction rules, and required report format.
  - This file currently has no runtime placeholder and should normally be sent as-is.
- `prompts/meow_llm_judge_6d_source_system.txt`
  - Source capture of the upstream `LLM-as-a-Judge` system prompt from `Survey-Outline-Evaluation-Benckmark/scripts/evaluate_llm.py`.
  - This is a provenance artifact, not the default direct-payload prompt for this repo.
- `prompts/meow_llm_judge_6d_source_user.txt`
  - Source capture of the upstream 6-dimension `LLM-as-a-Judge` user prompt from `Survey-Outline-Evaluation-Benckmark/scripts/evaluate_llm.py`.
  - This file preserves upstream wording and only replaces runtime inserts with `{topic}` and `{outline}` placeholders.

Short form:

- `prompts/` files are direct LLM API inputs.
- Default handling is raw read plus optional `{Var}` substitution only.
- No extra rewriting layer by default.
- Exception: `prompts/meow_llm_judge_6d_source_*.txt` are source/provenance captures. Do not assume they are the paper's exact metric prompts, and do not silently collapse them into the normal payload contract.

## 4. User output preference

The default preference in this repository is:

- Do not output prompts as files unless the user explicitly asks for a file.
- When the user asks for a prompt, prompt template, system prompt, or user prompt, output the prompt directly in the chat so it can be copied immediately.
- Prefer a copy-ready fenced code block for prompt delivery.
- Do not create helper `.txt`, `.json`, `.md`, or `.html` files just to make prompts easier to copy unless the user explicitly requests that format.
- Respond in Chinese by default.
- Keep proper nouns, model names, paper titles, API names, code identifiers, and other technical terms in their original form when translation would reduce precision.

Short form:

- Prompt requests: reply inline.
- File output: only when explicitly requested.
- Language: Chinese by default, except proper nouns and technical terms.

## 5. Editing preference

- If the task is prompt-facing, optimize for direct copy/paste usability first.
- If a saved artifact would change the workflow from "copy now" to "open file and copy", do not do it unless the user asked for that tradeoff.

## 6. Current intent to preserve

For this repo, assume the user is often trying to:

- understand what the MEOW pipeline is actually doing
- compare paper claims against released code or dataset behavior
- recover faithful prompt text
- inspect outline structure examples per paper

Support that workflow with concise explanations and provenance-aware prompt output.

## 7. `refs/` vs `results/`

Treat `refs/` and `results/` as different classes of artifacts. Do not silently mix them.

- `refs/<paper_id>/`
  - reference-side artifacts
  - paper-specific source materials
  - human / gold outline files such as `outline.json`
  - reconstruction inputs such as `meow_reconstructed_blind.json`
- `results/<paper_id>/`
  - experiment outputs
  - model-generated outlines
  - run-specific evaluation results
  - anything that can have multiple settings / reruns / variants

Operational rules:

- Do not treat `refs/` as the default destination for experimental outputs.
- If the same paper can have multiple runs, prefer `results/<paper_id>/<run_name>/...`.
- If a user points to a concrete file under `results/`, preserve that path instead of copying the artifact into `refs/`.
- `refs/<paper_id>/outline.json` remains the default reference outline unless the user explicitly supplies another reference path.
- If a workflow needs both a model output and a gold outline:
  - read the model output from `results/` by default
  - read the gold outline from `refs/` by default

Short form:

- `refs/` = references and stable paper-side artifacts.
- `results/` = experimental outputs and run-specific evaluations.

## 8. Blind Outline Generation and Evaluation Contract

Current blind-outline workflow is `results-first`.

Generation:

- [scripts/run_codex_meow_outline_blind.sh](/Users/xjp/Desktop/Outline_COT/scripts/run_codex_meow_outline_blind.sh)
- Default output root is `results/`.
- If `--run-name NAME` is supplied, write to:
  - `results/<paper_id>/<run_name>/chatgpt_meow_outline_blind.json`
- If `--run-name` is omitted, legacy flat output remains:
  - `results/<paper_id>/chatgpt_meow_outline_blind.json`

Evaluation:

- [scripts/evaluate_chatgpt_meow_blind_batch.py](/Users/xjp/Desktop/Outline_COT/scripts/evaluate_chatgpt_meow_blind_batch.py)
- This script can now evaluate:
  - discovered blind outputs under `results/` or `refs/`
  - a single explicit model outline via `--source-outline`
- Important CLI knobs:
  - `--paper`
  - `--source-outline`
  - `--reference-outline`
  - `--output-dir`
  - `--summary-path`
  - `--run-name`
  - `--results-root`

Default path resolution:

- model outline:
  - `results/<paper_id>/<run_name>/chatgpt_meow_outline_blind.json` if `--run-name` is given
  - else `results/<paper_id>/chatgpt_meow_outline_blind.json` if present
  - else legacy fallback `refs/<paper_id>/chatgpt_meow_outline_blind.json`
- reference outline:
  - `refs/<paper_id>/outline.json` unless explicitly overridden
- eval outputs:
  - same directory as the run output, typically `results/<paper_id>/<run_name>/`
- summary:
  - `results/_summaries/<run_name>/chatgpt_meow_outline_blind.eval.summary.json` when `--run-name` is used

Operational rule:

- For new work, prefer namespaced runs under `results/<paper_id>/<run_name>/`.
- Do not introduce new evaluation outputs under `refs/` unless the user explicitly asks for a legacy layout.

## 9. MEOW evaluation assets

- `resources/Survey-Outline-Evaluation-Benckmark/` is a read-only vendor mirror of the upstream evaluation repo.
- Treat the vendored repo as source of truth for upstream evaluation code and prompt provenance. Do not rewrite it in place.
- Local promoted evaluation entrypoints live in `scripts/`, while provenance prompt captures live in `prompts/`.
- Read `docs/meow_evaluation_assets.md` before inferring metric coverage, runner behavior, or prompt status.
- Do not conflate:
  - the paper's 5-criterion `LLM-as-a-Judge`
  - the upstream repo's 6-dimension judge, which adds `Content - Academic Value`
- Treat `Structural Distance` as a programmatic metric path and `LLM-as-a-Judge` as a prompt-driven evaluation path.
- Treat ref-based reward helpers as auxiliary programmatic metrics unless the user explicitly asks about them; do not present them as the paper's main evaluation table metrics.

## 10. Execution and Orchestration Policy

For this repo, use a policy-first execution model. Choose among direct execution, native subagent delegation, and manual `codex exec` dispatch based on task shape rather than style preference.

### 10.1 Execution mode selection

- Prefer direct execution for short, tightly coupled, or critical-path work:
  - single-file edits
  - narrow bug fixes
  - one-off source checks
  - any task where the next step immediately depends on the answer
- Prefer native subagents when the environment supports them and the work is:
  - independently scannable
  - bounded in scope
  - useful to run in parallel with the main agent's integration work
  - better handled in a separate context window
- Prefer manual `codex exec` dispatch for work that is:
  - long-running
  - batch-oriented
  - artifact-heavy
  - easier to audit through explicit logs, output directories, and rerunnable commands
- Do not open subagents or background jobs just to appear more agentic. If the task is small, urgent, or tightly coupled, keep it in the main agent.
- If native subagent tools are unavailable, fall back to manual `codex exec` dispatch rather than forcing everything through serial manual reading.

### 10.2 Delegation rules

- Use native subagents for:
  - repo comprehension across multiple independent surfaces
  - parallel paper/file comparisons
  - bounded provenance checks
  - sidecar verification that does not block the main agent's immediate next step
- Keep delegated asks concrete and provenance-aware. A good delegated task should state:
  - the exact question
  - the target files or surfaces
  - the expected output shape
  - whether the task is read-only or allowed to mutate files
- Prefer read-only delegation for comprehension, comparison, and evidence gathering.
- If the main agent is blocked on a small answer that it can obtain directly, do not delegate it.
- Do not treat delegated output as final truth. Delegation produces intermediate evidence for later synthesis.

### 10.3 Batch research and `codex exec`

- For cross-paper inspection, batch comparison, large report preparation, figure precomputation, or other heavy non-mutating analysis, prefer using `codex exec` jobs first instead of serial manual reading.
- When multiple independent scans can be run separately, dispatch them in parallel and then synthesize the results in the main agent.
- Prefer `codex exec` when the task benefits from:
  - explicit shell commands
  - saved output artifacts
  - reproducible reruns
  - isolated long-context reading
- Keep the main agent focused on integration, provenance tracking, contradiction checking, and final interpretation rather than doing all heavy reading inline.
- Prefer read-only `codex exec` runs for evidence gathering unless a task explicitly requires mutation.

### 10.4 Verification and integration

- Subagent outputs and `codex exec` artifacts are intermediate evidence, not final claims.
- Important claims about prompts, runtime behavior, evaluation metrics, and repo provenance must be verified against primary source artifacts before being presented as confirmed.
- The main agent remains responsible for:
  - synthesis
  - contradiction resolution
  - path correctness
  - final wording
- Do not collapse inferred or reconstructed prompt text into confirmed prompt text without explicit provenance.
- When delegated analyses disagree, reconcile against source artifacts rather than choosing by majority.

### 10.5 Reporting expectations

- In final answers, separate:
  - confirmed from source
  - inferred or reconstructed
  - open uncertainty
- Preserve concrete file paths and artifact locations.
- State whether an important conclusion came from:
  - direct source inspection
  - delegated subagent analysis
  - manual `codex exec` output
- For long reports, summarize delegated findings, but keep provenance visible enough that a later reader can trace the claim back to source evidence.

## 11. graphify

This project may maintain a `graphify` knowledge graph at `graphify-out/`.

Rules:
- For architecture, prompt provenance, cross-file relationships, or pipeline-tracing questions, consult `graphify-out/GRAPH_REPORT.md` before broad raw-file search when the graph exists
- If `graphify-out/wiki/index.md` exists, navigate it before reading scattered raw files
- Treat `INFERRED` edges as leads, not final truth; verify important claims against source files
- If the graph is missing or likely stale after meaningful repo changes, rebuild with `graphify . --update` or `graphify .` for a full rebuild
- After modifying code files in this session, run `python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"` to keep the graph current
- Detailed usage notes live in `docs/skills/graphify_skills_guide.md`
