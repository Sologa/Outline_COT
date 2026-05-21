# MEOW test100 outlines

This directory contains the extracted gold/human outlines for the 100 MEOW test-set papers already mirrored under `data/paper_sets/meow_test100/`.

Provenance:
- GitHub source: `cedricshan/Survey-Outline-Evaluation-Benckmark/datasets/test_prompts.json`
- Git blob SHA: `5ebe31ea9ebb0fc9eb547247c5ea7b7d3a8cb7ed`
- Hugging Face dataset: `haajimi/Meow`

Direct Hugging Face check:
- `https://huggingface.co/datasets/haajimi/Meow/resolve/main/test.jsonl` was downloaded directly.
- The direct file is 262144 bytes, SHA-256 `df29da443e93a221f37e090c2e9f2898715a93148a8da5873cb92155552f9a58`.
- Only the first 2 JSONL records parse completely; the third record is truncated in the upstream file.
- The first direct-HF outline matches the GitHub benchmark assistant outline exactly. The 100 full outlines here therefore use the GitHub benchmark prompt file as the complete parseable source.

Each `NNN_<arxiv_id>.outline.json` file contains the paper title, arXiv ID, local PDF/TeX paths, source provenance, and the extracted `outline` list.

Index files:
- `../metadata/outline_manifest.jsonl`: compact per-paper index
- `../metadata/outlines.jsonl`: all 100 full outline records
- `../metadata/outline_summary.json`: extraction summary and schema notes
