# SR vs Survey 結構分析報告

日期：2026-04-23
工作區：`/Users/xjp/Desktop/Outline_COT`

## Executive Summary

這份報告回答兩個看似衝突、其實不在同一量尺上的觀察：

1. 用 repo 目前的 MEOW `Structural Distance` 做 `benchmark100` 定量分析時，**不支持**「`strict_review` 的 scaffold 比 `survey` 更標準化」。
2. 但只看四篇本地 SR (`2307.05527`, `2409.13738`, `2511.13936`, `2601.19926`) 的 gold outlines，人眼又會強烈覺得它們的 top-level scaffold 很像，而 model outputs 則有明顯「放飛自我」或 generic survey 化的傾向。

這兩件事可以同時為真。原因是：

- 現有 `Structural Distance` 是 **shape-only ordered tree edit distance**。它只看 `level` 與順序，不看 `title`、`numbering`、`ref`。
- 所以，當你把分析截到 `level = 1` 時，這個 metric 幾乎只是在看「一級章節數量」與 sibling 排列，而不是看 `Introduction -> Method -> Results -> Discussion -> Conclusion` 這種**功能骨架**。
- 你在四篇 SR 上看到的「很像」，主要是 **paper-faithful functional scaffold similarity**；model 的 drift 則主要是 **genre conversion**：把原 paper 的報告型結構改寫成 generic literature review / taxonomy 結構。

一句話版：

> 目前的 quantitative 結果證明不了「SR 比 survey 更同質」，但 qualitative 深讀也清楚顯示：這四篇 SR 的 gold outlines 共享一套相當接近的 paper-faithful top-level scaffold，而 model outputs 的確會穩定漂向 generic review template。

---

## 1. Scope 與資料來源

### 1.1 Quantitative authority

本輪 quantitative 分析使用的權威分組是：

- [`results/benchmark100_manual_outline_audit/official100_agent_protocol_v1_20260418/protocol_v1/report.md`](../results/benchmark100_manual_outline_audit/official100_agent_protocol_v1_20260418/protocol_v1/report.md)
- [`results/benchmark100_manual_outline_audit/official100_agent_protocol_v1_20260418/paper_labels.final.jsonl`](../results/benchmark100_manual_outline_audit/official100_agent_protocol_v1_20260418/paper_labels.final.jsonl)

這份 protocol-v1 的 final authority 給出的 paper-level counts 是：

- `strict_review = 10`
- `survey = 18`
- `excluded = 72`

excluded breakdown:

- `broad_review_only = 12`
- `observational_or_questionnaire_survey = 12`
- `overview/taxonomy = 12`
- `peer/code/reviewer_false_positive = 29`
- `state_of_the_art_or_advances = 7`

### 1.2 Quantitative artifact

本輪 shape-only 統計結果保存在：

- [`results/benchmark100_manual_outline_audit/official100_agent_protocol_v1_20260418/sr_survey_shape_test_20260423/report.md`](../results/benchmark100_manual_outline_audit/official100_agent_protocol_v1_20260418/sr_survey_shape_test_20260423/report.md)
- [`results/benchmark100_manual_outline_audit/official100_agent_protocol_v1_20260418/sr_survey_shape_test_20260423/summary.json`](../results/benchmark100_manual_outline_audit/official100_agent_protocol_v1_20260418/sr_survey_shape_test_20260423/summary.json)

這份 artifact 現在已含三層：

- `full_depth`
- `level<=2`
- `level=1`

### 1.3 Qualitative comparison surfaces

這份報告使用兩組 qualitative evidence：

1. **early main runs**
   - 目的：對齊最早四篇 cross-judge / root-cause thread，也最接近「我一開始只做那四篇時」的語境。
   - representative predicted files:
     - [`results/2307.05527/gpt-5.4-xhigh-3papers/chatgpt_meow_outline_blind.json`](../results/2307.05527/gpt-5.4-xhigh-3papers/chatgpt_meow_outline_blind.json)
     - [`results/2409.13738/gpt-5.4-xhigh-3papers/chatgpt_meow_outline_blind.json`](../results/2409.13738/gpt-5.4-xhigh-3papers/chatgpt_meow_outline_blind.json)
     - [`results/2511.13936/gpt-5.4-xhigh-3papers/chatgpt_meow_outline_blind.json`](../results/2511.13936/gpt-5.4-xhigh-3papers/chatgpt_meow_outline_blind.json)
     - [`results/2601.19926/gpt-5.4-xhigh-2601/chatgpt_meow_outline_blind.json`](../results/2601.19926/gpt-5.4-xhigh-2601/chatgpt_meow_outline_blind.json)
