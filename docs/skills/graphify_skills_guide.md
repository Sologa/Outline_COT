# graphify 中文說明

## 文件目的

這份文件整理你目前安裝到本機 Codex 的 `graphify`，重點不是只介紹 GitHub repo，而是說明：

- 本機實際怎麼安裝
- 哪些檔案已經被寫入
- 在 Codex 裡要怎麼叫用
- 它會產生哪些輸出
- 目前哪些功能可用、哪些還是選配

本文以你這台機器目前的安裝結果為準。

## 本機安裝結果

目前已完成的安裝包含四部分：

1. `graphify` CLI 已安裝
2. `graphify` skill 已安裝
3. 這個 repo 已寫入 graphify 的 Codex 常駐規則
4. 這個 repo 已新增 Codex hook

### CLI

- 套件版本：`graphifyy 0.3.21`
- 可執行指令：`graphify`
- PATH 入口：`~/.local/bin/graphify`
- 實際 Python script 來源：`~/Library/Python/3.13/bin/graphify`

之所以會有這個 PATH 包裝，是因為 `pip --user` 預設把 script 放到 `~/Library/Python/3.13/bin/`，該路徑不在你目前 shell PATH 內，所以另外做了一層 symlink 到 `~/.local/bin/graphify`。

### Skill 安裝路徑

官方 `graphify install --platform codex` 這版實際會寫到：

- `~/.agents/skills/graphify/SKILL.md`

但你這台目前既有 skills 生態主要仍然走 `~/.codex/skills/`，因此另外同步鏡像到：

- `~/.codex/skills/graphify/SKILL.md`
- `~/.codex/skills/graphify/.graphify_version`

也就是說，目前兩邊都有：

- `~/.agents/skills/graphify`
- `~/.codex/skills/graphify`

這樣做是為了避免不同 Codex 版本對 skill discovery path 的差異，讓新舊路徑都能找得到。

### Repo 內的常駐設定

已對目前 repo 寫入：

- [AGENTS.md](/Users/xjp/Desktop/Outline_COT/AGENTS.md)
- [.codex/hooks.json](/Users/xjp/Desktop/Outline_COT/.codex/hooks.json)

`AGENTS.md` 新增了一個 `## graphify` 區段，要求 agent：

- 在回答 architecture / codebase 問題前先讀 `graphify-out/GRAPH_REPORT.md`
- 如果存在 `graphify-out/wiki/index.md`，優先走 wiki，而不是直接翻 raw files
- 修改 code 後可用 graphify 的 watch rebuild 函數更新圖譜

`.codex/hooks.json` 新增了一個 `PreToolUse` hook。它的作用是：

- 當 repo 裡已經有 `graphify-out/graph.json`
- 且之後要跑 `Bash` 工具時
- 先注入一條提醒，要求優先看 `graphify-out/GRAPH_REPORT.md`

這是 graphify 在 Codex 上的「always-on」整合方式。

## 目前已安裝的功能範圍

### 已安裝

目前實際裝上的功能是：

- base CLI
- `pdf`
- `office`
- `watch`

這代表目前可直接支援的範圍包括：

- 一般 code / text / docs corpus 圖譜化
- PDF 讀取
- `.docx` 讀取
- `.xlsx` 讀取
- 檔案變更監看與重建

### 目前沒有額外裝的選配

目前沒有另外安裝：

- `leiden` / `graspologic`
- `neo4j`
- `mcp`

這三個未安裝的影響如下：

- 社群分群目前會走 `NetworkX` 內建的 `Louvain` fallback，而不是 `graspologic` 的 `Leiden`
- 目前不會直接推送到 Neo4j
- 目前不會啟用 graphify 的 MCP server 模式

但核心功能仍然可用，因為 `graphify` 的 community detection 本來就內建 fallback：

- 有 `graspologic` 時先用 `Leiden`
- 沒有時退回 `NetworkX` 的 `Louvain`

所以目前這個安裝不是「半殘」，而是「核心可用、少數進階選配未補」的狀態。

## graphify 在做什麼

`graphify` 的核心不是單純做 RAG，也不是只抽 keyword。它要做的是把一個資料夾內的內容轉成：

- 可查詢的 knowledge graph
- 社群分群結果
- 可瀏覽的 HTML / wiki / JSON / report 輸出

它的官方定位可以簡化成：

> any input (code, docs, papers, images) -> knowledge graph -> clustered communities -> HTML + JSON + audit report

它最適合的場景包括：

- 第一次接觸一個 codebase，想先理解結構
- 想把 papers、notes、tweets、screenshots 放進同一個知識圖譜
- 想在長期工作資料夾上做 persistent graph，而不是每次重新讀檔
- 想問「某個概念和另一個模組之間有沒有連結」

## 在 Codex 裡怎麼叫用

雖然 skill frontmatter 寫的是 `/graphify`，但在 Codex 裡實際要用的是：

```text
$graphify .
```

也就是：

- Claude Code 習慣 `/graphify`
- Codex 習慣 `$graphify`
- 注意：上面是 Codex skill 入口，不是本機 shell 指令。這台機器上 shell 形式的 `graphify .` / `graphify . --update` 曾經回報 `unknown command`，所以 repo 內不要再把它寫成可直接執行的 shell rebuild command。
- 如果只是 code 檔案修改後要快速刷新既有 graph，使用 Python package API：

