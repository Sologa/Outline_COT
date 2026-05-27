# HF MEOW Raw Taxonomy High261 Source Store

This folder stores the 261 `taxonomy-signal high` candidates from the
Hugging Face `haajimi/Meow` `raw` split in a `meow_test100`-like layout.

This is a candidate corpus, not a Tree50 corpus. No paper in this folder is
counted as a strict source-confirmed taxonomy-tree paper until a later
source-confirmation pass verifies TeX/PDF/figure/table/prose evidence.

MEOW `outline`, title, abstract, and metadata are ranking and inventory fields
only. They are not taxonomy-tree evidence.

Layout:

- `metadata/`: raw records, manifests, download shards, and summaries
- `outlines/`: one MEOW outline JSON file per candidate
- `pdf/`: downloaded arXiv PDFs, ignored by Git
- `tex_src/`: downloaded and extracted arXiv e-print sources, ignored by Git

Source candidate list:

- `results/engineering_validation/2026-05-24_hf_meow_raw_taxonomy_tree50_selection/candidate_inventory/high_candidates_ranked.jsonl`

Pinned raw split:

- `temp_artifacts/hf_meow_raw_check_2026-05-24/raw.jsonl`
- SHA256: `5938812a35aabe85f8b2a08d0408d70cdab1627ceeb008b93d82e3f76a01eca5`

Typical workflow:

```bash
python3 data/paper_sets/hf_meow_raw_taxonomy_high261/download_arxiv_assets.py materialize
python3 data/paper_sets/hf_meow_raw_taxonomy_high261/download_arxiv_assets.py download-shard --shard metadata/download_shards/input_shard_001_001_025.jsonl
python3 data/paper_sets/hf_meow_raw_taxonomy_high261/download_arxiv_assets.py merge-downloads
python3 data/paper_sets/hf_meow_raw_taxonomy_high261/download_arxiv_assets.py validate --require-download-complete
```
