# SR Outline 結果深讀與對照導讀報告

更新日期：2026-04-16

## 摘要

本報告在前一版四篇 SR blind outline 深讀的基礎上，新增分析兩組 abstract ablation：

- `ablation_no_meta_abstract`
- `ablation_with_meta_abstract`

主問題不只是 abstract 會不會讓分數變高，而是它會不會改變 outline 對 SR 兩群 references 的處理方式：

1. `background / concept / methods / related work`
2. `evidence base / included studies`

本版正文改成逐篇雙-ablation paired reading。每篇 paper 都固定看兩張圖：

- `gold vs ablation_no_meta_abstract`
- `gold vs ablation_with_meta_abstract`

先講正式結論：

- 這次 ablation 的 contract 變動只有一個：blind generation prompt 可選擇多插入 `Target Paper Abstract`；gold 與 evaluation 本身沒有改。
- abstract 不是普遍利多。它在 `2601.19926` 明顯改善 SR 體裁感，也改寫了正式 `score-best`；但在 `2511.13936` 反而把 evidence 主體收窄，讓整體退化。
- `2409.13738` 的 `with_meta_abstract` 結構距離變好，但更接近「平均用力的規整 taxonomy」，不因此改寫正式最佳。
- 全量重算後，四篇最新 `score-best` 分別是：
  - `2307.05527`：`gpt-5.4-xhigh-3papers`
  - `2409.13738`：root blind output
  - `2511.13936`：`ablation_no_meta_abstract`
  - `2601.19926`：`ablation_with_meta_abstract`
- 全量重看後，四篇最新 `SR-aware best` 分別是：
  - `2307.05527`：`gpt-5.4-xhigh-3papers`
  - `2409.13738`：root blind output
  - `2511.13936`：`ablation_no_meta_abstract`
  - `2601.19926`：`ablation_with_meta_abstract`

---

## 1. 方法與判準

### 1.1 資料來源

- gold outline 一律讀 `data/paper_sets/meow_refs/<paper_id>/outline.json`
- generation 候選一律讀 `results/<paper_id>/**/chatgpt_meow_outline_blind.json`
- `__judge-*` 只視為同一份 outline 的重評，不當成新 generation run
- `codex_eval` 只視為 root blind output 的評分紀錄，不另外新增一份 outline 候選
- 本版 `best-by-score` 的候選池是目前 repo 內所有已有 eval 的 blind outputs，而不只看前一版報告已收錄的 run

### 1.2 這次 abstract ablation 的實際 contract

這次新增的不是新的 extraction，也不是新的 gold，而是 blind generation prompt 的單一 ablation。

code 上已確認的唯一變動在：

- [`scripts/codex_meow_outline_blind_lib.py`](../scripts/codex_meow_outline_blind_lib.py)
- [`scripts/run_codex_meow_outline_blind.sh`](../scripts/run_codex_meow_outline_blind.sh)

具體來說：

- `USER_PROMPT_TEMPLATE` 現在在 `Title:` 與 `References:` 之間，保留一個可選的 `{target_paper_abstract_block}`
- `build_prompt()` 只有在 `include_meta_abstract=True` 且 `meta.abstract` 非空時，才插入
  `Target Paper Abstract:\n...`
- runner 透過 `include_meta_abstract` 開關控制是否把 `meta.abstract` 放進最終 blind prompt

因此，這次要看的不是「模型有沒有改」，而是：

> 同一份 `title + ref_meta` 任務，在額外看到 target paper abstract 之後，outline 會不會更接近 gold 的 SR 節奏，還是更被 abstract 帶去一個更 narrative 或更 taxonomy 化的方向。

### 1.3 `best-performing` 的雙軌口徑

#### `best-by-score`

同 paper 下，以現成 eval 的六維平均分最高者為主；若平均分同分，則以較低 `structural_distance` 決勝。

#### `best-by-SR-split-awareness`

人工依 outline 細項判定下列三種 zone 是否存在：

