# Prompt Variants

This directory stores prompt variants local to the experiment.

- `taxonomy_augmented_outline_prompt_template.txt`: v1 minimal template for adding a supplied taxonomy to the original blind outline-generation prompt.
- `taxonomy_augmented_outline_prompt_guarded_template.txt`: v2 guarded template that adds explicit anti-overexpansion guidance.

The template is intentionally generic. It treats taxonomy as an input that can guide outline organization, regardless of how the taxonomy is obtained.
