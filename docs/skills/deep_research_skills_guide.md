# Deep-Research-skills 中文說明

## 文件目的

這份文件整理你目前已安裝到本機 Codex 的 `Weizhena / Deep-Research-skills`，重點不是泛泛介紹 repo，而是說明：

- 本機實際裝了哪些 skills
- 這套 workflow 怎麼跑
- `web_researcher` agent 在做什麼
- 哪些設定是必要的
- 目前已知的本機注意事項

本文以你現在的本機安裝結果為準。

## 本機安裝結果

已安裝的 skills：

1. `research`
2. `research-add-items`
3. `research-add-fields`
4. `research-deep`
5. `research-report`

已安裝的 agent 與模組：

- `~/.codex/agents/web-researcher.toml`
- `~/.codex/agents/web-search-modules/academic-papers.md`
- `~/.codex/agents/web-search-modules/chinese-tech.md`
- `~/.codex/agents/web-search-modules/general-web.md`
- `~/.codex/agents/web-search-modules/github-debug.md`
- `~/.codex/agents/web-search-modules/stackoverflow.md`

已新增的 Codex config 關鍵設定：

- `suppress_unstable_features_warning = true`
- `features.multi_agent = true`
- `features.default_mode_request_user_input = true`
- `[agents.web_researcher]`

## 這套技能在做什麼

`Deep-Research-skills` 不是一個單點功能 skill，而是一套有狀態的多階段研究工作流。它把調研拆成兩個主階段：

1. **Outline 生成階段**
2. **Deep research 執行階段**

再加上一個最後的報告彙總階段。

它適合的場景包括：

- 學術研究
- benchmark / 文獻整理
- 技術選型
- 產品/市場/競品調研
- 公司/投資/盡調類研究

這套 workflow 的核心觀念是：

- 先定義要研究哪些對象
- 再定義每個對象要收集哪些欄位
- 再由多個 research agent 平行搜集資訊
- 最後統一彙整成 Markdown 報告

## 整體工作流

### Phase 1: `research`

先做前置研究與 outline 生成。

它會先用模型既有知識產出：

- 該主題的主要研究對象清單
- 建議的欄位框架

接著再做 web search 補充：

- 補缺漏的 items
- 補更多 field 維度
- 讓使用者指定時間範圍

最後它會產出兩個核心檔案：

- `outline.yaml`
- `fields.yaml`

### Phase 2: `research-add-items`

如果你覺得第一階段漏了研究對象，就用這個 skill 補 item。

它會：

- 自動尋找目前工作目錄下的 `outline.yaml`
- 讓你補指定 item
- 可選擇再啟動 web search 找更多 item
- 去重後原地更新 `outline.yaml`

### Phase 3: `research-add-fields`

如果你覺得欄位定義不夠，就用這個 skill 補 field。

它會：

- 自動尋找 `fields.yaml`
- 讓你直接手動補 field，或透過 web search 補常見欄位
- 讓你指定 category 與 detail level
- 原地更新 `fields.yaml`

### Phase 4: `research-deep`

這是核心執行階段。

它會：

- 讀取 `outline.yaml`
- 讀取 items 與 execution config
- 檢查已有的 JSON 輸出，支援 resume
- 按 batch 啟動多個 background research agents
- 每個 agent 負責一到多個 items
- 依 `fields.yaml` 的欄位結構輸出結構化 JSON

對每個研究對象，它要求 agent：

- 依 fields 定義輸出 JSON
- 對不確定值加上 `[uncertain]`
- 在 JSON 最後加入 `uncertain` 陣列
- 所有欄位值一律用英文
- 最後一定要跑 `validate_json.py`

### Phase 5: `research-report`

當所有 item 的 JSON 都完成後，用這個 skill 產生最終報告。

它會：

- 讀取所有 JSON
- 讀取 `fields.yaml`
- 根據欄位結構整理所有內容
- 跳過帶 `[uncertain]` 的值
- 跳過 `uncertain` 陣列中列出的欄位
- 生成 `generate_report.py`
- 最後產出 `report.md`

它還有幾個比較細的設計：

- 會先掃描適合放在 TOC 的摘要欄位，例如 star、score、release_date
- 支援 flat JSON 與 nested JSON
- 支援 category 名稱多語 mapping
- 未定義在 `fields.yaml` 的額外欄位會收進 `Other Info`

## 核心檔案結構

這套 workflow 最重要的不是 prompt 本身，而是它的中間資料結構。

### `outline.yaml`

這個檔案主要負責：

- 研究主題
- 研究 items 列表
- 執行參數

其中 execution 會包含：

- `batch_size`
- `items_per_agent`
- `output_dir`

### `fields.yaml`

這個檔案定義每個研究對象應該有哪些欄位。

欄位通常會按 category 分組，並帶：

- field 名稱
- field 描述
- `detail_level`

它其實就是整個 deep research 的 schema。

### `results/*.json`

每個 item 最後各自輸出一個 JSON。

這些 JSON 會被：

- `research-deep` 用來做 resume 判斷
- `research-report` 用來彙整報告

### `report.md`

最終輸出報告。通常是：

- TOC
- 每個 item 的彙總內容
- 依 field category 展開的詳細內容

## 5 個 skill 的實際定位

### `research`

- 功能：建立研究大綱與欄位結構
- 關鍵輸出：`outline.yaml`、`fields.yaml`
- 適合：開始一個新調研專案時

### `research-add-items`

- 功能：補研究對象
- 關鍵輸出：更新 `outline.yaml`
- 適合：items 不完整時

### `research-add-fields`

- 功能：補欄位定義
- 關鍵輸出：更新 `fields.yaml`
- 適合：schema 不夠細時