- `background zone`：導論、背景、related work、方法、protocol、conceptual foundations
- `evidence zone`：results、RQ、task/application/evaluation synthesis、明顯在整理納入研究的主體章
- `mixing zone`：discussion、future directions、limitations，或同章同時混用概念型 refs 與 evidence refs

這個口徑不看分數高低，而看 section-level ref pattern 與章節功能是否保留 SR 的閱讀邏輯。

### 1.4 圖檔與驗證

本版主圖改成 8 張 paired PNG：

- 每篇 2 張
- 左邊固定是 gold
- 右邊分別是 `ablation_no_meta_abstract` 與 `ablation_with_meta_abstract`

驗證分三層做：

1. source 對 source：8 張 ablation tree SVG 的 `box` / `bullet` 數都和來源 outline JSON node 數完全一致
2. raster 檢查：8 張 paired PNG 全部成功輸出，尺寸非零
3. 目視檢查：逐張看 paired PNG，確認左右 panel 沒有重疊、沒有超框、沒有文字截斷

圖檔位置：

- `docs/figures/sr_outline_results_guide_2026-04-16/`

### 1.5 全量重算後的 `best-by-score`

| Paper | 最新 score-best | 平均六維分數 | Structural Distance |
| --- | --- | ---: | ---: |
| `2307.05527` | `gpt-5.4-xhigh-3papers` | `8.25` | `0.2857` |
| `2409.13738` | root blind output | `8.4167` | `0.4468` |
| `2511.13936` | `ablation_no_meta_abstract` | `8.25` | `0.4130` |
| `2601.19926` | `ablation_with_meta_abstract` | `8.6667` | `0.7647` |

### 1.6 全量重看後的 `best-by-SR-split-awareness`

| Paper | 最新 SR-aware best | 是否由 abstract ablation 改寫 | 簡述 |
| --- | --- | --- | --- |
| `2307.05527` | `gpt-5.4-xhigh-3papers` | 否 | abstract 版更顯式，但 official best 仍是舊版 blind best |
| `2409.13738` | root blind output | 否 | abstract 版更規整，但沒有超過 root 的 SR 動線 |
| `2511.13936` | `ablation_no_meta_abstract` | 是 | no-abstract 版最清楚保住方法、evidence、evaluation、challenges 的分區 |
| `2601.19926` | `ablation_with_meta_abstract` | 是 | abstract 版第一次真正把背景、方法、findings、limits、future 分開 |

---

## 2. 逐篇 abstract ablation 導讀

### 2.1 `2307.05527`

#### Gold 的 SR split 基準

這篇 gold 的 split 仍然是四篇裡最乾淨的一種：

- `background zone`：`1 Introduction`、`2 Background and Definitions`、`3 Data and Methodology`
- `evidence zone`：`4 Analysis and Results`
- `mixing zone`：`5 Discussion`

具體 ref pattern 也很清楚：

- `2 Background and Definitions` 用 `vaswani2017attention`、`imagetransformer2018`、`huang2018music`、`dhariwal2020jukebox`
- `3 Data and Methodology` 用 `moher2009preferred`、`arxiv_page`
- `4 Analysis and Results` 才切到 `kim2020glow`、`douwes2021energy`、`huang2020ai`、`Suh2021AI`

#### `gold vs ablation_no_meta_abstract`

![2307.05527 gold vs ablation no meta abstract](figures/sr_outline_results_guide_2026-04-16/2307_05527_gold_vs_ablation_no_meta_abstract_side_by_side.png)

`ablation_no_meta_abstract` 的主架構是：

- `2 Review methodology and analytical framework`
- `3 Generative audio model landscape`
- `4` 到 `8` 連續五個 harm/theme chapters
- `9 Governance, evaluation, and mitigation`
- `10 Future directions`

它有注意到 SR 的兩群 refs，但 evidence 被完全打散成多個 harm chapters：

- `2 Review methodology and analytical framework` 的確是方法區，用 `moher2009preferred`、`shelby2022sociotechnical`
- `4 Creativity, authorship, and cultural production` 用 `huang2020ai`、`frid2020music`、`Suh2021AI`
- `5 Privacy, identity, and security risks` 用 `Wang2020DeepSonar`、`Li2021Robust`
- `6 Misinformation and public trust` 用 `Mirsky2021Creation`、`meskys2020regulating`

