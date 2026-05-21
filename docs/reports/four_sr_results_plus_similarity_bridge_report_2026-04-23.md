# 四篇 SR 結果與相似度分析整合報告

日期：`2026-04-23`
工作區：`/Users/xjp/Desktop/Outline_COT`

## 摘要

這份報告要把兩條原本分開的分析線接起來：

1. 四篇本地 SR 在 `results/` 裡的實際 blind outline 結果，到底哪個 run 最好，abstract ablation 有沒有幫助，模型又是怎麼偏掉的。
2. 後來做的 `SR vs survey` 章節名稱相似度分析，到底有沒有支持「這四篇 gold 看起來很像」這個直覺。

最短的結論是：

- 四篇 paper 的實際結果顯示，最佳 run 並不一致，abstract 也不是普遍利多。
- 但四篇 gold 的確共享一套很接近的報告式骨架，而模型大綱常漂向通用 survey / taxonomy 模板。
- 後來的 title similarity 分析部分支持了這個直覺：如果看章節名稱而不是 pure shape，`SR` 的確比 `survey` 更像彼此，尤其在 `all_layers`。

所以，這兩條線不是互相衝突，而是在回答不同層次的問題：

- 四篇結果線回答的是：**模型實際產出了什麼，哪裡偏了，哪個版本最好。**
- 相似度分析線回答的是：**你一開始看到的「四篇 gold 很像」能不能被量化。**

## 1. 第一條主線：四篇 SR 的實際結果

這條主線的主報告是：

- [docs/sr_outline_results_guide_2026-04-16_zh.md](./sr_outline_results_guide_2026-04-16_zh.md)

根據那份報告，全量重算後的四篇最新結果如下：

| Paper | 最新 score-best | 最新 SR-aware best | 是否一致 |
| --- | --- | --- | --- |
| `2307.05527` | `gpt-5.4-xhigh-3papers` | `gpt-5.4-xhigh-3papers` | 一致 |
| `2409.13738` | root blind output | root blind output | 一致 |
| `2511.13936` | `ablation_no_meta_abstract` | `ablation_no_meta_abstract` | 一致 |
| `2601.19926` | `ablation_with_meta_abstract` | `ablation_with_meta_abstract` | 一致 |

這張表很重要，因為它直接說明：

- 這四篇不能用單一 run 設定通吃。
- 其中兩篇的最佳結果來自 abstract ablation，但另外兩篇不是。

### 1.1 abstract ablation 的總表

| Paper | `no_meta_abstract` Avg / SD | `with_meta_abstract` Avg / SD | 判讀 |
| --- | --- | --- | --- |
| `2307.05527` | `7.3333 / 0.4000` | `8.0000 / 0.3784` | abstract 強化 methodology 與 literature framing，但仍未改寫全局最佳 |
| `2409.13738` | `7.7500 / 0.4286` | `7.2500 / 0.2903` | abstract 降低 structural distance，但更像規整 taxonomy |
| `2511.13936` | `8.2500 / 0.4130` | `6.3333 / 0.3250` | abstract 將 evidence 收窄到 generative alignment 故事線，反而退化 |
| `2601.19926` | `6.2500 / 0.8431` | `8.6667 / 0.7647` | abstract 明顯重建 background / method / findings / limits / future |

這裡最值得記住的不是哪個數字最大，而是：

- abstract 不是普遍利多
- 它只在某些 paper 能把 outline 拉回 SR 節奏

### 1.2 四篇逐篇的一句話版結果

- `2307.05527`
  - 最佳仍是 `gpt-5.4-xhigh-3papers`
  - abstract 有幫助，但主要是 methodology 更顯式，沒有改寫全局最佳

- `2409.13738`
  - 最佳仍是 root blind output
  - abstract 雖讓 structure distance 變低，但更像平均用力的規整 taxonomy

- `2511.13936`
  - 最佳是 `ablation_no_meta_abstract`
  - abstract 反而把 evidence 收窄，讓 coverage 退化

- `2601.19926`
  - 最佳是 `ablation_with_meta_abstract`
  - abstract 是四篇裡最明顯的正例，明確把大綱拉回 SR 節奏

## 2. 第二條主線：四篇結果到底在說什麼

這條主線的根因報告是：

- [docs/cross_judge_score_root_cause_report_2026-04-09.md](./cross_judge_score_root_cause_report_2026-04-09.md)

那份報告的核心不是「模型普遍很差」，而是：

- blind generation 的任務是根據 `title + ref_meta` 寫一份合理的 literature review outline
- evaluation gold 卻是 `data/paper_sets/meow_refs/<paper_id>/outline.json`，也就是 paper-faithful 的真實章節骨架

這兩件事本來就不是同一件事。

### 2.1 最典型的 mismatch

最典型的是 `2409.13738` 和 `2601.19926`：

