# Outline_COT Repo Guide

This file is the repo-level guide for future conversations and agents working in this repository.

Read this file before inferring workflow from scattered prompt files, helper HTML, or older notes.

## 1. Repo purpose

This repository is primarily used to inspect, reconstruct, compare, and extract:

- MEOW-style literature review outlines
- outline-generation prompts
- CoT / reasoning prompts tied to outline generation
- prompt provenance across paper, repo code, and dataset artifacts

Current working artifacts include:

- `refs/<paper_id>/outline.json`
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

Short form:

- `prompts/` files are direct LLM API inputs.
- Default handling is raw read plus optional `{Var}` substitution only.
- No extra rewriting layer by default.

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
