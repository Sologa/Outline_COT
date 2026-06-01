# Prompts

Status: `draft_data_pending_no_runs`

This folder is for experiment-local prompt templates only.

Current status: `placeholder_docs_only`.

The final generated-arm prompt contract is:

`target_title_plus_ref_meta_no_target_abstract`

The baseline arm should reuse or match the faithful MEOW blind prompt builder
from:

`scripts/codex_meow_outline_blind_lib.py`

The taxonomy payload arms will use a guarded user prompt template:

`taxobench_cs_outline_payload_prompt_template.txt`

Do not send any prompt from this folder to a model until the adapter and render
smoke are implemented and approved.

Prompt-visible fields must not include:

- target survey/review paper abstract
- `Target Paper Abstract:` block
- local filesystem paths
- `metadata_*` provenance fields
- downloader/debug provenance fields

Reference paper abstracts inside sanitized `ref_meta[].abstract` are preserved
when present.
