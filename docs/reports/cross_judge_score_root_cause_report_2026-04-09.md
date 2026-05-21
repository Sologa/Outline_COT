# Cross-Judge 低分根因研究報告

日期：2026-04-09
研究對象：`2307.05527`、`2409.13738`、`2511.13936`、`2601.19926`
對應結果摘要：[`docs/cross_judge_cli_results_2026-04-09.md`](./cross_judge_cli_results_2026-04-09.md)

## Executive Summary

這批 cross-judge 結果的核心問題，不是「模型大綱普遍很差」，而是「生成任務、gold 標準、judge rubric、local 實作細節」四件事同時沒有完全對齊。

先說結論：

1. **不是四篇都差。**
   - `2307.05527` 的 `gpt-5.4 xhigh -> gemini judge` 之 `6D Judge Avg` 是 `8.7500`。
   - `2511.13936` 的同一路徑是 `8.3333`。
   - 真正明顯拖低整體印象的是 `2409.13738` 和 `2601.19926`，而且失分集中在少數 rubric，不是六維全面崩掉。

2. **最大的 confirmed cause 是 task / evaluation contract mismatch。**
   - blind generation 的 prompt 明確要求模型「根據 `title + ref_meta` 寫一份 literature review outline」。
   - evaluation 的 structural gold 卻默認用 `data/paper_sets/meow_refs/<paper_id>/outline.json`，也就是從 paper / TeX 抽出的**實際論文章節骨架**。
   - 這兩個任務不是同一件事。前者偏「合理綜述寫作」，後者偏「忠實重建 paper 現成結構」。

3. **`2601.19926` 是最強的反例，也是最強的證據。**
   - gold outline 只有 `7` 個節點、`4` 個一級章節。
   - 但 blind generation 產生的是 `25` 到 `40` 個節點、`9` 到 `10` 個一級章節的完整 taxonomy 式綜述。
   - `Structural Distance` 因此直接飆到 `0.692308` 和 `0.804878`。
   - 可是兩個 judge 同時都承認這些大綱在「資訊快速定位」上其實不差，表示**這不是單純內容品質低，而是評分標準和生成目標錯位**。

4. **judge rubric 對「平均用力」「沒有三級標題」「標題過長」非常敏感。**
   - `2409.13738` 和 `2601.19926` 的 `gpt` 版本都被 Gemini judge 在 `结构_详略得当` 打到 `2.5`。
   - judge 理由很一致：主章節之間子節數量太平均、層級深度一致、沒有三級標題、像 taxonomy 羅列。
   - 也就是說，模型不是完全沒結構，而是**用了 judge 不喜歡的結構風格**。

5. **還有幾個 secondary fidelity issues，會讓分數更不乾淨，但不足以單獨解釋低分。**
   - local judge 目前把 `{topic}` 填成 `paper_id`，不是 paper title。
   - blind runner 目前把 `ref_meta` 以 strict JSON 餵給模型；upstream released formatter 用的是 Python repr-style object。
   - local workflow 報的是 upstream repo-defined **6D judge**，不是 paper wording 中更常被理解成的 5D judge。

一句話版本：

> 這批低分主要不是因為模型不會寫大綱，而是因為現在拿「blind synthesis 出來的合理綜述大綱」去跟「paper 的真實章節骨架」比，然後再用一個特別討厭平均展開與長標題的 6D judge 去打分，所以分數被系統性壓低，尤其在 `2409.13738` 和 `2601.19926` 特別明顯。

---

## What Is Actually “Bad” and What Is Not

### 1. 真正差的是哪裡

從 [`docs/cross_judge_cli_results_2026-04-09.md`](./cross_judge_cli_results_2026-04-09.md) 看，整體分數不是全面低迷，而是呈現兩極化：

| Paper | Generated Outline | Structural Distance ↓ | 6D Judge Avg ↑ |
|---|---|---:|---:|
| `2307.05527` | `gpt-5.4 xhigh` | `0.285714` | `8.7500` |
| `2307.05527` | `gemini-3.1-pro-preview` | `0.387097` | `6.6667` |
| `2409.13738` | `gpt-5.4 xhigh` | `0.277778` | `6.5833` |
| `2409.13738` | `gemini-3.1-pro-preview` | `0.333333` | `7.0000` |
| `2511.13936` | `gpt-5.4 xhigh` | `0.297297` | `8.3333` |
| `2511.13936` | `gemini-3.1-pro-preview` | `0.459459` | `6.0000` |
| `2601.19926` | `gpt-5.4 xhigh` | `0.804878` | `6.6667` |
| `2601.19926` | `gemini-3.1-pro-preview` | `0.692308` | `7.3333` |