2. **common-run sanity check**
   - 目的：避免 qualitative 只押在不同 run family 上，額外用四篇都共同存在的同一 generation family 再看一遍 drift 是否穩定。
   - representative predicted files:
     - [`results/2307.05527/gpt-5.4-mini-xhigh-4papers/chatgpt_meow_outline_blind.json`](../results/2307.05527/gpt-5.4-mini-xhigh-4papers/chatgpt_meow_outline_blind.json)
     - [`results/2409.13738/gpt-5.4-mini-xhigh-4papers/chatgpt_meow_outline_blind.json`](../results/2409.13738/gpt-5.4-mini-xhigh-4papers/chatgpt_meow_outline_blind.json)
     - [`results/2511.13936/gpt-5.4-mini-xhigh-4papers/chatgpt_meow_outline_blind.json`](../results/2511.13936/gpt-5.4-mini-xhigh-4papers/chatgpt_meow_outline_blind.json)
     - [`results/2601.19926/gpt-5.4-mini-xhigh-4papers/chatgpt_meow_outline_blind.json`](../results/2601.19926/gpt-5.4-mini-xhigh-4papers/chatgpt_meow_outline_blind.json)

四篇 gold outlines 都來自：

- [`data/paper_sets/meow_refs/2307.05527/outline.json`](../../data/paper_sets/meow_refs/2307.05527/outline.json)
- [`data/paper_sets/meow_refs/2409.13738/outline.json`](../../data/paper_sets/meow_refs/2409.13738/outline.json)
- [`data/paper_sets/meow_refs/2511.13936/outline.json`](../../data/paper_sets/meow_refs/2511.13936/outline.json)
- [`data/paper_sets/meow_refs/2601.19926/outline.json`](../../data/paper_sets/meow_refs/2601.19926/outline.json)

---

## 2. Quantitative Results

### 2.1 主表

| split | SR n | survey n | SR within mean | survey within mean | between mean | survey-SR | between-SR | between-survey | benchmark mean-distance acc | p(within diff) | p(separation gap) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `full_depth__benchmark_strict_review_vs_survey` | 10 | 18 | 0.5410 | 0.5004 | 0.5036 | -0.0406 | -0.0375 | 0.0032 | 0.3214 | 0.8114 | 0.9670 |
| `full_depth__benchmark_strict_review_plus_local4_vs_survey` | 14 | 18 | 0.5360 | 0.5004 | 0.5064 | -0.0356 | -0.0296 | 0.0060 | 0.3571 | 0.7906 | 0.9266 |
| `level_le_2__benchmark_strict_review_vs_survey` | 10 | 18 | 0.4362 | 0.4072 | 0.4172 | -0.0290 | -0.0191 | 0.0099 | 0.5714 | 0.7988 | 0.5623 |
| `level_le_2__benchmark_strict_review_plus_local4_vs_survey` | 14 | 18 | 0.4363 | 0.4072 | 0.4214 | -0.0291 | -0.0149 | 0.0142 | 0.6071 | 0.7758 | 0.4267 |
| `level_1__benchmark_strict_review_vs_survey` | 10 | 18 | 0.1715 | 0.0987 | 0.1395 | -0.0727 | -0.0319 | 0.0408 | 0.7500 | 0.9484 | 0.2058 |
| `level_1__benchmark_strict_review_plus_local4_vs_survey` | 14 | 18 | 0.2031 | 0.0987 | 0.1578 | -0.1044 | -0.0453 | 0.0591 | 0.7500 | 0.9876 | 0.1352 |

### 2.2 最重要的定量結論

最強、最穩的 quantitative conclusion 是：

1. 六個分析裡 `survey_minus_sr` **全部為負**。
   - 這代表 `survey` 的組內平均 shape distance 在所有設定下都比 `strict_review` 更小。
   - 換句話說，依這個 metric 看，`survey` 反而更像彼此。
2. 六個分析裡 `between_minus_sr` **全部為負**。
   - 這代表組間距離從來沒有大到超過 SR 組內距離。
   - 所以也談不上清晰的 `strict_review` vs `survey` 結構分離。
3. 最有訊號的是 `level=1` 的 top-level 結果。
   - `benchmark_mean_distance_acc = 0.75`
   - 這顯示最淺層的 top-level structure 的確有一點 group signal。
   - 但注意：這不等於「SR 比 survey 更標準化」，只代表 top-level sibling count/shape 有一些可分性。