也就是說，它保留了 methodology zone，但把 gold 的 `Analysis and Results` 徹底展成一串 topic buckets。這讓它更像 harm taxonomy，不像單一 `Results` 容器。

#### `gold vs ablation_with_meta_abstract`

![2307.05527 gold vs ablation with meta abstract](figures/sr_outline_results_guide_2026-04-16/2307_05527_gold_vs_ablation_with_meta_abstract_side_by_side.png)

加入 abstract 後，主架構明顯變了：

- `2 Background on Generative Audio Models`
- `3 Frameworks for Ethical Assessment`
- `4 Systematic Review Methodology`
- `5 How the Literature Frames Impact`
- `6 Taxonomy of Ethical Implications`
- `7 Mitigation and Governance`
- `8 Discussion and Conclusion`

這版 abstract 的作用很明確：

- 強化了 `Methods / Review Protocol`
  - `4.1 Review design and reporting standards` 用 `moher2009preferred`
  - `4.2 Search strategy, inclusion criteria, and corpus construction` 用 `arxiv_page`
- 也強化了 literature framing
  - `5 How the Literature Frames Impact`
  - `5.1 Positive applications emphasized in generative audio research`

但它也把中段 evidence 改寫成 `How the Literature Frames Impact -> Taxonomy of Ethical Implications`，而不再像 gold 那樣保留單一 `Analysis and Results` 容器。

#### 兩個 ablation 的直接比較與最新結論

這篇 abstract 的效果不是單純「變好」或「變差」，而是變得更顯式：

- `no_meta_abstract`：method 區存在，但 evidence 被打散成五個 harm chapters，偏 topic taxonomy
- `with_meta_abstract`：methodology 與 literature framing 顯著增強，整體更像知道自己在寫一篇 SR

不過，官方最佳仍然沒有被改寫：

- 最新 `score-best`：`gpt-5.4-xhigh-3papers`
- 最新 `SR-aware best`：`gpt-5.4-xhigh-3papers`

原因是舊版 blind best 已經有：

- `2 Systematic Review Design`
- `2.3 Limits of the current evidence base`
- `4.1 Data provenance, memorization, and copyright`
- `7.1 Key findings from the reviewed literature`

換句話說，`with_meta_abstract` 值得重點看，但還不足以改寫正式最佳。它更像是把 methodology 和 review stance 顯式化，而不是把 gold 的 `Results` 容器重建得更好。

### 2.2 `2409.13738`

#### Gold 的 SR split 基準

這篇 gold 的動線很完整：

- `background zone`：`1 Introduction`、`2 Related Work`、`3 Methods`
- `evidence zone`：`5 Natural Language Processing`、`6 Process Model Generation`、`7 Process Extraction Evaluation`
- `mixing zone`：`8 Discussion`

gold 的 refs 也很典型：

- `2 Related Work` 用 `bellan2020qualitative`、`maqbool2019comprehensive`、`omg_bpmn`
- `3 Methods` 用 `Page2021`、`Fereday2006`
- `5` 到 `7` 才切到 `nasiri2023automatic`、`goossens2023extracting`、`han2020bps`、`friedrich2010automated`

#### `gold vs ablation_no_meta_abstract`

![2409.13738 gold vs ablation no meta abstract](figures/sr_outline_results_guide_2026-04-16/2409_13738_gold_vs_ablation_no_meta_abstract_side_by_side.png)

`ablation_no_meta_abstract` 的主架構是：

- `2 Review Design`
- `3 Foundations of NLP4PBM`
- `4 Rule-based and Heuristic Methods`
- `5 Machine Learning and Hybrid Data-driven Approaches`
- `6 Deep Learning and Pre-trained Language Models`
- `7 Large Language Models and Prompt-based Process Extraction`
- `8 Datasets, Benchmarks, and Evaluation`
- `9 Synthesis and Future Directions`

它對 SR split 的保留其實不錯：

