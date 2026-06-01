# No-Run Guardrails

Status: `prompt_contract_corrected_no_model_runs`

Canonical staging and prompt-safe taxonomy payloads now exist, but live
generation is still blocked by prompt-template comparability and explicit
approval gates.

Allowed now:

- edit documentation
- add future adapter/runner/evaluator design notes
- inspect source data read-only
- add tests that do not call external services
- regenerate or validate `data/taxobench-cs` only when the user explicitly
  approves the relevant canonical-data write scope

Not allowed without explicit user approval:

- render prompts into `results/`
- write Batch API JSONL for live submission
- submit OpenAI Batch jobs
- poll or collect model jobs
- run judge/evaluation
- update Google Sheets
- write into `/Users/xjp/Desktop/TaxoBench-CS`
- copy large PDFs/source bundles into Outline_COT

If a future script is added, it should default to dry-run or fail-closed unless
given an explicit write/run flag.
