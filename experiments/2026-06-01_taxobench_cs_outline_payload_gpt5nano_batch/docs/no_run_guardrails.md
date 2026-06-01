# No-Run Guardrails

Status: `draft_data_pending_no_runs`

This scaffold was created before TaxoBench-CS data was declared fully ready.

Allowed now:

- edit documentation
- add future adapter/runner/evaluator design notes
- inspect source data read-only
- add tests that do not call external services

Not allowed without explicit user approval:

- render prompts into `results/`
- write Batch API JSONL
- submit OpenAI Batch jobs
- poll or collect model jobs
- run judge/evaluation
- update Google Sheets
- write into `/Users/xjp/Desktop/TaxoBench-CS`
- copy large PDFs/source bundles into Outline_COT

If a future script is added, it should default to dry-run or fail-closed unless
given an explicit write/run flag.
