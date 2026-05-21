# Outline Induction IR Audit

Date: 2026-04-05

Prompt baseline:
- `prompts/outline_induction_ir_user.txt`

Audited files:
- `data/paper_sets/meow_refs/2511.13936/outline_induction_ir.yaml`
- `data/paper_sets/meow_refs/2310.07264/outline_induction_ir.yaml`
- `data/paper_sets/meow_refs/2510.01145/outline_induction_ir.yaml`
- `data/paper_sets/meow_refs/2503.04799/outline_induction_ir.yaml`
- `data/paper_sets/meow_refs/2312.05172/outline_induction_ir.yaml`

Scope:
- Audit only.
- No files modified under `data/paper_sets/meow_refs/`.
- `outline.json` and `COT.md` were not used as gold answers.
- Local title / metadata / log artifacts were used only for provenance checks.

## High-Priority Findings

- File: `data/paper_sets/meow_refs/2510.01145/outline_induction_ir.yaml`
  Line/key: `:10`, `:27`, `:317`, `:505`, `:617`; cross-check `.local/logs/outline_induction_ir/2510.01145.inputs.json:4`
  Why this is a problem:
  The provenance snapshot says `reference_count: 94`, but the current IR covers 113 unique refs and leaves `unassigned_refs: []`. That breaks auditability against the actually supplied reference set. Taxonomically, `n_asr_models` absorbs 84 refs and functions as a catch-all bucket rather than a discriminative node. At the same time, `n_african_resources` mixes true resource refs with `page2021prisma`, World Bank, WPR, and Nations Online sources, which are framing or demographic sources rather than ASR resource papers.

- File: `data/paper_sets/meow_refs/2503.04799/outline_induction_ir.yaml`
  Line/key: `:11`, `:161`, `:239`, `:603`, `:623`, `:707`
  Why this is a problem:
  The IR relies on multiple unstable or low-quality reference keys such as `key`, `GoogleAIBlog`, `ijcaonline`, `book`, and `latency`, but still treats them as normal assignable references. Several assignments look like keyword-triggered placements rather than metadata-grounded thematic inference, for example `oshea2015introductionconvolutionalneuralnetworks` in `n_evaluation_and_quality` because of `mos`, and `DBLP:journals/corr/VaswaniSPUJGKP17` in `n_multilingual_data` because of `parallel`. This is schema-valid but not a trustworthy reference-only induction IR.

- File: `data/paper_sets/meow_refs/2312.05172/outline_induction_ir.yaml`
  Line/key: `:23`, `:138`, `:481`, `:793`, `:797`
  Why this is a problem:
  `n_compression_and_deletion` contains 78 refs and `n_neural_generation` contains 40 refs, so the taxonomy is far too coarse for an auditable middle layer. The IR also hard-assigns generic MT / evaluation references such as `Vaswani2017` and `Papineni2002` into `n_neural_generation` instead of using `unassigned_refs`. That directly conflicts with the prompt's preference for conservative assignment and discriminative leaf nodes.

- File: `data/paper_sets/meow_refs/2310.07264/outline_induction_ir.yaml`
  Line/key: `:158`, `:162`, `:170`, `:229`, `:587`
  Why this is a problem:
  The ledger is almost entirely boilerplate. `assignment_reason` repeatedly uses only two templates: `Matched theme cues ...` and `No narrower theme cues ...`. That does not meet the prompt requirement that reasons be case-specific and explain positive evidence and nearby sibling boundaries. The file is structurally consistent, but the reasoning layer is too thin for real audit.

## Medium-Priority Findings

- File: `data/paper_sets/meow_refs/2310.07264/outline_induction_ir.yaml`
  Line/key: `:5`; cross-check `.local/logs/outline_induction_ir/2310.07264.inputs.json:3`
  Why this is a problem:
  The retained YAML has the full title, but the local inputs snapshot records only `Who k`. This is not proof that prohibited artifacts were used, but it does mean the currently stored provenance trail cannot fully explain how the final artifact was produced.