可以看到：

- `2307.05527` 和 `2511.13936` 至少有一條生成路徑拿到很高的 judge 分。
- `2601.19926` 真正嚴重的是 structural score，不是 judge 全面否定。
- `2409.13738` 的 structural 其實不算特別糟，但被 judge 的 `详略得当 / 逻辑深度 / 简洁性` 明顯扣分。

### 2. 哪些不是問題

以下說法都**不準確**：

- 「所有 paper 都生成失敗了」
- 「judge 認為這些大綱完全不能看」
- 「只要換一個模型就會好」
- 「問題只在 Structural Distance」

對照組 `2307.05527` 與 `2511.13936` 的存在，證明 benchmark 沒有完全壞掉，也證明模型不是完全不會生成有效 outline。真正的問題是：**某些 paper 的 gold 形狀和 blind synthesis 的自然輸出分佈衝突得非常厲害。**

---

## End-to-End Pipeline Reconstruction

這一節只整理 **confirmed** 的 pipeline 事實，不做推論。

### 1. Blind generation 在做什麼

local blind runner 是 [`scripts/run_codex_meow_outline_blind.sh`](../scripts/run_codex_meow_outline_blind.sh)。

它會讀：

- `data/paper_sets/meow_refs/<paper_id>/meow_reconstructed_blind.json`

然後用 [`scripts/codex_meow_outline_blind_lib.py`](../scripts/codex_meow_outline_blind_lib.py) 組 prompt。

blind generation 的 faithful prompt 核心長這樣：

- system prompt：
  - `You are a scientific writing assistant. Produce a structured outline based on the article metadata and references provided.`
- user prompt：
  - `Write an outline for a literature review based on the given title and references.`
  - 輸入只有 `Title` 與 `References`

對應 local code：

- [`scripts/codex_meow_outline_blind_lib.py`](../scripts/codex_meow_outline_blind_lib.py)
- upstream formatter：
  [`third_party/repos/Meow-Data-curation/utils/data_to_trainformat/formet_to_train_data.py`](../../third_party/repos/Meow-Data-curation/utils/data_to_trainformat/formet_to_train_data.py)

這表示 blind generation 的任務本質是：

> 給你一篇 review 的 title 與 references metadata，請你寫出一份合理的 literature review outline。

它**不是**：

- 重建這篇 paper 的真實 outline
- 從 paper 內容做 faithful outline extraction
- 根據 target outline 做對齊生成

### 2. Gold outline 在哪裡來

repo guide 和 [`docs/guides/meow_evaluation_assets.md`](../guides/meow_evaluation_assets.md) 都寫得很清楚：

- blind evaluation 預設 gold path 是 `data/paper_sets/meow_refs/<paper_id>/outline.json`
- `outline.json` 是 reference-side artifact
- source 來源是 paper / TeX 抽出的實際章節骨架，不是 blind prompt 的 target

相關來源：

- [`docs/guides/meow_evaluation_assets.md`](../guides/meow_evaluation_assets.md)
- [`third_party/repos/Meow-Data-curation/utils/data_exact/exact.py`](../../third_party/repos/Meow-Data-curation/utils/data_exact/exact.py)

也就是說，evaluation 默認拿來比的是：

> 這篇 paper 最後實際採用的章節結構

### 3. Structural Distance 實際在比什麼

Structural Distance 的 local path 是：

- [`scripts/combine_scores.py`](../scripts/combine_scores.py)
- [`scripts/evaluate_chatgpt_meow_blind_batch.py`](../scripts/evaluate_chatgpt_meow_blind_batch.py)

關鍵事實：

- `_build_shape_tree_from_sections()` 只看 `level`
- 每個節點都被寫成 `Node("n")`
- 不看 `title`
- 不看 `numbering`
- 不看 `ref`

所以它比的是**純 shape-only tree edit distance**，不是語義相似度。

這件事很重要，因為它意味著：

- 就算生成大綱語義上非常合理
- 只要節點數、層級深度、章節展開方式和 gold 不同
- structural score 還是會很差

### 4. Judge 在看什麼

local judge 用的是 upstream repo-defined **6D judge**：

- local prompt captures：
  - [`prompts/meow_llm_judge_6d_source_system.txt`](../prompts/meow_llm_judge_6d_source_system.txt)
  - [`prompts/meow_llm_judge_6d_source_user.txt`](../prompts/meow_llm_judge_6d_source_user.txt)
- local runner：
  - [`scripts/evaluate_chatgpt_meow_blind_batch.py`](../scripts/evaluate_chatgpt_meow_blind_batch.py)