- `2409.13738`
  - gold 仍保留 `Methods -> Results -> Evaluation -> Discussion -> Threats/Limitations`
  - predicted 常被改寫成 `Review Protocol -> Rule-based / ML / Deep Learning / LLMs -> Challenges -> Future`

- `2601.19926`
  - gold 只有 `4` 個一級章節
  - blind generation 卻傾向產生 `9` 到 `10` 個一級章節的完整 taxonomy 式 survey

所以這條主線的最重要結論是：

> 真正的 drift 不是只差幾個標題，而是整個 outline 從 paper-faithful report scaffold 漂到 generic review scaffold。

## 3. 第三條主線：為什麼你會覺得四篇 gold 很像

這條主線的相關報告有兩份：

- [docs/sr_vs_survey_quant_qual_report_2026-04-23.md](./sr_vs_survey_quant_qual_report_2026-04-23.md)
- [results/benchmark100_manual_outline_audit/official100_agent_protocol_v1_20260418/sr_survey_title_similarity_test_20260423/report.md](../results/benchmark100_manual_outline_audit/official100_agent_protocol_v1_20260418/sr_survey_title_similarity_test_20260423/report.md)

這裡的關鍵是先把兩種 metric 分開：

- MEOW 現行 `Structural Distance` 只看 tree shape
- 新做的 title similarity 會看章節名稱的重疊

### 3.1 title similarity 的主結果

| 分析版本 | `SR` 組內平均 | `survey` 組內平均 | 組間平均 | `SR - survey` |
| --- | ---: | ---: | ---: | ---: |
| 全層級，benchmark100 | `0.1223` | `0.0978` | `0.0954` | `+0.0244` |
| 全層級，SR 加本地四篇 | `0.1313` | `0.0978` | `0.0983` | `+0.0335` |
| 只看第一層，benchmark100 | `0.3262` | `0.3225` | `0.2855` | `+0.0037` |
| 只看第一層，SR 加本地四篇 | `0.3472` | `0.3225` | `0.2870` | `+0.0247` |

這張表的最重要解讀是：

- 如果看 `all_layers`，`SR` 比 `survey` 更像彼此，方向很清楚
- 如果只看 `level_1`，benchmark100 幾乎打平，但把本地四篇加進去後也轉成 `SR` 較高

### 3.2 本地四篇的親和性

把本地四篇 SR 個別拿去和兩群比較，四篇都更接近 `SR`：

| paper | 對 `SR` 平均相似度 | 對 `survey` 平均相似度 | 判定較像哪一群 |
| --- | ---: | ---: | --- |
| `2307.05527` | `0.4420` | `0.3595` | `SR` |
| `2409.13738` | `0.3313` | `0.2186` | `SR` |
| `2511.13936` | `0.4094` | `0.3145` | `SR` |
| `2601.19926` | `0.3164` | `0.2710` | `SR` |

也就是說，你最初感受到的「這四篇 gold 很像」，並不是錯覺。

## 4. 這兩條主線怎麼接起來

這裡最容易混亂，所以直接講結論。

### 4.1 它們不矛盾

四篇結果線告訴我們：

- 模型實際會從報告型骨架漂到通用綜述模板

title similarity 線則告訴我們：

- 如果看章節名稱而不是 pure shape，`SR` 的確比 `survey` 更像彼此

所以這兩條線不是互相打架，而是前後呼應。

### 4.2 它們各自回答不同問題

- 四篇結果線：
  - 哪個 run 最好？
  - abstract 有沒有幫助？
  - 哪篇 drift 最重？
  - 具體 drift 長什麼樣？

- similarity 線：
  - 你一開始看到的「四篇 gold 很像」能不能被量化？
  - 這個現象是在第一層就很強，還是主要在整份 outline？

### 4.3 合起來之後的最穩妥說法

最穩妥的整體說法是：

> 四篇本地 SR 的 gold outlines 共享一套接近的報告式骨架；blind generation 的輸出則常漂向通用綜述 / taxonomy 模板。後來的 title similarity 分析部分支持了這個直覺，尤其在整份 outline 的章節名稱層更明顯。

## 5. 這份整合報告應該怎麼做成投影片

如果要做 deck，主線應該是：

1. 先講四篇 paper 的實際結果
2. 再講 abstract ablation 為何不是普遍利多
3. 接著講四篇共同的 drift pattern
4. 最後再用 similarity 分析回答「為什麼你會覺得它們很像」

不能反過來。因為 similarity 分析只是補強，不是主體。

## 6. 最後結論

如果只留三句話：

1. 四篇本地 SR 的最佳 run 不一致，abstract 也不是普遍利多。
2. 模型最常見的偏移，是把 paper-faithful report scaffold 改寫成 generic review / taxonomy scaffold。
3. 後來的 title similarity 分析沒有推翻這個觀察，反而補充證明：只要看章節名稱，`SR` 的確比 `survey` 更像彼此，尤其在 `all_layers`。
