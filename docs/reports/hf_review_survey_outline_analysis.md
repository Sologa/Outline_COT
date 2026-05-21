# Hugging Face Review-vs-Survey Outline Analysis

更新日期：2026-04-17

## 1. 文件目的

這份文件是即將落地的 `scripts/hf_review_survey_outline_analysis.py` 的使用契約與報告側規格。

它的角色是：

1. 定義分析目標與範圍。
2. 說明輸入資料、標籤規則、結構特徵、統計方法與輸出 artifact。
3. 規定報告章節結構，讓之後的結果可以重跑、重驗證、可比較。

它**不是**實作說明，也**不是**最終結果本身。

## 2. 分析目標

此 pipeline 要回答的核心問題是：

1. `review` / `systematic review` 類 outline 是否比 `survey` 類 outline 更一致。
2. 這個差異在控制 `domain`、`year`、`reference count` 之後是否仍成立。
3. MEOW 主語料與外部 Hugging Face 對照語料是否都指向相同方向。

報告需要同時提供兩個層級的 genre 定義：

1. `strict`：只把嚴格 review / SR 類當作 `review`
2. `broad`：把更廣的 review / survey-adjacent 類型也納入 `review`

## 3. 資料契約

### 3.1 主要 corpus：MEOW `raw`

主分析集固定使用 Hugging Face 上的 `haajimi/Meow` `raw` split。

契約如下：

- `raw` 是正式主分析集。
- `test` 若可讀性有問題或資料損毀，必須顯式標記為 excluded。
- `sft` 與 `rl` 只能做 sensitivity check，不進主結論。

每筆資料至少使用下列欄位：

- `meta`
- `outline`
- `ref_meta`
- `cot`

主結構分析只依賴：

- `meta`
- `outline`

`ref_meta` 只當 confounder / 分層變數。

### 3.2 外部對照 corpus

外部對照語料不是 gold corpus，只是 validation corpus。

契約如下：

- 母體用 Hugging Face 上的 arXiv metadata datasets 建 candidate pool。
- 只納入 AI / CS 相關子領域，避免醫學 review 把 genre effect 和 domain effect 混在一起。
- 候選集先做弱標籤，再嘗試抽 section headings。
- 若只能拿到 section headers，就只做 coarse validation，不與 MEOW full-outline 指標混算。

### 3.3 排除原則

下列情況一律不能被默默當作正式樣本：

- `test` split 解析失敗或明顯 truncation
- 外部樣本無法取得足夠的結構訊息
- 標籤明顯屬於 false positive 類別，但未經人工校驗

## 4. 弱標籤定義

### 4.1 弱標籤層級

預期的弱標籤類別如下：

- `survey`
- `strict_review`
- `broad_review_only`
- `overview/taxonomy`
- `state_of_the_art_or_advances`
- `observational_or_questionnaire_survey`
- `peer/code/reviewer_false_positive`
- `ambiguous`

### 4.2 判斷順序

標籤規則以「先 title，再 `meta.survey_reason`，最後 abstract」為原則。

此外要先處理 false positive：

- `peer review`
- `reviewer`
- `code review`
- `review comments`
- questionnaire / observational survey 類

### 4.3 二分類折疊

弱標籤最後要折疊成兩套二分類。

#### strict

- 正類：`strict_review`
- 負類：`survey`

#### broad

- 正類：`strict_review`
- 正類：`broad_review_only`
- 正類：`overview/taxonomy`
- 正類：`state_of_the_art_or_advances`
- 負類：`survey`

`ambiguous` 與 false positive 類別不得直接進主統計，必須先經過 audit 或明確排除。

## 5. 結構特徵契約

### 5.1 outline canonicalization

若資料已有完整 `outline`，優先直接 canonicalize。

若外部資料只有 heading 列表，則以 coarse outline 方式處理，不與 full outline 同層比較。

### 5.2 feature set

每筆 outline 至少要輸出下列特徵：

- `top_level_count`
- `total_node_count`
- `max_depth`
- `level_counts` (`L1` / `L2` / `L3`)
- `canonical_role_sequence`
- `motif_presence`
- `SR-template score`
- `taxonomy-template score`
- `shape TED`
- `role-sequence edit similarity`
- `top-level lexical similarity`

### 5.3 canonical roles

角色映射建議固定為下列集合：

- `INTRO`
- `BACKGROUND`
- `METHOD`
- `EVIDENCE`
- `TAXONOMY`
- `APPLICATION`
- `CHALLENGE`
- `CLOSE`
- `OTHER`

其中 `Challenges and Future Directions` 一類應優先落在 `CHALLENGE`，不要直接折成 `CLOSE`。

## 6. 統計契約

### 6.1 descriptive stats

報告至少要列出：

- 各類別平均 `outline node` 數
- 平均 `top-level` 數
- `max depth`
- role 頻率
- transition 頻率
- motif 頻率
- entropy