### 2.3 邊界樣本 caveat

主測試的 `strict_review` 裡保留了一個明確的邊界樣本：

- `benchmark:55`
- `needs_audit = True`
- 已在 [`sr_survey_shape_test_20260423/report.md`](../results/benchmark100_manual_outline_audit/official100_agent_protocol_v1_20260418/sr_survey_shape_test_20260423/report.md) 中標出

此外，本輪對 `benchmark:55`，以及更保守地同時排除 `benchmark:55` / `benchmark:74` 做過 session 內 sanity check；方向都沒有翻轉，也就是 `survey within mean < SR within mean` 仍成立。這表示主結論不是由單一邊界樣本撐起來的。

---

## 3. 為什麼純 Shape Metric 和「四篇 gold 很像」會打架

這是整份分析最重要的概念釐清。

### 3.1 目前的 metric 實際在量什麼

repo 目前的 `Structural Distance` 是：

- `shape-only`
- `ordered`
- `tree edit distance`
- 只看 section `level`
- 不看 section `title`
- 不看 numbering、references、paper semantics

也就是說，它衡量的是：

> 標題樹的幾何形狀有多像

它**不是**在衡量：

> `Introduction -> Method -> Results -> Discussion -> Conclusion` 這種功能骨架有多像

### 3.2 在 `level=1` 時，metric 幾乎只剩「章節數量」

當 outline 被截到 `level = 1` 時，每份 outline 都退化成：

- 一個 root
- 底下若干平鋪的一級章節

這時候 pure shape-only TED 幾乎只會對：

- 一級章節總數
- flat sibling 的插刪成本

敏感。

它看不到下列差異：

- `Methods` vs `Review Protocol`
- `Results` vs `Datasets, Benchmarks, and Evaluation`
- `Discussion` vs `Open Challenges and Future Directions`

因此，對於你真正觀察到的四篇 phenomenon，`level=1` shape-only metric 本身就不是充分表徵。

### 3.3 一個最直觀的反例：`2409.13738`

對 early main representative runs 而言：

- `2409.13738` gold 的 top-level count = `10`
- `2409.13738` predicted 的 top-level count = `10`

因此，`level=1` shape distance 竟然是：

- `0.0`

但從語義上看，這一篇其實是 qualitative drift 非常明顯的例子：

- gold 保留了 `Methods -> Results -> NLP -> Process Model Generation -> Process Extraction Evaluation -> Discussion -> Threats/Limitations`
- predicted 則被改寫成 `Review Protocol -> Rule-based Methods -> Machine Learning Methods -> Deep Learning -> LLMs -> Evaluation Ecosystem -> Open Challenges`

也就是說：

> `level=1` shape distance 在這裡給出「完全不漂移」的訊號，但人工閱讀卻會判定為明顯 genre conversion。

這正是本輪 quantitative / qualitative tension 的最佳示範。

---

## 4. Four-Paper 第一層：定量與直覺為何相反

### 4.1 Early main representative predicted files 的 L1 結果

以 early main representative predicted files 計算 `level=1` shape-only distance：

#### 四篇 gold 彼此之間

- pairwise mean L1 shape distance = `0.3279`

#### 四篇 representative predicted 彼此之間

- pairwise mean L1 shape distance = `0.1594`

#### gold vs pred per paper

| paper | gold L1 count | pred L1 count | gold-vs-pred L1 shape distance |
| --- | ---: | ---: | ---: |
| `2307.05527` | 6 | 7 | 0.1250 |
| `2409.13738` | 10 | 10 | 0.0000 |
| `2511.13936` | 7 | 8 | 0.1111 |
| `2601.19926` | 4 | 9 | 0.5000 |

這組數字非常重要。它告訴我們：

1. 如果只看 `level=1` 的 flat tree geometry，四篇 predicted outlines 反而比四篇 gold 更像彼此。
2. 這不是因為 predicted 更 faithful，而是因為它們更容易收斂到**同一種 generic review template**。
3. `2409.13738` 的 `0.0` 是最典型的反例：shape 沒變，但 genre 已經變了。

### 4.2 Common-run sanity check

用四篇都共同存在的 `gpt-5.4-mini-xhigh-4papers` 再做一次相同檢查，pairwise predicted L1 shape distance 的 mean 仍是：

- `0.1594`

這表示：

> 「predicted outlines 在第一層更像彼此」不是單一路徑的偶然，而是穩定出現的 generic template convergence。

