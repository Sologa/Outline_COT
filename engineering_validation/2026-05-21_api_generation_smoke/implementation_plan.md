# Implementation Plan

1. Build a prototype runner under this engineering-validation folder.
2. Reuse `scripts/codex_meow_outline_blind_lib.py` for prompt rendering and normalized outline parsing.
3. Implement two isolated transports:
   - direct async Responses API
   - Batch API JSONL submission, polling, output collection, and parsing
4. Keep secrets out of this repo by reading `OPENAI_API_KEY` from the caller environment or an explicitly supplied external env file.
5. Write all generated prompts, raw responses, normalized outlines, batch files, and manifests under `results/engineering_validation/2026-05-21_api_generation_smoke/`.

Rollback is deleting this engineering-validation folder and the matching `results/engineering_validation/2026-05-21_api_generation_smoke/` output folder.