- upstream mirror：
  - [`third_party/repos/Survey-Outline-Evaluation-Benckmark/scripts/evaluate_llm.py`](../../third_party/repos/Survey-Outline-Evaluation-Benckmark/scripts/evaluate_llm.py)

這個 judge 的 6 維是：

1. `结构_信息快速定位`
2. `结构_详略得当`
3. `内容_章节互斥性`
4. `内容_逻辑深度`
5. `内容_学术价值`
6. `语用_描述性与简洁性`

其中幾條規則對這次分析特別關鍵：

- **詳略得當**
  - 如果各主章節的子標題數量、層級深度高度趨同，低於 3 分是合理結果。
- **邏輯深度**
  - 沒有三級標題，且內部只是並列列舉，通常只會落在 3-6 分。
- **描述性與簡潔性**
  - 標題超過 8 個詞，會被明確扣分。

這些規則和「寫出一份學術上漂亮的 taxonomy」其實不是完全同一組偏好。

### 5. Local fidelity differences

以下是 local workflow 與 upstream faithful reproduction 的已確認差異：

1. **judge topic 現在傳的是 `paper_id`，不是 title。**
   - local code：
     [`scripts/evaluate_chatgpt_meow_blind_batch.py`](../scripts/evaluate_chatgpt_meow_blind_batch.py)
   - 具體是：
     `messages = build_judge_messages(repo_root=repo_root, topic=paper_id, outline_text=outline_text)`

2. **blind runner 把 `ref_meta` 轉成 strict JSON。**
   - local code：
     [`scripts/codex_meow_outline_blind_lib.py`](../scripts/codex_meow_outline_blind_lib.py)
   - upstream released formatter：
     [`third_party/repos/Meow-Data-curation/utils/data_to_trainformat/formet_to_train_data.py`](../../third_party/repos/Meow-Data-curation/utils/data_to_trainformat/formet_to_train_data.py)
   - upstream formatter實際是把 `item['ref_meta']` 直接插進 template，屬於 Python repr-style payload。

3. **local workflow 用的是 6D judge，不是 paper 常被口語理解的 5D judge。**
   - 這點在 [`docs/guides/meow_evaluation_assets.md`](../guides/meow_evaluation_assets.md) 已經明確標記。

這三件事都是真的，但要分清楚：

- 第 1、2 點是 **secondary fidelity issues**
- 第 3 點主要是 **reporting / interpretation issue**
- 它們都不是這批低分的單一主因

---

## Per-Paper Root Cause Analysis

### `2307.05527`

#### 1. 結果概況

- gold outline：`30` nodes，levels = `{1: 6, 2: 10, 3: 14}`
- `gpt-5.4 xhigh` 生成：`34` nodes，levels = `{1: 7, 2: 27}`
- `gemini-3.1-pro-preview` 生成：`18` nodes，levels = `{1: 7, 2: 11}`

對應分數：

- `gpt -> gemini judge`
  - Structural Distance = `0.285714`
  - 6D Judge Avg = `8.7500`
- `gemini -> gpt judge`
  - Structural Distance = `0.387097`
  - 6D Judge Avg = `6.6667`

#### 2. gold skeleton vs generated skeleton

gold 的一級骨架：

- `Introduction`
- `Background and Definitions`
- `Data and Methodology`
- `Analysis and Results`
- `Discussion`
- `Conclusion`

`gpt` 版本的一級骨架：

- `Introduction`
- `Systematic Review Design`
- `Technical Landscape of Generative Audio`
- `Major Ethical Implications of Generative Audio Models`
- `Mitigation Strategies and Governance Mechanisms`
- `Open Challenges and Future Research Directions`
- `Conclusion`

白話講，這一篇的 gold 本身就已經是比較像綜述型、topic-organized 的 structure，所以 blind generation 雖然沒有忠實照抄章名，**但語義骨架沒有嚴重跑掉**。

#### 3. judge 為什麼沒有把它打很低

Gemini judge 對 `gpt` 版本的判語很直接：

- 認為它採用清晰的主題分類系統綜述結構
- 認為第 4 章有 `7` 個二級標題，主次很鮮明
- 認為第 5、6 章提供治理與未來方向，因此有學術與實務價值

這說明這個 case 裡：

- blind generation 產出的 natural style
- gold 的論文側結構
- judge rubric 的偏好

三者剛好沒有互相嚴重衝突。

#### 4. 這篇的 root cause 結論

- **confirmed cause**
  - 沒有看到明顯的 contract 爆炸；這篇是對照組，證明 benchmark 不是全面失效。
- **strong contributing factor**
  - `gemini` 生成版本比較壓縮，Methodology 沒展開，Future Directions 也不夠細，所以 academic value 被 Codex judge 壓到 `5.5`。
