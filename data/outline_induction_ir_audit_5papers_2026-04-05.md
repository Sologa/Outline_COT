# Outline Induction IR Audit

Date: 2026-04-05

Prompt baseline:
- `prompts/outline_induction_ir_user.txt`

Audited files:
- `refs/2409.13738/outline_induction_ir.yaml`
- `refs/2507.18910/outline_induction_ir.yaml`
- `refs/2509.11446/outline_induction_ir.yaml`
- `refs/2507.07741/outline_induction_ir.yaml`
- `refs/2401.09244/outline_induction_ir.yaml`

Evidence used:
- `logs/outline_induction_ir/2409.13738.inputs.json`
- `logs/outline_induction_ir/2507.18910.inputs.json`
- `logs/outline_induction_ir/2509.11446.inputs.json`
- `logs/outline_induction_ir/2507.07741.inputs.json`
- `logs/outline_induction_ir/2401.09244.inputs.json`
- `logs/outline_induction_ir/run5_20260405_164332_prefilled.log`
- local `refs/*/tex_src` titles and bibliography artifacts, used only to explain provenance gaps

Scope:
- Audit only.
- No files under `refs/` were modified.
- `outline.json` and `COT.md` were not used as gold answers.
- Local title / metadata / log artifacts were used only for provenance and assignment checks.

## High-Priority Findings

- File: `refs/2401.09244/outline_induction_ir.yaml`
  Line/key: `title` at `:5`; `n_translation_and_alignment.refs_complete` at `:173`, `:175`, `:176`; `n_evaluation_and_robustness.refs_complete` at `:225`; `n_bias_and_open_challenges.refs_complete` at `:253`; ledger entries at `:991`, `:1043`; cross-check `logs/outline_induction_ir/2401.09244.inputs.json:3-4` and `logs/outline_induction_ir/run5_20260405_164332_prefilled.log:21-24`
  Why this is a problem:
  The run-time snapshot says the model was prepared with `title: "Cross-lingual HS Survey"` and `reference_count: 196`, but the retained IR uses a different title and covers 207 references. The batch log confirms `ledger_count: 207`, which exceeds the supplied reference universe. The current YAML therefore includes references that were not part of the recorded run-time inputs, including `vaswani2017attention`, `mikolov2013distributed`, `pennington2014glove`, `touvron2023llama`, `zhang2023interpretable`, and `rightforpeace`. That breaks the prompt's reference-only and auditability requirements at the provenance level.

- File: `refs/2409.13738/outline_induction_ir.yaml`
  Line/key: `title` at `:5`; `unassigned_refs` at `:414-425`; cross-check `logs/outline_induction_ir/2409.13738.inputs.json:3-4` and `logs/outline_induction_ir/run5_20260405_164332_prefilled.log:1-4`
  Why this is a problem:
  The run-time snapshot records `title: "Title label1"` and `reference_count: 84`, but the retained IR uses the full paper title and only covers 72 references in total. The batch log confirms `ledger_count: 72` and `unassigned_count: 11`, which means 12 supplied references are silently omitted from both `refs_complete` and `unassigned_refs`. Missing inputs include `kitchenham2004procedures`, `dumas2018fundamentals`, `Devlin2019BERTPO`, `devlin_bert`, `mikolov2013distributed`, `lopez2021challenges`, and `bellan2022extracting`. This is a direct violation of the prompt rule that every supplied reference must be assigned or explicitly left unassigned.

- File: `refs/2509.11446/outline_induction_ir.yaml`
  Line/key: top-level nodes at `:11-37`, `:38-87`, `:88-144`; broad fallback and cue-driven ledger entries at `:660-759`; cross-check `logs/outline_induction_ir/2509.11446.inputs.json:3`
  Why this is a problem:
  The artifact is internally closed on coverage, but the taxonomy is too broad and the ledger is not case-specific enough to qualify as an auditable induction IR. `n_re_tasks_and_artifacts` functions as a catch-all node for generic foundations and textbooks such as `vaswani2017attention`, `Abbott1981`, `jurafsky2023speech`, and `see2019massivelypretrainedlanguagemodels`. At the same time, `n_evaluation_and_empirical_assessment` absorbs foundational model papers and RE textbooks such as `devlin2018bert`, `Devlin2018`, `OpenAI2023`, `Touvron2023`, `nuseibeh2000requirements`, `van2007requirements`, and `wiegers2013software` based only on shallow cues like `empirical`, `benchmark`, `evaluation`, or `mapping`. This violates the prompt's requirements for discriminative leaves, conservative assignment, and case-specific `assignment_reason`.

- File: `refs/2509.11446/outline_induction_ir.yaml`
  Line/key: `title` at `:5`; cross-check `logs/outline_induction_ir/2509.11446.inputs.json:3`, `logs/outline_induction_ir/run5_20260405_164332_prefilled.log:11-14`, and local title lines in `refs/2509.11446/tex_src/main.tex:118` and `:133`
  Why this is a problem:
  The run-time snapshot still shows `title: "Title label1"`, while the retained IR contains the full title. Local `tex_src` now contains the real title, but also contains the commented template line that explains why the title parser could have produced the placeholder at run time. This means the currently saved provenance trail cannot explain the final YAML title without appealing to artifacts outside the logged run-time inputs.