```bash
python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"
```

- 如果要重做完整 semantic graph，從 Codex 對話叫用 `$graphify .` 或按 skill workflow 走 package API / subagent pipeline，先確認 `.graphifyignore` 和 detect scope。

常用入口包括：

```text
$graphify .
$graphify <path>
$graphify <path> --mode deep
$graphify <path> --update
$graphify <path> --cluster-only
$graphify <path> --no-viz
$graphify <path> --svg
$graphify <path> --graphml
$graphify <path> --neo4j
$graphify <path> --mcp
$graphify <path> --watch
$graphify add <url>
$graphify query "<question>"
$graphify query "<question>" --dfs
$graphify path "AuthModule" "Database"
$graphify explain "SwinTransformer"
```

## 主要輸出長什麼樣

`graphify` 的輸出根目錄通常是：

- `graphify-out/`

其中最重要的檔案包括：

- `graphify-out/graph.json`
- `graphify-out/GRAPH_REPORT.md`
- `graphify-out/wiki/index.md`
- `graphify-out/cache/`

選配輸出可能還包括：

- `graphify-out/graph.html`
- `graphify-out/graph.svg`
- `graphify-out/graph.graphml`
- `graphify-out/cypher.txt`

可以把它們大致理解成：

- `graph.json`：圖譜資料本體
- `GRAPH_REPORT.md`：給人看的 plain-language 摘要，特別強調 god nodes 與社群結構
- `wiki/index.md`：更適合依節點/主題瀏覽的 wiki 形式輸出
- `cache/`：中間抽取快取
- `graph.html`：互動式視覺化
- `graph.svg`：適合嵌進 GitHub / Notion 的靜態圖
- `graph.graphml`：丟進 Gephi / yEd 類工具
- `cypher.txt`：給 Neo4j 的匯入語句

## 它和一般搜尋有什麼差別

`graphify` 的主張不是「比 grep 快」，而是：

- 把跨檔案關係持久化
- 把抽取到的關係標記 provenance
- 讓 agent 不用每次從 raw file 重新開始

它特別強調三件事：

1. persistent graph
2. honest audit trail
3. cross-document surprise

也就是：

- 關係會被存下來，不會隨 session 消失
- edge 會區分 `EXTRACTED`、`INFERRED`、`AMBIGUOUS`
- 會用社群分群找出跨文件的潛在連結

## 本機這次安裝對 repo 帶來的實際效果

你目前這個 repo 安裝 graphify 之後，新增的不是只有一個 skill 名稱，而是三層效果：

### 1. 新 session 可發現 `graphify` skill

因為已寫入：

- `~/.agents/skills/graphify/SKILL.md`
- `~/.codex/skills/graphify/SKILL.md`

所以之後新 session 有機會直接發現它。

### 2. 這個 repo 內有 always-on graph reminder

因為已寫入：

- [AGENTS.md](/Users/xjp/Desktop/Outline_COT/AGENTS.md)
- [.codex/hooks.json](/Users/xjp/Desktop/Outline_COT/.codex/hooks.json)

只要這個 repo 之後真的產出 `graphify-out/graph.json`，Codex 在跑 Bash 前就會看到 graphify 提醒。

### 3. 你現在的全域 Codex config 已具備 `multi_agent = true`

這不是 graphify 這次新寫入的，而是你之前裝 `Deep-Research-skills` 時已經開啟。

因此 graphify README 提到的 Codex 前置條件：

- `~/.codex/config.toml`
- `[features]`
- `multi_agent = true`

你這台目前已經滿足。

## 目前沒有做的事

這次安裝沒有做以下動作：

- 沒有安裝 `graphify hook install`
- 沒有替你在 repo 內直接跑一次 `$graphify .`
- 沒有安裝 `neo4j` / `mcp`
- 沒有安裝 `graspologic`

原因很簡單：

- `hook install` 會把 graph rebuild 綁到 git commit / checkout，屬於更侵入式的 workflow 變更
- 真正執行 `$graphify .` 會開始對當前資料夾做抽取與建圖，這已經超出單純「安裝 skill」的範圍
- `graspologic` 這條依賴比較重，但不是核心可用性的必要條件

如果你之後要，我可以再幫你做第二步：

- 直接在這個 repo 跑一次 `graphify`
- 看輸出的 `graphify-out/GRAPH_REPORT.md`
- 確認它對這個 outline / MEOW 分析 workspace 有沒有實際價值

## 短結論

這次安裝後，你現在得到的是：

- 可執行的 `graphify` CLI
- 可被 Codex 發現的 `graphify` skill
- repo 內的 graphify always-on 規則
- 核心可用的 graphify 能力

如果你接下來真的要用它，最值得先做的不是再補更多依賴，而是挑一個小範圍資料夾跑一次，確認：

- 圖譜品質
- `GRAPH_REPORT.md` 是否有用
- 對你這個 prompt / outline provenance repo 是否真的比直接 grep 更有增益
