# Prompts

`tree50_round4_tree_prompt_template.txt` is the taxonomy-payload user prompt
for the round4 tree arm.

The baseline arm uses the faithful MEOW blind prompt builder from
`scripts/codex_meow_outline_blind_lib.py` and intentionally has no taxonomy
block.

Neither arm includes the target survey/review paper abstract. Both arms see the
same target title and reference metadata JSON; only the tree arm sees the round4
tree payload.
