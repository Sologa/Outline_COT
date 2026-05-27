# Prompt For New Thread

Use this prompt in a new Codex conversation.

```text
你正在 /Users/xjp/Desktop/Outline_COT 工作。請先只讀檔，不要修改任何檔案。

任務背景：
我們之前做了 MEOW taxonomy extraction，產生 23 個 taxonomy_extraction.json，對應 22 篇 unique papers。這些 artifacts 保留了很多 source-grounded taxonomy/tree/table/DAG 資訊，但 schema 語義有問題：node-level `facet` 常被用來表示 local split axis / branch criterion / table column / visual grouping，而不是 TaxoAdapt-style 的 independent facet tree。現在的目標是做 semantic correction validation，不是馬上重抽，也不是直接重跑 downstream experiment。

請先閱讀以下必讀文件：

1. Snapshot summary:
   results/engineering_validation/2026-05-23_taxonomy_extraction_snapshot/snapshot_summary.md

2. Snapshot manifest:
   results/engineering_validation/2026-05-23_taxonomy_extraction_snapshot/MANIFEST.tsv

3. Semantic correction spec:
   engineering_validation/2026-05-23_taxonomy_extraction_semantic_correction/spec.md

4. Original extraction protocol:
   experiments/2026-05-19_meow_taxonomy_extraction/spec.md
   experiments/2026-05-19_meow_taxonomy_extraction/runbook.md
   experiments/2026-05-19_meow_taxonomy_extraction/config.yaml

5. Original extraction summaries:
   results/experiments/2026-05-19_meow_taxonomy_extraction/smoke/smoke_summary.md
   results/experiments/2026-05-19_meow_taxonomy_extraction/selected18_2026-05-21/selected18_summary.md

6. First taxonomy22 downstream input records:
   results/experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch_taxonomy22/2026-05-22T1241_taipei/_inputs/taxonomy22_input_manifest.json
   results/experiments/2026-05-22_taxonomy_augmented_outline_prompt_gpt5nano_batch_taxonomy22/2026-05-22T1241_taipei/_summaries/prompt_rendering_validation.json

7. ChatGPT report with strict TaxoAdapt-style multifaceted taxonomy discussion:
   results/engineering_validation/2026-05-23_taxonomy_extraction_snapshot/external_context/taxoadapt_style_multifaceted_taxonomy_audit_meow_samples_zh_TW.md
   如果這份不存在，再看 ~/Downloads/taxoadapt_style_multifaceted_taxonomy_audit_meow_samples_zh_TW.md

8. TaxoAdapt definition sources:
   /Users/xjp/Desktop/Taxonomy/external/paper_repos/taxoadapt/README.md
   /Users/xjp/Desktop/Taxonomy/docs/papers/pdf/TaxoAdapt_Aligning_LLM_Based_Multidimensional_Taxonomy_Construction.pdf

重要定義：
TaxoAdapt-style multifaceted taxonomy forest 不是「一棵樹裡有很多 facet 字段」。它至少需要多個 independent dimensions，例如 tasks / datasets / methodologies / evaluation_methods / real_world_domains；每個 dimension 有自己的 taxonomy tree/DAG；paper 可以被分類到多個 dimensions；paper 被 assign 到各 dimension 的 nodes；並且有基於 corpus topical distribution 的 hierarchical classification、width expansion、depth expansion。現有 22 篇 artifacts 目前沒有一篇完整符合這個定義。

目前要處理的問題：
- 不應再讓現有 artifacts 被理解為 multifaceted taxonomy trees。
- 需要把大多數 node.facet 語義改正為 local_split_axis 或 local_classification_criterion。
- 對每篇 paper 增加 artifact-level verdict，例如 artifact_type、is_taxoadapt_style_multifaceted=false、taxoadapt_style_verdict、taxoadapt_style_rationale。
- 不要直接覆寫原始 results/experiments/2026-05-19_meow_taxonomy_extraction 裡的 JSON。
- 原始狀態已 snapshot 在 results/engineering_validation/2026-05-23_taxonomy_extraction_snapshot/，必須保持可追溯。

請先完成只讀分析並給出：
1. 你對 semantic correction schema v2 的具體欄位設計。
2. 你會如何處理 node.facet：rename、保留但降級、或新增 projection 欄位。
3. 你會先抽樣處理哪些 papers，至少包含 096、074、077、097、037、094。
4. 你預計寫入哪些新檔案到 results/engineering_validation/2026-05-23_taxonomy_extraction_semantic_correction/。
5. 在我同意前，不要做 correction，不要重抽，不要跑模型 API，不要重跑 taxonomy22。
```