- **白話結論**
  - 這篇不是「系統有問題才剛好過關」，而是它剛好屬於 blind generation 與 gold 結構自然相容的 paper。

---

### `2409.13738`

#### 1. 結果概況

- gold outline：`27` nodes，levels = `{1: 10, 2: 15, 3: 2}`
- `gpt-5.4 xhigh` 生成：`35` nodes，levels = `{1: 10, 2: 25}`
- `gemini-3.1-pro-preview` 生成：`29` nodes，levels = `{1: 8, 2: 21}`

對應分數：

- `gpt -> gemini judge`
  - Structural Distance = `0.277778`
  - 6D Judge Avg = `6.5833`
  - 最低三維：`结构_详略得当 = 2.5`、`内容_逻辑深度 = 5.0`、`语用_描述性与简洁性 = 5.5`
- `gemini -> gpt judge`
  - Structural Distance = `0.333333`
  - 6D Judge Avg = `7.0000`
  - 最低三維：`结构_详略得当 = 5.5`、`内容_逻辑深度 = 6.5`、`内容_学术价值 = 6.5`

#### 2. gold skeleton vs generated skeleton

gold 的一級骨架偏功能章：

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

`gpt` 版本轉成方法演進型骨架：

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

這個轉換本身未必「錯」，但它已經不是 paper 的實際寫法，而是把 paper 重寫成一篇更典型的 computer-science taxonomy review。

#### 3. judge 為什麼扣這麼多

Gemini judge 對 `gpt` 版的低分理由非常規律：

- 認為第 `4` 到第 `9` 章幾乎都剛好 `3` 個二級標題
- 認為這是「典型平均用力」
- 認為沒有三級標題，內部層次扁平
- 認為部分標題超過 8 詞，不夠簡潔

repo 內部量化結果也支持這點：

- `gpt-2409` 的 top-level child counts 是 `[2, 3, 2, 3, 3, 3, 3, 3, 3, 0]`
- `gemini-2409` 的 top-level child counts 是 `[3, 3, 3, 3, 4, 2, 3, 0]`

白話講就是：

> 模型很愛把每個主章節都展成差不多 2-4 個子節。這對人類看起來可能算整齊，但這個 judge 會把它解讀成「沒有主次、平均出力、缺少層次設計」。

#### 4. 這篇的 root cause 結論

- **confirmed cause**
  - judge rubric 對「平均展開 + 沒有三級標題」有直接懲罰，這在 prompt 與 judge rationale 中都被直接證實。
- **strong contributing factor**
  - blind generation 把 gold 的功能型章節骨架重寫成方法演進 / taxonomy 骨架，所以雖然 structural 沒有像 `2601` 那麼爆，但已經開始錯位。
- **白話結論**
  - 這篇不是內容太差，而是「寫成了另一種學術上合理、但 judge 覺得太平均的綜述樣子」。

---

### `2511.13936`

#### 1. 結果概況

- gold outline：`36` nodes，levels = `{1: 7, 2: 15, 3: 14}`
- `gpt-5.4 xhigh` 生成：`35` nodes，levels = `{1: 8, 2: 27}`
- `gemini-3.1-pro-preview` 生成：`19` nodes，levels = `{1: 8, 2: 11}`

對應分數：

- `gpt -> gemini judge`
  - Structural Distance = `0.297297`
  - 6D Judge Avg = `8.3333`
  - 最低維度是 `语用_描述性与简洁性 = 5.5`
- `gemini -> gpt judge`
  - Structural Distance = `0.459459`
  - 6D Judge Avg = `6.0000`
  - 最低三維：`内容_学术价值 = 4.5`、`内容_章节互斥性 = 5.5`、`内容_逻辑深度 = 5.5`

#### 2. 這篇為什麼能當控制組

gold 本身就比較深，也比較接近 blind generation 會自然產出的學術綜述風格：

- 有 `Background`
- 有 `Methods`
- 有 `Results`
- 有 `Discussion`
- 有 `Limitations`
- 有 `Conclusion`

`gpt` 版本雖然也重寫成更 synthesize 的骨架，但整體節點數和 gold 很接近，judge 也認可它有清楚的：

- foundations
- applications
- evaluation
- open challenges / future directions

#### 3. 真正被扣的點

`gpt` 版本的弱點不是結構，而是標題太長。repo 內部重算可以直接列出一串超過 8 詞的標題，例如：

- `Human-preference alignment for text-to-audio and music generation`
- `Corpora and benchmarks for emotion, speech, music, and omni-audio tasks`
- `LLM-based judges and holistic evaluation for multimodal preference alignment`

Gemini judge 也正是因為這個理由，把 `语用_描述性与简洁性` 打成 `5.5`。

