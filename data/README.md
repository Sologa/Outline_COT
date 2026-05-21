# Data

`data/` stores paper sets and compact manifests used as evaluation inputs or reference truth.

- `paper_sets/meow_refs/`: earlier curated MEOW reference papers. These directories contain paper-side artifacts such as `outline.json`, reconstruction inputs, `COT.md`, and TeX source links.
- `paper_sets/meow_test100/`: MEOW 100-paper test set package. It includes metadata, released outline artifacts, PDF files, and arXiv source packages. Large `pdf/` and `tex_src/` payloads are ignored by Git.

Experiment outputs belong in `results/`, not here.
