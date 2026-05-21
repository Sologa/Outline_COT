# SR 架構規整性與 MEOW 資料結構報告

更新日期：2026-04-16

## 摘要

這份報告回答三個問題：

1. `data/paper_sets/meow_refs/` 裡所有 paper 的 gold outline，是否大多都像我們剛剛看的四篇 SR 一樣規整？
2. Hugging Face 上 MEOW 原篇釋出的 data，survey 的結構是否也跟 SR 一樣規整？
3. 若要統計這類「架構規格相似度」，應該怎麼定義、怎麼量化、怎麼做 dataset-level 統計？

先講結論：

- 是，`data/paper_sets/meow_refs/` 這批 gold outline 的規整性確實很高，但這不是只因為那四篇特殊；更大的原因是 **整個 `data/paper_sets/meow_refs/*/outline.json` corpus 幾乎本來就是 SR/review corpus**。
- 具體地說，`data/paper_sets/meow_refs/` 目前有 `13` 份 `outline.json`；其中 `12/13` 的 title 明寫 `systematic`，剩下 `1/13` 也是 `A Review`。
- 但 Hugging Face 的 MEOW dataset 不一樣。HF dataset 本體是 [`haajimi/Meow`](https://hf.co/datasets/haajimi/Meow)，而 repo 內可見的 released mirror sample `surveyX_dataset/` 主要是 **general survey**，不是純 SR；`human` outline 很多樣，`llm` outline 則明顯模板化。
- 因此，你現在看到「gold 很整齊、best 很像 generic taxonomy」這件事，背後其實是兩層分布不一致：
  - `data/paper_sets/meow_refs/` gold 偏 SR/review corpus
  - MEOW released survey sample 偏 general survey，且 model output 更模板化

---

## 0. 資料來源與限制

### 0.1 本地 `data/paper_sets/meow_refs/` corpus

本次完整讀了 `data/paper_sets/meow_refs/*/outline.json`。目前共有 `13` 份：

- `2306.12834`
- `2307.05527`
- `2310.07264`
- `2312.05172`
- `2401.09244`
- `2405.15604`
- `2409.13738`
- `2503.04799`
- `2507.07741`
- `2507.18910`
- `2510.01145`
- `2511.13936`
- `2601.19926`

### 0.2 Hugging Face / MEOW released data

我用 Hugging Face plugin 找到 MEOW paper 與資料集：

- paper: `Meow: End-to-End Outline Writing for Automatic Academic Survey`
- HF dataset: [`haajimi/Meow`](https://hf.co/datasets/haajimi/Meow)

plugin 回傳的 dataset metadata 顯示：

- tag：`arxiv:2509.19370`
- size：`1K<n<10K`
- 類型：`text-generation`

但 repo 內目前可直接檢查的 MEOW mirror 並不是整個 HF dataset，而是小樣本：

- `third_party/repos/Meow-Data-curation/surveyX_dataset/human.jsonl`
- `third_party/repos/Meow-Data-curation/surveyX_dataset/llm.jsonl`

兩者各 `14` 筆，且 title set 完全對齊，所以本報告對「MEOW released data」的結論，要精確講成：

> 對 repo 內可見的 released mirror sample 做結構分析。

---

## 1. `data/paper_sets/meow_refs/` 全量 outline：是否大多都像 SR？

### 1.1 最重要的先驗：這整批 paper 幾乎本來就是 SR/review

對 `13` 份有 `outline.json` 的 `data/paper_sets/meow_refs/` paper 而言：

- `12/13` 的 title 含 `systematic`
- `1/13` 的 title 雖不含 `systematic`，但仍是 `A Review`

也就是說，`data/paper_sets/meow_refs/` 這批 gold 本身就不是「一般 survey + SR 混合 corpus」，而是 **幾乎全 review / SR corpus**。

所以你觀察到「四篇 SR 很一致」這件事，本質上很可能不是四篇特例，而是 **整個 `data/paper_sets/meow_refs/` selection 本來就偏向 systematic/review writing convention**。

### 1.2 全量統計

對 `13` 份 `data/paper_sets/meow_refs/*/outline.json` 的頂層結構做統計後：

- `13/13` 有 `Introduction`
- `13/13` 有 `Method` / `Methodology` / `Survey Methodology` / `Scope & Methodology` 等 method-like container
- `13/13` 有 `Discussion` / `Challenges` / `Future Directions` / `Conclusion` / `Epilogue` 這類收束 container
- `10/13` 有明確 evidence-oriented container，例如：
  - `Results`
  - `Evaluation`
  - `Datasets`
  - `Natural Language Processing`
  - `Process Model Generation`
  - `Foundations of RAG`
- 只有 `4/13` 直接明寫 `Results`

所以，如果用狹義 IMRaD 去看，並不是每篇都長得一樣；但如果用較寬鬆的 SR/review scaffold 去看，大約 `10/13` 都落在：

`Introduction -> Method-like block -> evidence/topic synthesis block -> discussion/future/conclusion`

### 1.3 頂層 section 的共同骨架

最常見的頂層 section token：

| Token | 次數 |
| --- | ---: |
| `Introduction` | `13` |
| `Conclusion` | `10` |
| `Methodology` | `4` |
| `Discussion` | `4` |
| `Results` | `3` |
| `Limitations` | `2` |
| `Survey Methodology` | `2` |
| `Challenges and Future Directions` | `2` |
| `Related Work` | `2` |
| `Methods` | `2` |
| `Background` | `2` |

補充兩個分布：

- 頂層 section 數分布：`6` 章最多（`5` 篇），其次是 `8` 章（`3` 篇）
- 最大層級深度：`11/13` 到 level 3，只有 `2/13` 停在 level 2

也就是說，這批 gold 不只 function order 相對穩，連「大概幾章、會不會拆到三級」都相當規整。

### 1.4 全量逐篇 inventory

| Paper | Top-level sections | Top-level count | 粗分類 | Method-like | Results/evidence-like | Discussion/future/conclusion |
| --- | --- | ---: | --- | --- | --- | --- |
| `2306.12834` | `introduction` / `Methodology` / `Techniques used in the literature for Analysing EHR` / `Analysis of the literature` / `Research Viewpoint` / `Conclusion` | `6` | review-like，偏 narrative synthesis | 是 | 弱 | 是 |
| `2307.05527` | `Introduction` / `Background and Definitions` / `Data and Methodology` / `Analysis and Results` / `Discussion` / `Conclusion` | `6` | SR-like | 是 | 強 | 是 |
| `2310.07264` | `Introduction` / `Search Strategy` / `Classification based on Clinical Techniques` / `Classification based on AI Techniques` / `Discussion` / `Limitations` / `Suggested solutions` / `Conclusion` | `8` | SR-like，topic synthesis | 是 | 中 | 是 |
| `2312.05172` | `Introduction` / `Survey Methodology` / `Sentence Compression` / `Sentence Splitting` / `Challenges and Limitations` / `Conclusions` | `6` | review-like，compact | 是 | 弱 | 是 |
| `2401.09244` | `Introduction` / `Background and Related Work` / `Survey Methodology` / `Multilingual Hate Speech Datasets` / `Cross-lingual Resources` / `Cross-lingual Transfer Approaches` / `Challenges and Future Directions` / `Conclusion` | `8` | SR-like | 是 | 強 | 是 |
| `2405.15604` | `Introduction` / `Methodology` / `Text Generation Tasks` / `Evaluation` / `Related Challenges` / `Epilogue` | `6` | SR-like | 是 | 強 | 是 |
| `2409.13738` | `Introduction` / `Related Work` / `Methods` / `Results` / `Natural Language Processing` / `Process Model Generation` / `Process Extraction Evaluation` / `Discussion` / `Threats to Validity and Limitations` / `Conclusion` | `10` | SR-like，最典型 | 是 | 很強 | 是 |
| `2503.04799` | `Introduction` / `Background` / `Methodology` / `Datasets` / `Feature Extraction` / `Major ML Models` / `ML Techniques` / `Challenges` / `Future Directions` / `Conclusion` | `10` | review-like / taxonomy-aware | 是 | 強 | 是 |
| `2507.07741` | `Introduction` / `Scope & Methodology` / `Languages & Datasets` / `ASR Modeling Choices` / `Training & Evaluation` / `Best Performing Models` / `Discussion: Challenges & Opportunities` / `Conclusion` | `8` | SR-like | 是 | 強 | 是 |
| `2507.18910` | `Introduction` / `Methodology` / `Foundations of RAG` / `Year-by-Year Progress in RAG` / `RAG for Proprietary Data - Industry Implementation` / `Evaluation of RAG Systems` / `Challenges of RAG` / `Discussion and Future Direction` / `Conclusion` | `9` | SR-like / review-like hybrid | 是 | 強 | 是 |
| `2510.01145` | `Introduction` / `Related Work` / `Research Methodology` / `Study Characteristics` / `Challenges and Future Directions` / `Conclusion` | `6` | review-like，compact | 是 | 弱 | 是 |
| `2511.13936` | `Introduction` / `Background` / `Methods` / `Results` / `Discussion` / `Limitations` / `Conclusion` | `7` | SR-like | 是 | 很強 | 是 |
| `2601.19926` | `Introduction` / `Method` / `Results` / `Discussion & Conclusion` | `4` | SR-like，極簡 RQ-driven | 是 | 很強 | 是 |

### 1.5 這批 gold 到底有多「一致」？

答案是：**一致，但不是每篇都同一張模板。**

更精確地說，它們共享的是「review writing convention」，不是單一字面 template。

共同點：

- 幾乎必有 `Introduction`
- 幾乎必有 method/protocol/search block
- 幾乎必有一個中段 evidence/topic synthesis block
- 幾乎必有收尾 block（`Discussion` / `Limitations` / `Challenges` / `Future Directions` / `Conclusion`）

差異點：

- 有些篇用明確 `Results`（如 `2409.13738`, `2511.13936`, `2601.19926`）
- 有些篇不用 `Results`，而是直接把 evidence 攤成 topic/evaluation/dataset 容器（如 `2401.09244`, `2503.04799`, `2507.18910`）
- 有些篇極簡（如 `2601.19926`），有些篇展開很細（如 `2507.18910`, `2409.13738`）

### 1.6 對你原問題的直接回答

> 「之所以這四篇的架構都那麼一致，會不會是因為他們都是 SR？」

是，而且不只那四篇。
因為 `data/paper_sets/meow_refs/*/outline.json` 這整批本來就幾乎都是 systematic/review papers，所以你看到的規整性，很大一部分其實是 **corpus selection effect**。

更保守地講：

- 這四篇不是離群地規整
- `data/paper_sets/meow_refs/` 裡多數 paper 都共享類似的 review scaffold
- 但它們不是單一 hard template，而是同一族 review/SR writing convention 的不同變體

---

## 2. Hugging Face / MEOW data：survey 是否也像 SR 一樣規整？

### 2.1 HF dataset 本體

Hugging Face plugin 找到的 MEOW released dataset 是：

- [`haajimi/Meow`](https://hf.co/datasets/haajimi/Meow)

已知 metadata：

- 對應 paper：`arxiv:2509.19370`
- size tag：`1K<n<10K`
- task：`text-generation`

### 2.2 repo 內可直接檢查的 released mirror sample

本地 mirror 中最清楚的 outline-bearing files 是：

- `third_party/repos/Meow-Data-curation/surveyX_dataset/human.jsonl`
- `third_party/repos/Meow-Data-curation/surveyX_dataset/llm.jsonl`

兩者都是 `14` 筆，而且 title set 完全一致，所以可以直接做 paired comparison。

title 類型分布：

- `12/14` title 含 `Survey`
- `2/14` title 含 `Systematic`

換句話說，這個 sample **不是純 SR sample**，而是以 general survey 為主、少量 systematic review/scoping review 混入。

### 2.3 `human.jsonl`：人類 survey outline 並不特別規整

`human.jsonl` 的結構特徵：

- `n = 14`
- 平均 top-level section 數：`5.57`
- 中位數 top-level section 數：`6`
- 範圍：`0` 到 `8`

marker presence：

- 有 `Introduction`：`10/14`
- 有 `Background`：`2/14`
- 有 `Methods/Methodology`：`2/14`
- 有 `Results/Evaluation/Findings`：`5/14`
- 有 `Future`：`6/14`
- 有 `Conclusion`：`10/14`
- 有 `RQ`：`1/14`

最重要的是它的 top-level pattern 幾乎一筆一種，沒有明顯單一模板：

- `Introduction / Metrics and Benchmarks / Methods / Challenges and Future Directions`
- `Introduction / Alignment Data Collection / Alignment Training / Alignment Evaluation / Challenges and Future Directions / Conclusion`
- `INTRODUCTION / TAXONOMY OF DOMAIN SPECIALIZATION / ... / CONCLUSION`
- `QUERY REWRITER / RETRIEVER / RERANKER / READER / SEARCH AGENT / FUTURE DIRECTION`

也就是說，**human survey outline 的結構多樣性很高，沒有像 `data/paper_sets/meow_refs/` SR corpus 那樣穩定地帶 method/protocol/results 容器。**

### 2.4 `llm.jsonl`：模型 survey outline 明顯模板化

`llm.jsonl` 的特徵和 human 很不一樣：

- `n = 14`
- 平均 top-level section 數：`7.71`
- 中位數 top-level section 數：`8`
- 範圍：`5` 到 `9`
- 最大層級深度中位數：`2`

marker presence：

- 有 `Introduction`：`14/14`
- 有 `Background`：`14/14`
- 有 `Methods/Methodology`：`0/14`
- 有 `Results/Evaluation/Findings`：`1/14`
- 有 `Future`：`12/14`
- 有 `Conclusion`：`13/14`
- 有 `RQ`：`0/14`

更關鍵的是：

- `14/14` 都以 `Introduction` 開頭
- `13/14` 以 `Conclusion` 結尾
- 大多數都長成：
  - `Introduction`
  - `Background and Definitions`
  - 若干 topic blocks
  - `Challenges and Future Directions`
  - `Conclusion`

例如：

- `Introduction / Background and Definitions / NLP / Neural Network Optimization / Transformer Models / Efficiency in AI / Interdisciplinary Integration / Conclusion`
- `Introduction / Background and Definitions / Algorithmic Bias / Ethical AI / Model Interpretability / Responsible AI / Interconnections and Challenges / Future Directions / Conclusion`
- `Introduction / Background and Definitions / AI Technologies in Education / Ethical Implications of AI in Education / Educational Technology: Broader Context / Case Studies and Examples / Future Directions and Recommendations / Conclusion`

這代表什麼？

> 在 MEOW released mirror sample 裡，general survey 的 human outline 並不規整，但 model outline 反而被推向一個很穩定的 generic survey template。

### 2.5 所以，survey 是否跟 SR 一樣規整？

答案分兩半：

- **human survey**：不一樣，明顯沒有 SR 那麼規整
- **model-generated survey**：反而比 human 更規整，但這種規整是 generic survey template，不是 SR scaffold

也就是說，如果你問：

> 「survey 是否像 SR 一樣規整？」

最準確的回答是：

- 原始 human survey：**沒有**
- LLM survey output：**會被模板化成另一種規整**

這正好和你現在在 `results/` 裡看到的現象一致：

- gold（來自 SR/review paper extraction）很穩
- best（blind generation）會往 generic survey template 收斂

---

## 3. 要怎麼統計這類架構規格的相似度？

## 3.1 先說大方向：不要只用一個 metric

單一 metric 不夠，因為你要分的是兩種不同層次：

1. **hierarchy shape 是否像**
2. **section order / scaffold role 是否像**
3. **section titles / lexical cues 是否像**
4. **是否貼近 SR scaffold，而不是 generic taxonomy scaffold**

因此最合理的是用一個小型 metric suite，而不是只看 tree edit distance。

### 3.2 可直接採用的四層 metric suite

#### A. 純 hierarchy/shape metric

最直接的 baseline 就是 repo 已有的 shape-only TED：

- [scripts/compare_outlines_shape.py](/Users/xjp/Desktop/Outline_COT/scripts/compare_outlines_shape.py)
- [scripts/combine_scores.py](/Users/xjp/Desktop/Outline_COT/scripts/combine_scores.py)

現況：

- 只看 `level`
- 把所有 node label 都去掉
- 算 Zhang–Shasha tree edit distance

優點：

- 對「有沒有把一章拆成三章、深度差多少」很敏感

缺點：

- 完全不看 `title`
- 完全不知道 `Methods` 和 `Background` 的角色差異
- 分不出 `SR-like` 與 `taxonomy-like`

結論：

- 它應該保留，但只能當 baseline，不能單獨拿來回答你現在這個問題

#### B. Top-level canonical role sequence metric

把每個 top-level section title 先 canonicalize 成 role token，例如：

- `Introduction` -> `INTRO`
- `Background`, `Related Work`, `Background and Definitions` -> `BACKGROUND`
- `Method`, `Methods`, `Methodology`, `Survey Methodology`, `Review Protocol`, `Search Strategy` -> `METHOD`
- `Results`, `Findings`, `Evaluation`, `Datasets`, `Task/Application synthesis` -> `EVIDENCE`
- `Discussion`, `Challenges`, `Limitations`, `Future Directions`, `Conclusion` -> `CLOSE`

然後把每篇 outline 變成 top-level role sequence，例如：

- `INTRO -> BACKGROUND -> METHOD -> EVIDENCE -> CLOSE`
- `INTRO -> METHOD -> EVIDENCE -> CLOSE`
- `INTRO -> BACKGROUND -> TAXONOMY -> CHALLENGE -> CONCLUSION`

接著算：

- sequence edit distance
- longest common subsequence
- n-gram overlap

這層非常重要，因為它會比純 TED 更貼近「架構規格」。

#### C. Lexical/title-pattern metric

對 title 做輕量 normalization 後再算：

- top-level title Jaccard / overlap
- TF-IDF cosine on normalized section-title bag
- canonical heading token coverage

這可以抓出：

- `Methods` vs `Methodology`
- `Discussion` vs `Challenges and Future Directions`
- `Results` vs `Evaluation`

但注意：

- lexical metric 單獨用會被 synonymy 影響
- 所以最好和 role canonicalization 綁在一起

#### D. SR scaffold template matching

這是本題最需要補的新層。

先定義一組 SR-like scaffold 模板，例如：

- 強 SR 模板：`INTRO -> BACKGROUND? -> METHOD -> RESULTS/EVIDENCE -> DISCUSSION/LIMITATIONS -> CONCLUSION`
- 寬鬆 SR 模板：`INTRO -> METHOD -> EVIDENCE -> CLOSE`
- RQ-driven SR 模板：`INTRO -> METHOD -> RESULTS -> RQ* -> CLOSE`

再對每篇 outline 計算：

- template coverage
- template order consistency
- missing critical role penalty
- extra taxonomy branch penalty

最後得到一個 `SR-template score`。

這會直接回答你最在意的問題：

> 它是不是保住了 SR 的架構規格？

### 3.3 Dataset-level 統計怎麼做

#### 1. Pairwise similarity matrix

用上面 3 到 4 個 metrics 分別做 pairwise matrix：

- `shape_matrix`
- `role_sequence_matrix`
- `title_lexical_matrix`
- `sr_template_score`

然後看：

- `data/paper_sets/meow_refs/` 內部是否彼此更近
- `human survey` 內部是否更分散
- `llm survey` 是否呈現高相似模板化

#### 2. Cluster analysis

用多個 metrics 組成 feature vector 後做 clustering，例如：

- hierarchical clustering
- UMAP / PCA for visualization
- silhouette score

你會很自然看到兩到三族：

- SR-like review scaffold
- taxonomy-like survey scaffold
- 極簡/異常 compact scaffold

#### 3. Template coverage / motif frequency

這一步最直觀也最容易解釋。

統計：

- `Introduction` 出現率
- method-like section 出現率
- explicit `Results` 出現率
- `Discussion/Future/Conclusion` 出現率
- 常見 role 轉移，例如 `METHOD -> EVIDENCE`, `EVIDENCE -> CLOSE`

這能直接回答「哪一群更規整」。

#### 4. 組間 regularity 檢定

如果要正式比較：

- group A：`data/paper_sets/meow_refs/` SR/review outlines
- group B：MEOW `human` survey outlines
- group C：MEOW `llm` outlines

可比較：

- pairwise within-group distance 平均值
- top-level count variance
- role-sequence entropy
- ending-type entropy

然後做：

- permutation test
- bootstrap confidence interval
- 或簡單 Mann–Whitney U test（如果樣本數夠）

如果你只要一個非常實務的 regularity 指標，我建議直接用：

> group 內 pairwise role-sequence similarity 的平均值 + 其變異

因為這最貼近「同一個 corpus 裡是不是都長得差不多」。

---

## 4. Brainstorming 結論：實作上怎麼分梯次做

### 4.1 只做 1 個 measure

做 `canonical role sequence + SR-template score`

原因：

- 比 shape-only TED 更接近你真正想問的問題
- 實作成本低
- 解釋性強

### 4.2 做 3 個 measure

建議：

1. shape-only TED
2. canonical role-sequence edit similarity
3. SR-template score

這三個加起來已經足夠把：

- 純結構差異
- 章節次序差異
- SR 體裁差異

分開看。

### 4.3 做 5 個 measure

建議：

1. shape-only TED
2. role-sequence edit similarity
3. top-level lexical similarity
4. SR-template score
5. corpus-level entropy / motif frequency summary

這樣你可以同時做：

- pairwise comparison
- group regularity comparison
- corpus-level scaffold profiling

---

## 5. 對目前問題的最終回答

### Q1. `data/paper_sets/meow_refs/` 裡所有 paper 的 outline 是否大多都這樣？

是。
不是四篇特殊，而是 **整個 `data/paper_sets/meow_refs/*/outline.json` corpus 幾乎本來就是 systematic/review corpus**。

更精確地說：

- `12/13` title 含 `systematic`
- `13/13` 有 introduction
- `13/13` 有 method-like container
- `13/13` 有 closing container
- 約 `10/13` 可以算寬鬆 SR-like scaffold

### Q2. MEOW released survey 是否也像 SR 一樣規整？

不是一回事。

- HF dataset 本體是 [`haajimi/Meow`](https://hf.co/datasets/haajimi/Meow)
- repo 可見 sample 中，`human` survey outline **不如 SR 規整**，結構多樣
- 但 `llm` survey outline **反而更規整**，只是它規整成 generic survey template，而不是 SR scaffold

### Q3. 有沒有方法統計這類架構規格相似度？

有，而且最好不要只用一個 metric。

最推薦的組合是：

1. shape-only TED
2. canonical role-sequence similarity
3. SR-template score

如果再多做兩層，就加上：

4. lexical title similarity
5. motif frequency / entropy statistics

---

## Bottom Line

你最初的直覺是對的，但需要修正成更精確的版本：

> 這四篇 gold 很一致，確實和它們是 SR 有關；但更大的原因是 `data/paper_sets/meow_refs/` 整個 gold corpus 幾乎本來就是 systematic/review corpus。

而 MEOW released survey sample 告訴我們另一件事：

> human survey 並不天然那麼規整，真正高度規整的是 model 生成的 generic survey template。

所以後面若要評估「best 是否偏離 gold」，真正該比較的不是單純漂亮與否，而是：

- 它保住的是 `SR scaffold`
- 還是 `generic taxonomy scaffold`