- `2 Review Design` 用 `kitchenham2004procedures`、`Page2021`、`Fereday2006`
- `3 Foundations of NLP4PBM` 承擔背景區
- `4` 到 `8` 是清楚的 evidence chapters
- `9 Synthesis and Future Directions` 是 mixing / future zone

這版的問題不是失去 SR 感，而是仍然比較像技術流派 taxonomy。

#### `gold vs ablation_with_meta_abstract`

![2409.13738 gold vs ablation with meta abstract](figures/sr_outline_results_guide_2026-04-16/2409_13738_gold_vs_ablation_with_meta_abstract_side_by_side.png)

加入 abstract 後，主架構變成：

- `2 Conceptual and Methodological Foundations`
- `3 Rule-based Process Extraction Methods`
- `4 Machine Learning Methods for Process Extraction`
- `5 Deep Learning Methods for Process Extraction`
- `6 Datasets, Benchmarks, and Evaluation`
- `7 Large Language Models and Emerging Directions`
- `8 Open Challenges and Future Research`

abstract 在這篇的作用不是補出更強的 methodology block，而是把結構洗得更規整：

- `2 Conceptual and Methodological Foundations` 同時吃掉背景與方法
- `3` 到 `5` 三章變成非常對齊的 method taxonomy
- `6`、`7`、`8` 再接評測、LLM、未來方向

它的 `structural_distance` 的確比 `no_meta_abstract` 更低，但 judge 也明確把它視為「平均用力」：

- `结构_详略得当 = 2.0`
- `内容_逻辑深度 = 5.0`

#### 兩個 ablation 的直接比較與最新結論

這篇是「structural distance 變好，但 SR-aware 未必更好」的典型。

- `no_meta_abstract`：有單獨的 `Review Design`，SR 體裁感更清楚
- `with_meta_abstract`：更規整、更對稱，但把 background 與 methods 合併成一章，且三個方法章太平均

因此，加入 abstract 後，outline 更像一份整齊 taxonomy，但沒有真正超過 root blind output。

最新正式結論仍然是：

- 最新 `score-best`：root blind output
- 最新 `SR-aware best`：root blind output

也就是說，這篇 abstract 主要強化的是形式規整性，不是 gold 最在意的 SR 動線。

### 2.3 `2511.13936`

#### Gold 的 SR split 基準

這篇 gold 和 `2307.05527` 一樣，是很典型的 SR 骨架：

- `background zone`：`1 Introduction`、`2 Background`、`3 Methods`
- `evidence zone`：`4 Results`
- `mixing zone`：`5 Discussion`

gold 的關鍵 ref pattern 也很乾淨：

- `2 Background` 用 `bradley1952rank`、`christiano2017deep`
- `3 Methods` 用 `page2021prisma`、`harzing2007pop`、`google_scholar_hindex`
- `4 Results` 才切到 `parthasarathy2016using`、`cao2012combining`、`liu2021reinforcement`

#### `gold vs ablation_no_meta_abstract`

![2511.13936 gold vs ablation no meta abstract](figures/sr_outline_results_guide_2026-04-16/2511_13936_gold_vs_ablation_no_meta_abstract_side_by_side.png)

`ablation_no_meta_abstract` 的主架構是：

- `2 Review Methodology`
- `3 Foundations of Preference-Based Learning`
- `4 Preference-Based Learning for Audio Understanding`
- `5 Preference-Based Learning for Audio Generation and Interaction`
- `6 Data, Labels, and Benchmarks`
- `7 Evaluation of Preference-Based Audio Systems`
- `8 Cross-Cutting Challenges`
- `9 Future Directions`

這版是這批 ablation 裡最穩的一種：

- `2 Review Methodology` 明確保留方法區
- `3 Foundations...` 是 background zone
- `4` 到 `7` 是被拆開但仍清楚的 evidence zone
- `8`、`9` 是典型 mixing / future zone

具體 ref pattern 也很好讀：

- `4 Preference-Based Learning for Audio Understanding` 用 `yang2010ranking`、`cao2015speaker`
- `5 Preference-Based Learning for Audio Generation and Interaction` 用 `cideron2024musicrl`、`zhang2024speechalign`
- `7 Evaluation...` 用 `rix2001perceptual`、`zheng2023judging`
- `8 Cross-Cutting Challenges` 用 `metallinou2013annotation`、`casper2023open`