- File: `data/paper_sets/meow_refs/2511.13936/outline_induction_ir.yaml`
  Line/key: `:245`, `:550`; cross-check `.local/logs/outline_induction_ir/2511.13936.inputs.json:4`
  Why this is a problem:
  This is the strongest IR in the batch, but the available provenance snapshot records `reference_count: 83` while the current artifact covers 84 unique refs. The mismatch is small, but it still weakens end-to-end audit closure.

- File: `data/paper_sets/meow_refs/2510.01145/outline_induction_ir.yaml`
  Line/key: `:21`, `:24`, `:517`, `:561`
  Why this is a problem:
  `NationsOnline2025` and `nationsonline2025` appear as separate references. If they are actually the same source, coverage is inflated; if not, the distinction is undocumented. Either way, the IR does not make key normalization or provenance boundaries explicit enough.

- File: `data/paper_sets/meow_refs/2312.05172/outline_induction_ir.yaml`
  Line/key: `:11`, `:18`, `:285`
  Why this is a problem:
  `page2021prisma` is assigned to `n_readability_foundations`, which mixes review-protocol scaffolding into content taxonomy. This is a sign that the taxonomy is being filled opportunistically rather than preserving a clean reference-only thematic middle layer.

- File: `data/paper_sets/meow_refs/2503.04799/outline_induction_ir.yaml`
  Line/key: `:11`, `:83`, `:161`
  Why this is a problem:
  Top-level nodes such as `Core Speech-to-Speech Translation Architectures`, `Multilingual Data, Corpora, and Low-Resource Settings`, and `Applications, Deployment Constraints, and Future Directions` look more like a conventional review scaffold than a taxonomy induced tightly from the supplied references. This is not direct evidence of peeking at `outline.json` or `COT.md`, but it is a provenance warning sign.

## File-Specific Notes

- File: `data/paper_sets/meow_refs/2511.13936/outline_induction_ir.yaml`
  Status:
  No major schema or coverage defect found. YAML parses, required top-level keys are present, `rendered_outline` is absent, node and ledger types are correct, and `unassigned_refs` is used conservatively. This is also the only file in the batch that consistently prefers leaving weakly supported refs unassigned.

- File: `data/paper_sets/meow_refs/2310.07264/outline_induction_ir.yaml`
  Status:
  YAML parses, required top-level keys are complete, types are correct, and coverage/ledger consistency closes cleanly. The main weakness is not structure but auditability of reasoning and a provenance gap around the stored input title snapshot.

- File: `data/paper_sets/meow_refs/2510.01145/outline_induction_ir.yaml`
  Status:
  YAML and basic schema pass, but the artifact is not trustworthy as a precise outline induction IR because provenance counts do not match and the taxonomy is dominated by a single broad fallback node.

- File: `data/paper_sets/meow_refs/2503.04799/outline_induction_ir.yaml`
  Status:
  YAML and basic schema pass, and raw coverage is internally closed, but the artifact is heavily degraded by placeholder refs, weak citation keys, and cue-based assignment into broad conventional sections.

- File: `data/paper_sets/meow_refs/2312.05172/outline_induction_ir.yaml`
  Status:
  YAML and schema pass, and coverage is internally closed, but the taxonomy is too broad and assignment is too aggressive to function as a discriminative, reference-only, auditable middle layer.

## Quality Ranking

From worst to best:

1. `2510.01145`
   Main issue:
   Provenance count mismatch is severe, and the taxonomy collapses into an 84-ref `n_asr_models` bucket with no conservative use of `unassigned_refs`.

2. `2503.04799`
   Main issue:
   Placeholder / low-quality citation keys are treated as normal references, and several assignments look like cue matching rather than grounded thematic induction.

3. `2312.05172`
   Main issue:
   The structure is clean on paper, but the main nodes are too coarse and generic MT / summarization papers are over-assigned instead of left unassigned.

4. `2310.07264`
   Main issue:
   Structural consistency is decent, but the ledger is almost entirely boilerplate and therefore weak as an auditable explanation of assignment decisions.

5. `2511.13936`
   Main issue:
   Strongest file overall. The only notable issue is a small reference-count mismatch against the available provenance snapshot.

## Overall Judgment

`usable with revisions`