---

## 5. Four-Paper Qualitative Analysis

### 5.1 四篇 gold 共享的是什麼

四篇 gold 共享的，不是同名章節，而是相當清楚的 **paper-faithful functional scaffold**：

- `Introduction`
- 背景 / related work / 問題設定
- 明確的 `Method` / `Methods` / review design section
- 明確的 `Results` / evidence-bearing section
- `Discussion` / `Limitations` / `Threats to Validity`
- `Conclusion`

也就是說，它們的共同點是：

> 仍然保留了「原 paper 的報告型敘事順序」

而不是：

> 把整個 literature 重排成 taxonomy-oriented field survey

### 5.2 四篇 predicted 共享的是什麼

四篇 predicted outlines 共享的則是另一套非常穩定的 genre scaffold：

- `Introduction`
- `Review Methodology` / `Review Protocol` / `Systematic Review Design`
- 若干主題式或方法家族式章節
- `Challenges` / `Limitations` / `Future Directions`
- `Conclusion`

這套 scaffold 的核心不是 faithful reconstruction，而是：

> generic literature review writing template

所以 qualitative drift 的根本不是某一兩個 section title 偏掉，而是：

- **review-method insertion**
- **taxonomy / theme expansion**
- **future-direction boilerplate**
- 最終把 paper-faithful scaffold 改寫成 field-survey scaffold

---

## 6. Per-Paper Deep Reading

以下 qualitative deep reading 以 early main representative predicted files 為主；最後再用 common-run sanity check 補強「這不是單一路徑偶然」。

### 6.1 `2307.05527`

#### Gold top-level scaffold

- `Introduction`
- `Background and Definitions`
- `Data and Methodology`
- `Analysis and Results`
- `Discussion`
- `Conclusion`

#### Representative predicted top-level scaffold

- `Introduction`
- `Systematic Review Design`
- `Technical Landscape of Generative Audio`
- `Major Ethical Implications of Generative Audio Models`
- `Mitigation Strategies and Governance Mechanisms`
- `Open Challenges and Future Research Directions`
- `Conclusion`

#### Drift diagnosis

這篇的 drift 不是簡單加了一章，而是把單一的 `Analysis and Results` 主體拆成若干平行主題章：

- `Technical Landscape`
- `Ethical Implications`
- `Mitigation / Governance`
- `Open Challenges`

也就是把原本 paper-faithful 的 evidence-bearing 主體，改寫成了 field survey 式的 topical decomposition。

最核心的漂移類型：

- `review-method insertion`
- `taxonomy/theme expansion`
- `future directions endcap`

### 6.2 `2409.13738`

#### Gold top-level scaffold

- `Introduction`
- `Related Work`
- `Methods`
- `Results`
- `Natural Language Processing`
- `Process Model Generation`
- `Process Extraction Evaluation`
- `Discussion`
- `Threats to Validity and Limitations`
- `Conclusion`

#### Representative predicted top-level scaffold

- `Introduction`
- `Background`
- `Review Protocol`
- `Rule-based Methods`
- `Machine Learning Methods`
- `Deep Learning and Pre-trained Language Models`
- `Large Language Models for Process Extraction and BPM`
- `Evaluation Ecosystem`
- `Open Challenges and Future Directions`
- `Conclusion`

#### Drift diagnosis

這篇最清楚地展示了：

> 不是只差一點，而是 genre 被換掉了。

gold 仍然保留了非常強的 paper/report structure：

- `Methods`
- `Results`
- domain-specific functional chapters
- `Discussion`
- `Threats to Validity`

predicted 則把它壓成一條標準的 technology taxonomy：

- `Review Protocol`
- `Rule-based`
- `ML`
- `DL`
- `LLMs`
- `Evaluation Ecosystem`
- `Challenges/Future`

因此，這篇是最能說明「shape-only metric 會錯看」的例子：

- `level=1` shape 可接近甚至為零差
- 但 semantic scaffold 已經大幅漂移

### 6.3 `2511.13936`

#### Gold top-level scaffold

- `Introduction`
- `Background`
- `Methods`
- `Results`
- `Discussion`
- `Limitations`
- `Conclusion`

#### Representative predicted top-level scaffold

- `Introduction`
- `Methodology of the Systematic Analysis`
- `Foundations of Preference-Based Learning`
- `Preference-Based Learning for Audio Understanding`
- `Preference-Based Learning for Audio Generation and Interaction`
- `Datasets, Benchmarks, and Evaluation`
- `Open Challenges and Future Directions`
- `Conclusion`

