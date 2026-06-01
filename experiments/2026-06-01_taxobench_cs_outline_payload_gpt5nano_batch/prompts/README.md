# Prompts

Status: `prompt_contract_corrected_no_model_runs`

This folder is for experiment-local prompt templates only.

Current status: `neutral_append_template_render_only_verified_no_model_runs`.

The final generated-arm prompt contract is:

`target_title_plus_ref_meta_no_target_abstract`

The baseline arm should reuse or match the faithful MEOW blind prompt builder
from:

`scripts/codex_meow_outline_blind_lib.py`

The current taxonomy payload template is approved only for render-only request
building. It appends a neutral auxiliary taxonomy block to the released MEOW
baseline prompt skeleton, with no prompt-visible arm labels and no
treatment-only usage guidance.

Render-only taxonomy append template:

`taxobench_cs_outline_payload_prompt_template.txt`

Do not send any prompt from this folder to a model until the user separately
approves live generation.

Prompt-visible fields must not include:

- target survey/review paper abstract
- `Target Paper Abstract:` block
- local filesystem paths
- `metadata_*` provenance fields
- downloader/debug provenance fields

Reference paper abstracts inside sanitized `ref_meta[].abstract` are preserved
when present.