### 6.2 regularity stats

報告至少要列出：

- within-group pairwise similarity 的 mean / variance
- role-sequence entropy
- ending-type entropy
- top-level count variance

### 6.3 stratification

主結論不能只看 pooled。

至少要同時輸出：

- pooled
- stratified

建議 strata 至少包含：

- `domain × year bucket × ref_count bucket`

### 6.4 inference

推論層只允許：

- bootstrap CI
- permutation test

效果量至少提供：

- standardized mean difference
- 或 `Cliff's delta`

## 7. 人工 audit 契約

### 7.1 audit sample

需要建立一個固定 seed 的人工校驗集，規模約 `150–200` 篇。

抽樣必須分層覆蓋：

- `survey`
- `strict_review`
- `overview/state-of-the-art`
- `ambiguous`

### 7.2 audit artifact

audit 結果要固化成可重跑檔案，至少包含：

- 原始抽樣清單
- 人工 adjudicated labels
- 最終 precision / error pattern summary

### 7.3 不能偷換的地方

`meta.survey_reason` 不得被當成 gold label。

它只能當輔助訊號與 audit 參考。

## 8. 期望輸出 artifacts

以下是建議的輸出檔案契約。實作時可依 runner 參數放入 run directory，但檔名語意應維持一致。

### 8.1 manifest 與 corpus snapshot

- `manifest.json`
  - 資料來源 URL
  - split 可用性
  - 下載 / 解析時間戳
  - excluded split 與原因
  - 依賴 fallback 註記

- `corpus_snapshot.json`
  - 主 corpus 與 external corpus 的筆數
  - 解析成功率
  - 抽樣 seed
  - 類別分布

### 8.2 labeling artifacts

- `label_rules.json`
- `label_counts.json`
- `audit_sample.csv`
- `audit_sample.jsonl`
- `audit_adjudicated.csv`
- `audit_adjudicated.jsonl`
- `strict_membership.jsonl`
- `broad_membership.jsonl`

### 8.3 structure artifacts

- `meow_features.jsonl`
- `external_candidates.jsonl`
- `external_structure_features.jsonl`
- `role_transition_counts.json`
- `motif_counts.json`

### 8.4 statistics artifacts

- `summary_stats.json`
- `stratified_stats.json`
- `pairwise_similarity.json`
- `entropy_stats.json`
- `effect_sizes.json`
- `bootstrap_ci.json`
- `permutation_tests.json`

### 8.5 figures

至少應輸出下列圖：

- `genre_counts.png`
- `audit_sankey.png` 或 `audit_stacked_bar.png`
- `role_motif_heatmap.png`
- `within_group_similarity_boxplot.png`
- `clustering.png` 或 `embedding.png`

### 8.6 report

- `report.md`

`report.md` 是主報告入口，應可單獨閱讀，不需要再回頭看程式碼才能理解主結論。

## 9. 報告章節結構

報告建議固定使用以下章節順序：

1. `摘要`
2. `資料來源與排除原則`
3. `弱標籤規則與 audit`
4. `結構特徵定義`
5. `描述性統計`
6. `一致性與 regularity`
7. `分層分析`
8. `外部 validation`
9. `主結論`
10. `限制與後續工作`

其中主結論至少要直接回答三件事：

- strict review vs survey 的平均 outline 差異
- broad review vs survey 的平均 outline 差異
- 分層後結論是否仍成立

## 10. 參數與重跑契約

建議 runner 至少支援下列控制項：

- `--output-dir`
- `--seed`
- `--meow-limit`
- `--external-max-records`
- `--external-sample-per-label`
- `--external-structure-per-label`
- `--audit-per-bucket`
- `--pairwise-max-per-group`
- `--skip-external-structure`
- `--no-figures`

重跑時，若 seed 與輸入版本相同，以下內容應保持穩定：

- label membership
- audit sample
- stratified split
- 主要摘要表

## 11. 限制說明

這份分析有幾個必須明說的限制：

1. `raw` 是主分析集，但不代表它就是無偏的全體母體。
2. 外部 Hugging Face 語料是 validation corpus，不是 gold corpus。
3. 只有完整 outline 的樣本，才能做 full-outline 級比較。
4. 只有 section headers 的外部樣本，只能做 coarse structure check。
5. 弱標籤不是 gold label，必須搭配人工 audit 才能主張 precision。
6. `test` split 若有解析異常，必須明確排除，不能補成正常樣本。

## 12. 文件與實作的邊界

這份文件只規範：

- 輸入定義
- 標籤定義
- 結構特徵
- 統計輸出
- 報告章節

它不負責：

- 實際抓取資料
- 實際跑統計
- 實際產生 figures
- 實際修改 `scripts/` 或 `tests/`

後續若 `scripts/hf_review_survey_outline_analysis.py` 落地，這份文件應作為它的對照契約。
