# Outline Induction IR Prompts For Codex

This file is for humans and agents. It explains how to use the new prompt at [outline_induction_ir_user.txt](/Users/xjp/Desktop/Outline_COT/prompts/outline_induction_ir_user.txt) and provides copy-ready prompts for starting a new Codex conversation.

The target artifact is a **reference-only outline induction IR**:
- it is not a gold-outline explanation
- it is not a `COT.md` rewrite
- it is not a rendered outline
- it is an auditable YAML intermediate representation that assigns references to candidate section nodes or to `unassigned_refs`

Use [outline_induction_ir_user.txt](/Users/xjp/Desktop/Outline_COT/prompts/outline_induction_ir_user.txt) when you want a model to generate the IR itself.

Use the templates below when you want Codex to orchestrate the workflow, inspect repo files, and save outputs under `refs/<paper_id>/outline_induction_ir.yaml`.

If you are fixing already generated IRs after an audit pass, use the repair workflow at [outline_induction_ir_repair_workflow.md](/Users/xjp/Desktop/Outline_COT/docs/prompts/outline_induction_ir_repair_workflow.md). Do not try to continue the original generation session if the file was created via `codex exec --ephemeral`.

## Single-Paper Generation

```text
Read `AGENTS.md` first.

Then read `prompts/outline_induction_ir_user.txt`.

Task:
Generate a reference-only outline induction IR for paper `{paper_id}` and save it to:
`refs/{paper_id}/outline_induction_ir.yaml`

Rules:
- Use only the paper title and the available reference metadata as generation inputs.
- Do not use `outline.json`, `COT.md`, or any gold section structure to determine node titles or hierarchy.
- You may inspect local files to find title/reference metadata, but the IR itself must be induced from reference metadata only.
- The final saved artifact must be valid YAML.
- Every reference must appear either in some node's `refs_complete` or in `unassigned_refs`.
- Do not include `rendered_outline`.

After saving the file, give me a short summary of:
- how many top-level nodes were produced
- how many references were assigned
- how many references remained unassigned
```

## Sequential Loop Script

Do not ask one Codex call to process every paper. The safer workflow is one `codex exec` call per paper inside a shell loop. Use [run_outline_induction_ir_loop.sh](/Users/xjp/Desktop/Outline_COT/scripts/run_outline_induction_ir_loop.sh) for that.

Examples:

```bash
bash scripts/run_outline_induction_ir_loop.sh --dry-run
```

```bash
bash scripts/run_outline_induction_ir_loop.sh --force 2601.19926
```

```bash
bash scripts/run_outline_induction_ir_loop.sh --force
```

The script defaults to:
- `model=gpt-5.4`
- `model_reasoning_effort=xhigh`
- full-access non-interactive Codex execution

Override them when needed:

```bash
bash scripts/run_outline_induction_ir_loop.sh --force --model gpt-5.4 --effort xhigh
```

If you explicitly want to override the Codex service tier on this machine, use one of the values that the local Codex config accepts:

```bash
bash scripts/run_outline_induction_ir_loop.sh --force --service-tier fast
```

```bash
bash scripts/run_outline_induction_ir_loop.sh --force --service-tier flex
```

## Audit Mode

```text
Read `AGENTS.md` first.

Then read `prompts/outline_induction_ir_user.txt`.

Task:
Audit one or more existing `refs/<paper_id>/outline_induction_ir.yaml` files for structural completeness and provenance compliance.

Audit checklist:
- confirm the file is valid YAML
- confirm required top-level keys exist
- confirm every node contains the required fields
- confirm every reference is either assigned in `refs_complete` or listed in `unassigned_refs`
- confirm no `rendered_outline` block is present
- confirm the artifact does not appear to rely on `outline.json` or `COT.md` as supervision
- flag weak nodes with empty `refs_complete` that lack a valid `preserve_reason`
- flag assignments whose `assignment_reason` is missing or too vague

Rules:
- Focus on bugs, provenance risks, silent omissions, and schema violations.
- If you find issues, cite the file and the exact key path or line area involved.
- Do not rewrite the artifact unless I explicitly ask for fixes.

Output:
- findings first
- then a short summary of overall IR quality
```

## Repair Mode

For post-audit repair of existing IR files, do not batch multiple papers into one repair chat. Use one new Codex conversation per paper and treat the work as targeted editing of the stored YAML artifact.

The detailed workflow, repair order, acceptance criteria, and copy-ready prompts live in [outline_induction_ir_repair_workflow.md](/Users/xjp/Desktop/Outline_COT/docs/prompts/outline_induction_ir_repair_workflow.md).