相反地，`gemini` 生成版本的問題是：

- 沒有把 `Future Directions / Open Challenges` 展得夠完整
- 第 6 章 `Large Audio-Language and Omnimodal Models` 沒有二級展開
- 讓 Codex judge 覺得 academic value 太弱

#### 4. 這篇的 root cause 結論

- **confirmed cause**
  - judge 對標題長度與 academic value 顯式有規則，這篇正好驗證了它真的在執行那些規則。
- **strong contributing factor**
  - 生成版本如果太壓縮，會被 judge 認為沒有研究議程；如果太展開、標題太長，又會被 judge 認為不夠簡潔。
- **白話結論**
  - 這篇證明系統不是完全失靈，而是有一個很明確的 sweet spot：結構要完整，但不能平均展太開；標題要具體，但不能太長。

---

### `2601.19926`

#### 1. 結果概況

- gold outline：`7` nodes，levels = `{1: 4, 2: 3}`
- `gpt-5.4 xhigh` 生成：`40` nodes，levels = `{1: 9, 2: 31}`
- `gemini-3.1-pro-preview` 生成：`25` nodes，levels = `{1: 10, 2: 15}`

對應分數：

- `gpt -> gemini judge`
  - Structural Distance = `0.804878`
  - raw edit operations = `33`
  - reference node count = `8`
  - source node count = `41`
  - 6D Judge Avg = `6.6667`
  - 最低三維：`结构_详略得当 = 2.5`、`内容_逻辑深度 = 5.0`、`语用_描述性与简洁性 = 5.5`
- `gemini -> gpt judge`
  - Structural Distance = `0.692308`
  - raw edit operations = `18`
  - reference node count = `8`
  - source node count = `26`
  - 6D Judge Avg = `7.3333`
  - 最低三維：`内容_章节互斥性 = 6.5`、`内容_学术价值 = 6.5`、`结构_详略得当 = 7.0`

#### 2. 這篇是整份研究裡最關鍵的證據

gold 的一級骨架只有：

- `Introduction`
- `Method`
- `Results`
- `Discussion \& Conclusion`

但 blind generation 自然產生的是完整 synthesize/taxonomy 骨架：

`gpt` 版本：

- `Introduction`
- `Review Design and Conceptual Framework`
- `Main Interpretability Paradigms`
- `What Syntax Do Language Models Encode?`
- `What Shapes Syntactic Knowledge?`
- `Multilingual and Cross-Lingual Syntax`
- `Methodological Tensions and Evaluation Pitfalls`
- `Synthesis and Future Directions`
- `Conclusion`

`gemini` 版本：

- `Introduction`
- `Methodology of the Systematic Review`
- `Theoretical Foundations: Syntax and Neural Language Models`
- `Methodologies for Probing Syntactic Knowledge`
- `Localization and Mechanisms of Syntax in Transformers`
- `Evaluation of Specific Syntactic Phenomena`
- `Cross-Lingual and Multilingual Syntactic Transfer`
- `Limitations, Heuristics, and Fragility of Neural Syntax`
- `Integrating Explicit Syntax into Language Models`
- `Conclusion and Future Directions`

這裡最重要的觀察是：

> 這兩份 blind outline 看起來都像「人類會寫的、有組織的現代 NLP survey」。
> 但 gold `outline.json` 看起來更像 paper 最後實際發表時採用的扁平章節骨架。
> 這兩者不是同一個輸出分佈。

#### 3. 為什麼 Structural Distance 爆掉

Structural Distance 在這篇爆掉，不是因為 semantic nonsense，而是因為：

- gold 太扁平
- generated 太展開
- metric 只看 shape，不看 title / semantic content

這個 case 的 structural debug 幾乎已經把原因寫在臉上：

- gold node count = `8`
- source node count = `41`
- raw edit operations = `33`
- denominator = `41`
- final shape distance = `0.804878`

換句話說，只要生成稿不是故意模仿那種「四大章 + 三個 Results 子題」的扁平 paper skeleton，它就很難不被打爆。

#### 4. 為什麼 judge 又沒有把它全盤否定

Gemini judge 對 `gpt` 版本給了：

- `结构_信息快速定位 = 9.0`
- `内容_章节互斥性 = 8.5`
- `内容_学术价值 = 9.5`

它真正扣的是：

- 主章節之間子節數過於平均
- 沒有三級標題
- 有多個長標題

這說明：

- judge 認為這是一份**可讀的、功能清楚的、甚至有學術價值**的 outline
- structural metric 卻認為它和 gold 差非常遠

這正是本次研究最核心的證據：