#### `gold vs ablation_with_meta_abstract`

![2511.13936 gold vs ablation with meta abstract](figures/sr_outline_results_guide_2026-04-16/2511_13936_gold_vs_ablation_with_meta_abstract_side_by_side.png)

加入 abstract 後，主架構變成：

- `2 Review Methodology and Scope`
- `3 Foundations of Preference-Based Learning`
- `4 Preference Learning in Audio Analysis and Emotion Recognition`
- `5 Post-2021 Shift Toward Generative Audio Alignment`
- `6 Preference Signals, Data Pipelines, and Objectives`
- `7 Evaluation of Preference-Based Audio Systems`
- `8 Open Problems and Research Opportunities`

這版 abstract 的副作用很明顯：

- evidence 被重新聚焦到「post-2021 generative audio alignment」
- `4`、`5`、`6` 三章之間的邊界變模糊
- judge 也確實認為 overlap 變重：
  - `内容_章节互斥性 = 4.5`

雖然它的 `structural_distance` 比 `no_meta_abstract` 更低，但整體分數反而大幅下降：

- `no_meta_abstract`：`8.25`
- `with_meta_abstract`：`6.3333`

#### 兩個 ablation 的直接比較與最新結論

這篇是最明確的「abstract 反而帶偏」案例。

- `no_meta_abstract`：把 methods、foundations、applications、benchmarks、evaluation、challenges 都分得很清楚
- `with_meta_abstract`：abstract 把模型拉向更近期、也更敘事化的 generative alignment 故事線

換句話說，這裡的 abstract 沒有補強 `Results / Evidence synthesis`，反而收窄了 evidence coverage。

因此這篇被 abstract ablation 改寫了正式最佳，但改寫的是 `no_meta_abstract`：

- 最新 `score-best`：`ablation_no_meta_abstract`
- 最新 `SR-aware best`：`ablation_no_meta_abstract`

### 2.4 `2601.19926`

#### Gold 的 SR split 基準

這篇 gold 很短，但主軸其實非常明確：

- `background zone`：`1 Introduction`、`2 Method`
- `evidence zone`：`3 Results`
- `mixing zone`：`4 Discussion & Conclusion`

它雖然不是四篇裡 split 最硬的一篇，卻很明確保住了：

- `Method`
- `Results`
- `Discussion & Conclusion`

#### `gold vs ablation_no_meta_abstract`

![2601.19926 gold vs ablation no meta abstract](figures/sr_outline_results_guide_2026-04-16/2601_19926_gold_vs_ablation_no_meta_abstract_side_by_side.png)

`ablation_no_meta_abstract` 的主架構是：

- `2 Review Methodology and Conceptual Framework`
- `3 Behavioral Evidence of Syntactic Knowledge`
- `4 Representational Analyses of Syntax`
- `5 Mechanistic and Causal Interpretability of Syntax`
- `6 Multilingual and Cross-Lingual Syntax`
- `7 How Syntactic Knowledge Emerges`
- `8 Modeling with Explicit Syntactic Bias and Control`
- `9 Open Debates and Future Directions`

這份 outline 的問題和前一版 `gpt-5.4-mini-xhigh-4papers` 很像，甚至更強：

- evidence 被完全展平為大型 taxonomy
- `Results` 這個容器消失
- `Methodology` 與 `Conceptual Framework` 合在一起，之後一路是分門別類的主題章

它不是沒有方法區，但 evidence 與 discussion 的功能邊界被極度稀釋，所以：

- `structural_distance = 0.8431`
- `内容_章节互斥性 = 5.0`

#### `gold vs ablation_with_meta_abstract`

![2601.19926 gold vs ablation with meta abstract](figures/sr_outline_results_guide_2026-04-16/2601_19926_gold_vs_ablation_with_meta_abstract_side_by_side.png)

這篇是 abstract 最有用的一篇。加入 abstract 後，主架構變成：

