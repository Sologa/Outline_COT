# Taxonomy-Augmented Outline Prompt Experiment

## Identity

- Experiment id: `2026-05-20_taxonomy_augmented_outline_prompt`
- Owner: xjp / Codex
- Status: provisional runner ready
- Created: 2026-05-20

## Hypothesis

Providing an explicit taxonomy as an additional input to the original blind MEOW outline-generation prompt will improve outline structure, especially for the topical or methodological main body, without requiring a substantially different prompt.

The experiment tests whether taxonomy information is useful as an outline-planning signal, not whether the taxonomy extractor itself is correct.

## Scope

- Target paper set: only `096_2502.03108` for the first provisional run.
- Baseline to compare against: the same blind outline-generation prompt without taxonomy, using the same model, effort, paper inputs, and evaluation backend.
- Inputs:
  - paper title
  - reference metadata
  - two input conditions: `no_abstract` and `with_abstract`
  - taxonomy text rendered from the taxonomy artifact as compact tree labels only
- Outputs:
  - model-generated outlines under `results/experiments/2026-05-20_taxonomy_augmented_outline_prompt/2026-05-20_paper096/...`
  - evaluation artifacts under the same result run
  - paired comparison summary against baseline
- Out of scope:
  - changing the stable `prompts/` directory
  - updating the official stable experiment ledger
  - rerunning or modifying taxonomy extraction
  - full 100-paper runs before this single-paper provisional result is reviewed

## Method

Create prompt variants that preserve the original blind outline prompt and add one concise taxonomy block before the references.

The taxonomy block must be generic. The template is meant to support any future workflow that supplies a taxonomy to guide outline generation, regardless of how that taxonomy was obtained.

The primary variant should be low-restriction: it tells the model to use taxonomy when it helps organize the topical or methodological body, while preserving normal review/survey scaffold sections when warranted.

A second guarded variant may add explicit anti-overexpansion wording. This is an ablation, not the default prompt.

## Success Metrics

- Primary metric: paired improvement over baseline on the existing MEOW outline evaluation path.
- Secondary metrics:
  - structural distance / shape comparison where available
  - LLM judge score by the same backend as the baseline
  - section-title and hierarchy overlap for the taxonomy-heavy main body
- Qualitative checks:
  - no obvious taxonomy-leaf overexpansion
  - normal survey scaffold sections are not suppressed when warranted
  - generated `ref` lists remain grounded in provided reference metadata
- Minimum improvement needed: to be decided after baseline and run-scope decisions.

## Risks

- Provenance risk: taxonomy inputs may be mistaken for a gold outline. The prompt must keep taxonomy as guidance, not target structure.
- Evaluation mismatch risk: taxonomy-heavy papers may improve while non-taxonomy papers do not; this result must not be generalized to all MEOW papers.
- Overfitting risk: paper `096_2502.03108` has an unusually explicit taxonomy-to-outline relationship, so the first result is a capability probe, not a population estimate.
- Cost/runtime risk: paired baseline plus taxonomy runs should stay single-paper until the design is reviewed.

## Promotion Gate

This experiment can move toward stable pipeline support only after:

- baseline and taxonomy-augmented runs are produced under the same model/effort/settings
- taxonomy rendering is deterministic and tested
- both minimal and guarded variants are compared before choosing a stable wording
- prompt wording is reviewed with the user
- provisional single-paper outputs show improvement or explainable no-change/failure
- the user and Codex agree on whether results are stable enough for formal recordkeeping