> 同一份生成稿，同時被 judge 認為「不差」，卻被 structural metric 認為「很遠」，說明問題不是單純品質差，而是任務定義與 gold 定義不一致。

#### 5. 這篇的 root cause 結論

- **confirmed cause**
  - blind generation 任務與 gold evaluation 任務嚴重錯位。
  - structural metric 只看 shape，不看 semantic content。
- **strong contributing factor**
  - Gemini judge 額外不喜歡均勻展開與長標題，讓 `gpt` 版本的 6D 平均也被壓低。
- **secondary fidelity issue**
  - local judge 把 topic 傳成 `2601.19926` 而不是真實 title，這會讓 judge 少一層主題語境，但不足以單獨造成 `0.804878` 的 structural 爆炸。
- **白話結論**
  - 這篇分數差，最主要不是模型亂寫，而是你要它「盲寫一篇合理 survey 大綱」，卻拿「作者最後實際採用的扁平 paper 骨架」當答案。

---

## Cross-Paper Patterns

### Pattern 1: 任務越像「blind synthesis」，gold 越像「paper skeleton」，Structural Distance 就越容易失真

最典型的是 `2601.19926`。

但 `2409.13738` 也有類似傾向：gold 有很多功能章節，如 `Related Work`、`Threats to Validity and Limitations`，而 blind generation 更傾向把內容重寫成方法演進與 taxonomy。

### Pattern 2: judge 很喜歡「有研究議程感」的大綱，但很討厭「平均展開」的大綱

這導致一個矛盾：

- 如果你把挑戰、限制、未來方向寫清楚，academic value 會變高。
- 但如果你每章都平均拆成 3 個子節，`详略得当` 又會被打低。

所以模型要同時過關，必須做到：

- 不是每章都平均拆
- framing 章要短
- 核心章要深
- 最好某些核心章有三級標題

### Pattern 3: cross-judge 不是純 judge A/B，因為同時換了 generator

這一點要很小心，不能過度解讀。

這次 cross-judge 的 setup 是：

- `gpt` 生成稿交給 Gemini judge
- `gemini` 生成稿交給 Codex judge

所以：

- 看見平均分差異，不能直接等同於「judge backend 偏好差異」
- 因為 generator 和 judge 同時變了

但我們仍然可以保守地說：

- **inference**
  - 兩種 judge 的文字偏好確實不完全一樣。
  - Gemini judge 對 `gpt` 生成稿平均給出更高的 `信息快速定位` 與 `学术价值`。
  - Codex judge 對 `gemini` 生成稿平均給出更高的 `描述性与简洁性`。

四篇平均值如下：

| 維度 | `gpt 生成 -> gemini judge` | `gemini 生成 -> codex judge` |
|---|---:|---:|
| `结构_信息快速定位` | `9.000` | `7.250` |
| `结构_详略得当` | `5.375` | `6.250` |
| `内容_章节互斥性` | `8.875` | `6.375` |
| `内容_逻辑深度` | `6.500` | `6.500` |
| `内容_学术价值` | `9.250` | `5.750` |
| `语用_描述性与简洁性` | `6.500` | `8.375` |

這個表只能支持：

- **judge taste + generator style 的組合效應明顯存在**

不能支持：

- 「單純是 Gemini judge 比較寬鬆」
- 或「單純是 Codex judge 比較嚴格」

### Pattern 4: 對照組很重要

`2307.05527` 與 `2511.13936` 的存在很關鍵，因為它們證明：

- 這不是一個「所有 blind generation 都會被 structural 與 judge 一起打爛」的 benchmark
- 而是「某些 paper 的 gold 結構剛好和 blind synthesis 風格對不上」

這也是為什麼不能把問題簡化成「模型生成太差」。

---

## Confirmed Causes vs Contributing Factors

### Confirmed Causes

1. **blind generation 與 evaluation gold 的任務定義不一致。**
   - blind generation 只吃 `title + ref_meta`
   - evaluation 預設 gold 用 `data/paper_sets/meow_refs/<paper_id>/outline.json`
   - 前者是 synthesis，後者是 extraction / paper-structure reference

2. **Structural Distance 是 shape-only metric。**
   - 只看 `level`
   - 不看標題與語義

3. **6D judge 對平均展開、無三級標題、長標題有顯式懲罰。**
   - 這在 prompt 與 judge rationale 中都有直接證據

4. **本地 workflow 用的是 upstream repo-defined 6D judge，不是 paper 常被口語理解的 5D judge。**
   - 這會影響結果的解讀與對外描述

### Strong Contributing Factors

1. **某些 paper 的 gold outline 天生對 blind synthesis 不友善。**
   - `2601.19926` 是最明顯案例