- `2 Related Surveys and Conceptual Background`
- `3 Systematic Review Design`
- `4 Methods for Studying Syntax in Transformers`
- `5 Empirical Coverage of the Literature`
- `6 Synthesis of Findings on Syntactic Knowledge`
- `7 Methodological and Interpretive Limits`
- `8 Recommendations for Future Research`

這個變化是實質性的，不只是 wording 漂亮：

- `3 Systematic Review Design` 真正補出了方法區
  - `3.1 Review protocol, inclusion criteria, and reporting standards`
- `5 Empirical Coverage of the Literature` 與 `6 Synthesis of Findings...` 重新把 evidence 拉回 results-like containers
- `7 Methodological and Interpretive Limits` 明確承擔 discussion / limitation
- `8 Recommendations for Future Research` 明確承擔 future zone

也就是說，abstract 在這篇的作用，是把原本會滑向大 taxonomy 的 blind outline，重新拉回 `background -> method -> findings -> limits -> future` 的 SR 節奏。

#### 兩個 ablation 的直接比較與最新結論

這篇是本次 abstract ablation 最重要的正例。

- `no_meta_abstract`：幾乎是純 taxonomy
- `with_meta_abstract`：第一次明確重建 SR 容器

因此這篇被 abstract 真正改寫了正式最佳：

- 最新 `score-best`：`ablation_with_meta_abstract`
- 最新 `SR-aware best`：`ablation_with_meta_abstract`

這也意味著，前一版我對 `2601.19926` 的判斷要更新：現在最接近 gold 的，不再是舊版 Gemini，而是新的 `with_meta_abstract`。

---

## 3. Cross-paper Synthesis

### 3.1 abstract 不是普遍加分，而是會重寫 blind 任務的「自我定位」

從 code 看，這次 blind prompt 只多了一個 `Target Paper Abstract` block；但效果不是只多一些細節，而是會改變模型對任務的理解：

- 沒有 abstract 時，模型更依賴 `title + ref_meta` 去做 topic induction
- 有 abstract 時，模型更容易明確知道 paper 想把自己定位成什麼 type of review

所以 abstract 最常改變的，不是小標題內容，而是：

- methodology 是否被顯式成章
- evidence 是否仍然保留 `Results` / `Synthesis` 容器
- limitations / future 是否被拉回來變成獨立功能區

### 3.2 abstract 最常補強的是 `Methods / Review Protocol`

四篇裡最穩定的共通點是：加 abstract 後，methodology wording 更容易浮出來。

典型例子：

- `2307.05527`：`4 Systematic Review Methodology`
- `2601.19926`：`3 Systematic Review Design`

但這個補強不一定夠。若 abstract 同時把中段 evidence 改寫成更強的 framing / taxonomy，方法章變得更顯式，也不代表整體更接近 gold。

### 3.3 structural distance 變好，不代表 SR-aware fit 一定變好

本次最清楚的例子是 `2409.13738`：

- `ablation_with_meta_abstract` 的 `structural_distance` 比 `no_meta_abstract` 更低
- 但它把背景與方法合在一起，並且讓 3-5 章過度對齊

這種情況下，模型看起來更規整，卻不一定更像 gold 的閱讀動線。這也是為什麼這篇沒有被 abstract 改寫正式最佳。

### 3.4 abstract 對 evidence zone 的影響有兩種相反方向

#### 方向 A：把 evidence 拉回 results-like containers

代表案例：`2601.19926`

- `5 Empirical Coverage of the Literature`
- `6 Synthesis of Findings on Syntactic Knowledge`

這種變化有利於 SR-aware fit。

#### 方向 B：把 evidence 收窄成更強的 narrative focus

代表案例：`2511.13936`

- `5 Post-2021 Shift Toward Generative Audio Alignment`
- `6 Preference Signals, Data Pipelines, and Objectives`

這種變化會讓 outline 看起來更有故事線，但 evidence coverage 反而縮小，並增加章節邊界重疊。

### 3.5 本輪更新後最重要的實務結論