### `research-deep`

- 功能：批次平行做深度調研
- 關鍵輸出：每個 item 的 JSON
- 適合：outline 與 fields 都確認後

### `research-report`

- 功能：將 JSON 結果轉成 Markdown 報告
- 關鍵輸出：`generate_report.py`、`report.md`
- 適合：deep research 完成後

## `web_researcher` agent 在做什麼

這套 skill 能跑起來的關鍵，不只是 `SKILL.md`，還包括 `web_researcher` agent。

它的角色是專職做網路研究，設定上大致是：

- model: `gpt-5.4`
- reasoning_effort: `high`
- sandbox: `read-only`
- web_search: `live`

它的 developer instructions 很長，但重點可以壓成幾點：

- 不要用其他 skills
- 你是專門做網路研究的 agent
- 要生成多組 query
- 要去多來源比對
- 要特別注意時間、版本、來源可靠性
- 回傳時一定要附 source links

## `web-search-modules` 的用途

`web_researcher` 不會直接亂搜，它被要求先載入對應的策略模組，再開始查。

目前安裝的模組有五個：

### `github-debug.md`

- 用途：查 GitHub Issues 類的 bug、版本問題、workaround
- 適合：debug、issue 追蹤、library bug 調查

### `stackoverflow.md`

- 用途：查技術問答、API 用法、程式實作問題
- 適合：Stack Overflow / Stack Exchange 類型研究

### `general-web.md`

- 用途：查最佳實務、新聞、比較研究、一般 web 資訊
- 適合：產品比較、best practices、社群經驗

### `academic-papers.md`

- 用途：查學術論文
- 適合：Google Scholar、arXiv、Semantic Scholar、Hugging Face Papers 等來源

### `chinese-tech.md`

- 用途：查中文技術社群
- 適合：CSDN、Juejin、Zhihu、V2EX、云厂商社区等來源

這套模組化設計的好處是：

- 調研不會只有單一來源
- 類型不同的研究會走不同策略
- 同一個 task 可以混用多個模組

## 這套 skill 的優點

### 1. workflow 很完整

它不是「幫你搜一下」，而是從 schema 定義一路做到報告生成。

### 2. 中間產物清楚

`outline.yaml`、`fields.yaml`、`results/*.json`、`report.md` 的分工很清楚，方便中途修改與 resume。

### 3. 平行研究設計合理

`research-deep` 有 batch、resume、items_per_agent 這些控制點，不是一次把所有東西亂丟給一群 agent。

### 4. 適合結構化比較

這套非常適合做「同一組欄位下，研究多個對象」的任務，例如：

- 比較多個 AI agent
- 比較多個 framework
- 比較多篇論文
- 比較多家公司/產品

## 目前你這台機器上的注意事項

### 1. 需要重啟 Codex

新的 skills 和 agent 是裝進 `~/.codex` 了，但要在新 session 裡被完整發現，還是需要重啟 Codex。

### 2. 它依賴 multi-agent 與 request-user-input 類能力

這套 workflow 本質上高度依賴：

- multi-agent
- 使用者確認節點
- live web search

如果這些功能在 session 裡沒打開，它的效果會打折。

### 3. upstream skill 有硬編路徑問題

原始 `research-deep` 內建 prompt 把驗證腳本寫死成：

```bash
python /home/weizhena/.codex/skills/research/validate_json.py ...
```

這在你這台 macOS 機器上會失效。

我已經把本機安裝版本改成：

```bash
python $HOME/.codex/skills/research/validate_json.py ...
```

這是必要修正，不然 deep phase 第一次驗證就會因路徑錯誤失敗。

### 4. 官方安裝腳本不適合直接套到你現在的 config

repo 內的 `scripts/install-codex.sh` 會直接重寫整段 `[features]`。

你的 `~/.codex/config.toml` 原本已經有自己的設定，所以這次我是做「最小合併」而不是直接跑它。

## 你之後怎麼用

如果要用自然語言觸發，可以這樣理解：

### 開始一個新研究

用 `research` 產生 outline 和 fields。

例如：

```text
Use the research skill to build an outline for AI Agent Demo 2025
```

### 補研究對象

如果 items 不夠，使用 `research-add-items`。

### 補欄位

如果 schema 不夠細，使用 `research-add-fields`。

### 正式跑深度研究

outline 和 fields 都確認後，使用 `research-deep`。

### 最後出報告

所有 JSON 都完成後，使用 `research-report`。

## 這套技能適不適合你現在這個 repo

我認為是適合的，而且比一般通用技能更貼近你現在的工作型態。

你目前這個 repo 常做的事情包括：

- outline / taxonomy 類結構整理
- prompt / provenance 分析
- paper / code / artifact 對照
- literature review 與研究型整理

`Deep-Research-skills` 雖然不是專門為 MEOW 這類 outline 分析設計，但它的工作習慣和你的 repo 很相容：

- 先定框架
- 再補 items / fields
- 再批量做深調研
- 最後統一產報告

如果你之後想把某個 paper family、方法族群、工具生態或 benchmark 系列做成結構化調研，這套 skill 很有用。

## 總結

`Deep-Research-skills` 比較像一個「研究工作流框架」，不是單一 skill。

它最適合的任務是：

- 多對象
- 結構化欄位
- 需要上網查證
- 需要分階段確認
- 最後要產出可讀報告

你現在本機已經具備：

- 5 個 research skills
- 1 個 web research agent
- 5 個 research modules
- 必要的 Codex config

所以只差一件事：

- **重啟 Codex**

重啟後，這套 skills 才會在新的 session 裡完整生效。