2. **blind generation 自然偏向寫成現代 CS/NLP 綜述的 taxonomy。**
   - 尤其容易加入：
     - background / theoretical foundations
     - methods / paradigms
     - evaluation
     - challenges / future directions

3. **不同 generator + judge 的組合會放大某些風格偏好。**
   - 這點有數據支持，但目前不是 isolated A/B，必須保守描述

### Secondary Fidelity Issues

1. **judge 的 `{topic}` 目前是 `paper_id`，不是 title。**
2. **blind prompt 的 `ref_meta` 序列化方式和 upstream released formatter 不完全一致。**
3. **cross-judge 報表沒有把「這是 6D judge，不是 paper 5D judge」放在最顯眼的位置。**

這些都值得修，但不能把它們當成這批低分的唯一解釋。

---

## Recommended Fixes and Validation Experiments

以下 fix 依優先順序排列。

### Fix 1: 先把 evaluation contract 對齊

#### 建議

把現在的任務拆成兩條，不要再混成一條：

1. **Paper-faithful reconstruction track**
   - 任務：盡量重建 paper 的真實 outline
   - gold：`data/paper_sets/meow_refs/<paper_id>/outline.json`

2. **Blind survey synthesis track**
   - 任務：根據 `title + ref_meta` 生成一份合理的 survey outline
   - gold：不要直接用論文側的 `outline.json` 當唯一答案
   - 改用：
     - 人工評審
     - 多 judge 比較
     - 或一份專門為 blind synthesis 建的 normalized reference skeleton

#### 為什麼排第一

因為只要 contract 不修，`2601.19926` 這種 case 會持續被 structural metric 系統性誤傷。

#### 最小驗證實驗

1. 先挑 `2601.19926`
2. 準備一份「盲寫合理綜述」導向的 normalized reference skeleton
3. 用現有兩份 blind outputs 重新算 structural distance
4. 預期：
   - structural distance 會顯著低於目前的 `0.692308 / 0.804878`
   - judge 結論與 structural 結論之間的衝突會明顯縮小

### Fix 2: 再修 generation prompt 與 output shape 控制

#### 建議

如果目標仍是把 6D judge 分數拉高，生成端至少要新增三種控制：

1. **避免平均展開**
   - framing 章節不要都拆成 3 個子節
   - 核心章節才深拆

2. **必要時引入三級標題**
   - 尤其是 judge 明顯認為應該更深拆的核心章

3. **限制標題長度**
   - 明確要求除必要術語外，標題盡量控制在 8 詞內

#### 為什麼排第二

因為這是直接對 `2409.13738` 與 `2601.19926` 的 judge 低分點下手。

#### 最小驗證實驗

1. 針對 `2409.13738` 與 `2601.19926`
2. 新增一個 prompt variant，要求：
   - non-uniform section expansion
   - at least one deeply expanded core chapter
   - concise titles
3. 同一模型重跑 blind generation
4. 用同一 judge 重新評
5. 預期：
   - `结构_详略得当` 明顯高於目前的 `2.5 / 5.5 / 7.0`
   - `语用_描述性与简洁性` 也應提高

### Fix 3: 最後修 judge hygiene 與 faithful reproduction 細節

#### 建議

1. judge 改傳真實 title，不要傳 `paper_id`
2. blind runner 另開一個 faithful variant，使用 upstream repr-style `ref_meta`
3. 報表與文件中更明確標註「這是 upstream 6D judge」

#### 為什麼排第三

因為這些問題是真的，但不像 contract mismatch 那麼致命，也不像 generation shape 那麼直接影響主分數。

#### 最小驗證實驗

1. 固定同一份 outline
2. judge A/B 比較：
   - `topic = paper_id`
   - `topic = title`
3. blind runner A/B 比較：
   - `ref_meta` as JSON
   - `ref_meta` as repr-style object
4. 預期：
   - judge 分數可能有小幅漂移
   - generation wording / section naming 可能有局部變化
   - 但不應該再被誤認為主因

### Fix 4: 分開報告 5D 與 6D，避免 interpretation drift

#### 建議

在所有 cross-judge 報表中，把這件事放到摘要第一屏：

- paper wording 常被理解成 5D judge
- local workflow 用的是 upstream repo-defined 6D judge
- 多出來的維度是 `内容_学术价值`

#### 最小驗證實驗

1. 修改 summary docs 標示方式
2. 讓不參與本 repo 的讀者閱讀一次
3. 確認不再出現「為什麼 paper 是 5 個標準，你這裡是 6 維」的混淆

---

## Appendix: Key Evidence

### A. `2601.19926` structural 爆炸的直接證據

來源：