如果之後要把 blind outline 做得更接近這批 SR gold，重點不只是「要不要加 abstract」，而是要顯式控制以下兩件事：

1. abstract 只能補 methodology / paper stance，不能自動把中段 evidence 全部改寫成更漂亮的 taxonomy
2. 若 gold 明顯有 `Results` / `RQ` / `Included studies synthesis` 容器，prompt 或 review checklist 必須顯式要求保留這種容器，而不是只獎勵規整、對稱、描述性強的章法

---

## 4. Appendix

### 4.1 全量重算後的 `score-best` / `SR-aware best`

| Paper | 最新 score-best | 最新 SR-aware best | 是否一致 |
| --- | --- | --- | --- |
| `2307.05527` | `gpt-5.4-xhigh-3papers` | `gpt-5.4-xhigh-3papers` | 一致 |
| `2409.13738` | root blind output | root blind output | 一致 |
| `2511.13936` | `ablation_no_meta_abstract` | `ablation_no_meta_abstract` | 一致 |
| `2601.19926` | `ablation_with_meta_abstract` | `ablation_with_meta_abstract` | 一致 |

### 4.2 `no_meta_abstract` vs `with_meta_abstract` 分數與判讀

| Paper | `no_meta_abstract` Avg / SD | `with_meta_abstract` Avg / SD | 判讀 |
| --- | --- | --- | --- |
| `2307.05527` | `7.3333 / 0.4000` | `8.0000 / 0.3784` | abstract 強化 methodology 與 literature framing，但仍未改寫全局最佳 |
| `2409.13738` | `7.7500 / 0.4286` | `7.2500 / 0.2903` | abstract 降低 structural distance，但更像平均用力的規整 taxonomy |
| `2511.13936` | `8.2500 / 0.4130` | `6.3333 / 0.3250` | abstract 將 evidence 收窄到 generative alignment 故事線，反而退化 |
| `2601.19926` | `6.2500 / 0.8431` | `8.6667 / 0.7647` | abstract 明顯重建 background / method / findings / limits / future |

### 4.3 abstract 是否改變 `background / evidence / mixing` 分區

| Paper | `no_meta_abstract` | `with_meta_abstract` |
| --- | --- | --- |
| `2307.05527` | background 與 method 還在，但 evidence 被打散成 harm taxonomy | method zone 更清楚，evidence 改成 `literature framing + taxonomy`，更顯式但不更像 gold |
| `2409.13738` | `Review Design + Foundations + evidence chapters + future` | background 與 methods 合併，方法流派章更對稱，SR-aware 未提升 |
| `2511.13936` | method、foundations、applications、benchmarks、evaluation、challenges 分得清楚 | evidence 收窄到 post-2021 generative alignment，章節邊界變模糊 |
| `2601.19926` | 大 taxonomy，`Results` 容器消失 | 補出 `Systematic Review Design`、`Empirical Coverage`、`Synthesis`、`Limits` |

### 4.4 Gold outline 的固定基準

| Paper | Gold background zone | Gold evidence zone | Gold mixing zone |
| --- | --- | --- | --- |
| `2307.05527` | `1`, `2`, `3` | `4` | `5` |
| `2409.13738` | `1`, `2`, `3` | `5`, `6`, `7` | `8` |
| `2511.13936` | `1`, `2`, `3` | `4` | `5` |
| `2601.19926` | `1`, `2` | `3` | `4` |

---

## 結語

這次 abstract ablation 最值得記住的一句話是：

> abstract 最常做的不是「補一些內容」，而是改變 blind outline 對自己正在寫哪一種 review 的判斷。

因此，abstract 只有在一種情況下特別有用：

- 它能把 outline 從大而全 taxonomy，拉回 `background -> method -> findings -> limits -> future` 的 SR 節奏

`2601.19926` 就是正例；`2511.13936` 則是反例。
這也進一步證明，若後續真的要讓 blind generation 更貼近 SR gold，不能只問「要不要加 abstract」，而要明確規定：

- 哪裡必須保留 methodology
- 哪裡必須保留 evidence synthesis 容器
- 哪裡可以做 discussion / limitations / future 的混用