- File: `refs/2507.18910/outline_induction_ir.yaml`
  Line/key: `n_rag_foundations` at `:11-23`; `n_agents_and_domain_applications` at `:123-162`; cue-driven ledger entries at `:287-314`, `:435-462`, and `:511-518`
  Why this is a problem:
  Coverage closes cleanly, but the taxonomy is not precise enough for a trustworthy middle layer. `n_rag_foundations` absorbs `time2024patrick`, `ragwebui2023`, `openwebui2023`, and `athina2024` under a broad fallback explanation even though these are magazine, product, or guide-style sources rather than core architectural foundations. `n_agents_and_domain_applications` also absorbs generic LLM papers such as `Brown2020` and `Chowdhery2022`, while `n_retrieval_and_indexing` takes domain-specific healthcare and legal papers such as `Magesh2025LegalHallucinations`, `Miao2024NephrologyRAG`, `Yang2025RAGHealthcare`, `CBR_RAG_Legal`, and `Gilbert2024MedCurator` based almost entirely on the presence of words like `retrieval`, `index`, or `domain`. This is schema-valid, but it is not a sufficiently discriminative or audit-friendly taxonomy.

## Medium-Priority Findings

- File: `refs/2507.07741/outline_induction_ir.yaml`
  Line/key: `n_transfer_and_adaptation` at `:192-219`; cue-driven assignments at `:578-581`, `:842-845`, `:862-865`, and `:918-921`
  Why this is a problem:
  This file has no major schema or coverage defect, but the method taxonomy is still too permissive. `n_transfer_and_adaptation` accepts sociolinguistic theory (`myers-scotton_social_1995`), education-policy material (`UNESCO_Multilingual_2024`), broad multilingual corpora (`commonvoice`), and even `Zhu_2017_ICCV`, which is a CycleGAN computer-vision paper, based mainly on generic `multilingual` or `transfer` cues. These assignments are weak enough that at least some of them should have gone to `unassigned_refs` instead of being hard-assigned.

- File: `refs/2507.07741/outline_induction_ir.yaml`
  Line/key: `n_e2e_asr_architectures` at `:35-171`; assignments at `:762-773`, `:886-929`
  Why this is a problem:
  `n_e2e_asr_architectures` behaves as a very large catch-all bucket. It pulls in weakly related or generic model references such as `radford2022robust`, `peng2023prompting`, `specaugment`, `mt5`, and `t5` using generic `speech recognition`, `transformer`, or `end to end` cues. This makes the node internally heterogeneous and reduces audit precision, even though the file is still stronger than the other four on basic provenance closure.

## File-Specific Notes

- File: `refs/2409.13738/outline_induction_ir.yaml`
  Status:
  YAML parses, required top-level keys are complete, types are correct, `rendered_outline` is absent, and the artifact does use `unassigned_refs` conservatively. The main failure is hard provenance closure: the saved IR does not account for the full run-time reference universe, and the final title is not explained by the logged `inputs.json`.

- File: `refs/2507.18910/outline_induction_ir.yaml`
  Status:
  YAML parses, required top-level keys are complete, internal coverage closes, and there is no node/ledger mismatch. The main weakness is taxonomy precision: several top-level nodes are broad enough that weak evidence refs can be forced into them via generic cue matching.

- File: `refs/2509.11446/outline_induction_ir.yaml`
  Status:
  YAML parses, required top-level keys are complete, internal coverage closes, and there is no `rendered_outline`. The file is still not a strong IR because the title provenance is broken and the assignment ledger is dominated by generic fallback and keyword-triggered reasoning.

- File: `refs/2507.07741/outline_induction_ir.yaml`
  Status:
  This is the cleanest file in the batch on schema and coverage. YAML parses, required keys are present, internal reference accounting closes, and the single unassigned ref (`Sreeram2020`) is handled conservatively. The remaining weakness is over-broad method taxonomy and cue-triggered placement of weakly supported references.

- File: `refs/2401.09244/outline_induction_ir.yaml`
  Status:
  YAML parses and is internally self-consistent, but it is not provenance-safe. The saved artifact uses a title and reference universe that do not match the recorded run-time inputs, so it cannot be treated as a true reference-only induction artifact for that logged run.

## Quality Ranking

From worst to best:

1. `2401.09244`
   Main issue:
   The retained IR uses 207 references against a logged run-time universe of 196, and its title also differs from the run-time snapshot. This breaks the reference-only provenance contract directly.

2. `2509.11446`
   Main issue:
   Title provenance is broken, and the taxonomy is mostly sustained by broad fallback buckets and keyword-triggered routing rather than case-specific assignment logic.

3. `2409.13738`
   Main issue:
   The artifact uses `unassigned_refs` reasonably, but it still drops 12 supplied references entirely and the title does not match the logged input snapshot.

4. `2507.18910`
   Main issue:
   Coverage is fine, but the main top-level nodes are too broad and absorb weak-evidence product, domain, and generic LLM references through shallow cue matching.

5. `2507.07741`
   Main issue:
   Strongest file in the set on schema and coverage. The remaining problems are mostly taxonomy coarseness and several obviously weak cue-based assignments.

## Overall Judgment

`still not usable`