- [`results/2601.19926/gpt-5.4-xhigh__judge-gemini-3.1-pro-preview/chatgpt_meow_outline_blind.eval.debug.json`](../results/2601.19926/gpt-5.4-xhigh__judge-gemini-3.1-pro-preview/chatgpt_meow_outline_blind.eval.debug.json)
- [`results/2601.19926/gemini-3.1-pro-preview__judge-gpt-5.4-xhigh/chatgpt_meow_outline_blind.eval.debug.json`](../results/2601.19926/gemini-3.1-pro-preview__judge-gpt-5.4-xhigh/chatgpt_meow_outline_blind.eval.debug.json)

關鍵數字：

| Run | raw edit ops | ref nodes | source nodes | distance |
|---|---:|---:|---:|---:|
| `gpt -> gemini judge` | `33` | `8` | `41` | `0.804878` |
| `gemini -> gpt judge` | `18` | `8` | `26` | `0.692308` |

### B. 四篇 paper 的 gold vs generated 節點規模

| Paper | Gold nodes | Gold levels | GPT nodes | GPT levels | Gemini nodes | Gemini levels |
|---|---:|---|---:|---|---:|---|
| `2307.05527` | `30` | `{1:6,2:10,3:14}` | `34` | `{1:7,2:27}` | `18` | `{1:7,2:11}` |
| `2409.13738` | `27` | `{1:10,2:15,3:2}` | `35` | `{1:10,2:25}` | `29` | `{1:8,2:21}` |
| `2511.13936` | `36` | `{1:7,2:15,3:14}` | `35` | `{1:8,2:27}` | `19` | `{1:8,2:11}` |
| `2601.19926` | `7` | `{1:4,2:3}` | `40` | `{1:9,2:31}` | `25` | `{1:10,2:15}` |

### C. `2409.13738` / `2601.19926` 的 judge 低分點高度一致

| Paper | Run | 最低維度 |
|---|---|---|
| `2409.13738` | `gpt -> gemini judge` | `详略得当 2.5`、`逻辑深度 5.0`、`简洁性 5.5` |
| `2409.13738` | `gemini -> gpt judge` | `详略得当 5.5`、`逻辑深度 6.5`、`学术价值 6.5` |
| `2601.19926` | `gpt -> gemini judge` | `详略得当 2.5`、`逻辑深度 5.0`、`简洁性 5.5` |
| `2601.19926` | `gemini -> gpt judge` | `章节互斥性 6.5`、`学术价值 6.5`、`详略得当 7.0` |

### D. 這份報告依賴的主要 evidence files

- [`docs/cross_judge_cli_results_2026-04-09.md`](./cross_judge_cli_results_2026-04-09.md)
- [`docs/guides/meow_evaluation_assets.md`](../guides/meow_evaluation_assets.md)
- [`scripts/run_codex_meow_outline_blind.sh`](../scripts/run_codex_meow_outline_blind.sh)
- [`scripts/codex_meow_outline_blind_lib.py`](../scripts/codex_meow_outline_blind_lib.py)
- [`scripts/evaluate_chatgpt_meow_blind_batch.py`](../scripts/evaluate_chatgpt_meow_blind_batch.py)
- [`scripts/combine_scores.py`](../scripts/combine_scores.py)
- [`prompts/meow_llm_judge_6d_source_system.txt`](../prompts/meow_llm_judge_6d_source_system.txt)
- [`prompts/meow_llm_judge_6d_source_user.txt`](../prompts/meow_llm_judge_6d_source_user.txt)
- [`third_party/repos/Meow-Data-curation/utils/data_to_trainformat/formet_to_train_data.py`](../../third_party/repos/Meow-Data-curation/utils/data_to_trainformat/formet_to_train_data.py)
- [`third_party/repos/Meow-Data-curation/utils/add_cot/add_cot.py`](../../third_party/repos/Meow-Data-curation/utils/add_cot/add_cot.py)
- [`third_party/repos/Survey-Outline-Evaluation-Benckmark/scripts/evaluate_llm.py`](../../third_party/repos/Survey-Outline-Evaluation-Benckmark/scripts/evaluate_llm.py)

---

## Final Takeaway

如果只用一句白話收尾：

> 現在這個 cross-judge setup 最容易吃虧的地方，是它要求模型盲寫一篇「像樣的綜述大綱」，卻又拿 paper 真實的章節骨架當標準答案。當 paper 本身的實際 outline 很扁平、很 paper-specific，而模型自然會寫出更完整的 taxonomy 時，Structural Distance 就會先炸；再加上 judge 又特別討厭平均拆章、缺三級標題、標題太長，最後看起來就像「分數很差」，但其實很多時候是任務和評分標準沒對準。