#### Drift diagnosis

這篇是最典型的 `taxonomy expansion`：

- gold 的 `Background / Results / Discussion` 被提升、拆散成多個 thematic first-level chapters
- 之後再補上一個非常 textbook 的 `Open Challenges and Future Directions`

也就是說，predicted outline 讀起來不像在 faithful 地重建 paper 的報告結構，而像在替這個 topic 寫一份更通用的 survey。

### 6.4 `2601.19926`

#### Gold top-level scaffold

- `Introduction`
- `Method`
- `Results`
- `Discussion & Conclusion`

#### Representative predicted top-level scaffold

- `Introduction`
- `Review Design and Conceptual Framework`
- `Main Interpretability Paradigms`
- `What Syntax Do Language Models Encode?`
- `What Shapes Syntactic Knowledge?`
- `Multilingual and Cross-Lingual Syntax`
- `Methodological Tensions and Evaluation Pitfalls`
- `Synthesis and Future Directions`
- `Conclusion`

#### Drift diagnosis

這篇是四篇裡 drift 最重的一篇，也是最乾淨的 mismatch exemplar。

gold 是一份非常緊、非常 paper-faithful 的 `RQ-driven review`：

- `Method`
- `Results`
- `Discussion & Conclusion`

其中 `Results` 內部直接按 `RQ1 / RQ2 / RQ3` 展開。

predicted 則幾乎完全改寫成 field-map 式 survey taxonomy：

- `Review Design`
- `Conceptual Foundations`
- `Interpretability Paradigms`
- `Syntactic Phenomena`
- `Multilingual Syntax`
- `Methodological Debates`
- `Future Directions`

它不只是「多幾章」，而是把：

- `RQ-driven synthesis`

變成：

- `topic-centered literature map`

這正是為什麼這篇的 structural mismatch 最嚴重。

---

## 7. 綜合判斷

### 7.1 對最初問題的直接回答

如果問題是：

> 「SR 的 outline section 架構是否比 survey 更接近？」

那麼答案要分成兩句：

1. **用 repo 目前的 MEOW shape-only structural metric，不能這樣說。**
   - 現有 quantitative 結果沒有支持這個結論。
   - 反而在所有 split 中，`survey` 的組內平均 shape distance 更小。
2. **但你在四篇 SR 上看到的 qualitative 現象是真實存在的。**
   - 這四篇 gold 共享的是 `paper-faithful functional scaffold`
   - model outputs 共享的是 `generic literature review scaffold`
   - 這兩件事不矛盾，只是目前 metric 沒有量到你真正看到的東西

### 7.2 這輪最重要的新認識

本輪最值得保留的 insight 不是某個單一 p-value，而是：

> 在 `level=1` 下，predicted outlines 比 gold outlines 更像彼此，這不是因為它們更 faithful，而是因為它們更容易收斂到 generic review template。

換句話說，model 的「放飛自我」不是完全無規則亂飛；恰恰相反，它是：

- 有規律地
- 穩定地
- 朝同一種 survey-genre template 收斂

### 7.3 這代表什麼

如果後續要真的量化你在四篇 SR 上看到的現象，下一步不應該再只做 pure shape-only TED，而應該改成：

1. **top-level functional-role sequence metric**
   - 例如：`INTRO -> METHOD -> EVIDENCE -> DISCUSSION/LIMITATION -> CLOSE`
2. **paper-faithful vs generic-review scaffold classifier**
   - 看 prediction 是否插入：
     - `Review Methodology/Protocol`
     - 多個平行 taxonomy chapters
     - `Challenges/Future Directions` boilerplate
3. **gold-vs-pred first-layer role preservation**
   - 問的不是「章數差多少」
   - 而是：
     - `Results` 是否保住
     - `Discussion / Limitations` 是否保住
     - `RQ-driven / paper-driven scaffold` 是否被 topic taxonomy 取代

---

## 8. Final Answer

本輪可以收斂成一個非常清楚的最終結論：

- `benchmark100` 的 quantitative analysis 不支持「SR 比 survey 更同質」。
- 但四篇本地 SR 的 qualitative analysis 清楚顯示，gold outlines 的 top-level scaffold 確實更接近 paper-faithful report structure。
- model predictions 並非純隨機失控，而是穩定地漂向 generic literature review / taxonomy template。
- 因此，你最初看到的現象是對的；錯的不是觀察，而是拿目前這個 pure shape-only metric 去量那個觀察。
