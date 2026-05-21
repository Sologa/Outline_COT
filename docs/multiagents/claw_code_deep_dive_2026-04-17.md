# `Sologa/claw-code` Deep Dive（2026-04-17）

本文件記錄對 [`Sologa/claw-code`](https://github.com/Sologa/claw-code) 的實作研究，目的是理解一個公開 agent harness 如何處理：

- subagent runtime
- output / manifest persistence
- task / team / cron lifecycle
- background shell vs background LLM worker
- CLI surface 與實作成熟度之間的差距

研究前提：

- 這個 repo 是研究樣本，不是 Anthropic 官方 Claude Code 原始碼。
- 本次本地檢視的 commit 是：`e874bc6a4467158d91d644783c497c8eca472874`

## 0. 證據地圖

如果之後只想快速回到最核心的實作點，優先看這些符號或檔案：

- `rust/crates/tools/src/lib.rs`
  - `execute_agent_with_spawn()`
  - `spawn_agent_job()`
  - `run_agent_job()`
  - `build_agent_runtime()`
  - `allowed_tools_for_subagent()`
  - `write_agent_manifest()`
  - `persist_agent_terminal_state()`
  - `agent_store_dir()`
- `rust/crates/runtime/src/task_registry.rs`
- `rust/crates/runtime/src/team_cron_registry.rs`
- `rust/crates/runtime/src/bash.rs`
- `rust/crates/commands/src/lib.rs`
- `rust/README.md`
- `PHILOSOPHY.md`
- `PARITY.md`

## 1. Repo 自我定位與整體架構

### 1.1 README 的定位

從 repo 自己的 README 來看，它把自己定位成：

- `claw` CLI agent harness 的 public Rust implementation
- canonical implementation 位於 `rust/`
- `src/` + `tests/` 比較像 companion Python/reference workspace，而不是主 runtime surface

這點很重要，因為它直接說明：

- 真正需要研究的是 `rust/`
- 不應把零散 Python / 測試輔助檔誤當成產品核心

### 1.2 `PHILOSOPHY.md` 暗示的更大系統邊界

`PHILOSOPHY.md` 的價值不在於宣言，而在於它透露了這個 repo 認為真正的 coordination system 其實不只在此 repo 內。

文件中提到的三部分：

- `OmX (oh-my-codex)`：workflow layer
- `clawhip`：event / notification router
- `OmO (oh-my-openagent)`：multi-agent coordination

這個訊號代表：

- `claw-code` repo 本身不一定承擔全部 coordination 邏輯
- 真正的多代理協作可能被拆散到外部 companion system 中

因此：

- 如果只看 `claw-code` runtime，就能研究 subagent 與局部 orchestration
- 但不應想當然地把它等同於完整生產級 team platform

## 2. 真正的 subagent 執行路徑

關鍵檔案：

- `rust/crates/tools/src/lib.rs`

### 2.1 入口：`execute_agent_with_spawn()`

這條路徑做的事非常具體：

1. 驗證輸入，例如 description / prompt 不得為空
2. 產生 `agent_id`
3. 解析 output directory
4. 建立：
   - `output_file`
   - `manifest_file`
5. 標準化 `subagent_type`
6. 解析 model
7. 建立 system prompt
8. 根據 `subagent_type` 產生 allowed tools
9. 先把任務 header 與 prompt 寫入 output markdown
10. 建立初始 manifest，狀態標記為 `running`
11. 把 manifest 寫入磁碟
12. 呼叫 `spawn_fn(job)` 啟動背景工作

這代表：

- `Agent` 工具不是單純在記憶體裡開一個物件
- 它一開始就把任務與狀態 materialize 成磁碟 artifact

### 2.2 背景執行：`spawn_agent_job()`

`spawn_agent_job()` 的實作顯示：

- 它用的是 `std::thread::Builder::new().spawn(...)`
- thread name 會帶有 agent id
- thread 內用 `catch_unwind` 包住真正的 job 執行
- 如果 job 失敗或 panic，會把 terminal state 寫回 manifest

這說明：

- 這裡的 subagent 不是外部 CLI subprocess
- 它是同一個進程內的 background Rust thread

### 2.3 真正跑模型：`run_agent_job()` + `build_agent_runtime()`

這裡是最關鍵的 implementation detail。

`run_agent_job()` 會：

- 先建 runtime
- 設定 `DEFAULT_AGENT_MAX_ITERATIONS`
- 用 delegated prompt 跑一個 turn
- 擷取 final assistant text
- 把結果作為 terminal state 寫回

而 `build_agent_runtime()` 顯示：

- 每個 subagent 會有新的 `ConversationRuntime`
- runtime 會使用新的 `Session::new()`
- 會建立獨立的 API client
- 會建立獨立的 `SubagentToolExecutor`
- 權限由 `PermissionEnforcer` 控制

這些細節加起來，結論很明確：

- 這條路徑是真正的「隔離 LLM context worker」
- 它不是只在主會話裡模擬一個角色

### 2.4 測試側也支持「isolated session」這個判斷

`tools/src/lib.rs` 內有測試 `subagent_runtime_executes_tool_loop_with_isolated_session()`。

這個測試的重點不是功能炫技，而是它明確做了幾件事：

- 用新的 `ConversationRuntime`
- 明確使用 `Session::new()`
- 只給 `read_file` 權限
- 跑 tool loop
- 驗證最終輸出與 tool result 都被寫進 session message 流

這使得前述判斷不只是讀 production path 的推論，也有測試側的佐證：

- 作者確實把 subagent 當成獨立 session runtime
- 而不是只是 prompt 層的角色切換

## 3. subagent 的 prompt、工具與權限模型

### 3.1 system prompt 怎麼補上 subagent 身分

`build_agent_system_prompt()` 會先載入基礎 system prompt，再額外 append 一段 subagent 指示，大意是：

- 你是一個 background sub-agent
- 只處理 delegated task
- 只能用可用工具
- 不要問使用者問題
- 用簡潔結果收尾

這意味著：

- subagent 身分並不是單靠外部敘述存在
- runtime 會明確在 system prompt 層補上 worker 規範

### 3.2 `subagent_type` 對工具能力的影響

`allowed_tools_for_subagent()` 直接把不同類型映射到不同 whitelist。

目前值得注意的類型：

- `Explore`
  - 以讀、搜、Web 類工具為主
- `Plan`
  - 也是讀與搜，但允許 `TodoWrite` 與 `SendUserMessage`
- `Verification`
  - 允許 `bash`、`PowerShell`、Web、`TodoWrite`、`SendUserMessage`
- `general-purpose`
  - 工具最寬，包含 write/edit/bash/Web/Notebook 等

這個設計透露兩層意思：

1. subagent 不是只有 prompt 專業分工，還有實際 capability scoping
2. repo 作者理解 multi-agent 不是只靠人設，而是要靠工具邊界來收斂風險

### 3.3 預設模型與類型正規化

從同一檔案還可以再補出兩個小而重要的訊號：

- `DEFAULT_AGENT_MODEL` 目前是 `claude-opus-4-6`
- `normalize_subagent_type()` 會把 alias 正規化成幾個較穩定的類型，例如：
  - `general-purpose`
  - `Explore`
  - `Plan`
  - `Verification`
  - `claw-guide`
  - `statusline-setup`

這意味著：

- subagent type 並不是完全自由文本
- runtime 對某些常用 worker 類型有內建心智模型

## 4. subagent 的磁碟狀態與 artifact

### 4.1 會落盤哪些東西

`claw-code` 的 subagent 至少會產生兩類 artifact：

- `output_file`：markdown 檔
- `manifest_file`：JSON 檔

output file 一開始會寫：

- agent task header
- id
- name
- description
- subagent type
- created_at
- prompt

在 terminal state 時，`append_agent_output()` 會追加：

- `status`
- `blocker`（若失敗）
- `final response`
- `error`

### 4.2 manifest 會記哪些資訊

從 `write_agent_manifest()` 和 `persist_agent_terminal_state()` 可以看出，manifest 會保存：

- `agent_id`
- `name`
- `description`
- `subagent_type`
- `model`
- `status`
- `output_file`
- `manifest_file`
- `created_at`
- `started_at`
- `completed_at`
- `lane_events`
- `current_blocker`
- `derived_state`
- `error`

這讓 `claw-code` 的 subagent 具有一種很實際的特性：

- 它不是只有 runtime 當下的 memory state
- 它有事後可審計的 file-based trail

### 4.3 agent store 放哪裡

`agent_store_dir()` 的邏輯是：

- 若設了 `CLAWD_AGENT_STORE`，直接用它
- 否則取目前工作目錄的 ancestor 來推導 `.clawd-agents`
- 再不行就回到 `cwd/.clawd-agents`

這個設計的意義是：

- 子代理結果有穩定、可搜尋、可回讀的落點
- 這比只有 terminal scrollback 更接近真正的 worker artifact store

## 5. `task/team/cron` 的成熟度判斷

### 5.1 `TaskRegistry`

`TaskRegistry` 是 thread-safe 的 in-memory registry。

它存的內容包括：

- `task_id`
- `prompt`
- `description`
- `task_packet`
- `status`
- timestamps
- `messages`
- `output`
- `team_id`

重要的是：

- `run_task_create()`、`run_task_packet()` 等工具 handler 基本上是在 registry 裡建立記錄並回傳 metadata
- 沒有對應的外部背景執行器被綁到 task create path 上

所以它比較像：

- task metadata lifecycle
- state holder

而不是：

- 真正的 distributed task runner

### 5.2 `TeamRegistry`

`run_team_create()` 的動作主要是：

- 從輸入裡抽出 `task_id`
- 建一個 team record
- 把 team id 寫回各 task 的 `team_id`

這代表目前的 `team` 比較像：

- 一個 grouping / bookkeeping surface

而不是：

- 有自主溝通、分工、重試、仲裁能力的 multi-agent team runtime

### 5.3 `CronRegistry`

`run_cron_create()` 會把：

- `schedule`
- `prompt`
- `description`

這些資訊記進 registry。

但根據 `PARITY.md` 的說法，目前 team/cron 還沒有變成真正的 scheduler 或 worker fleet。這和前述 registry-based shape 是一致的。

## 6. background shell 與 background LLM worker 的分離

### 6.1 bash background path

`rust/crates/runtime/src/bash.rs` 顯示：

- `run_in_background=true` 時，bash 直接 `spawn()` OS child process
- `stdin/stdout/stderr` 都導向 `null`
- 回傳 `backgroundTaskId`
- 不建立 subagent manifest
- 不建立獨立 LLM session

這是一種典型的 shell 背景程序語義。

### 6.2 為什麼這和 subagent 不一樣

subagent path 具備：

- 新的 `ConversationRuntime`
- 新的 `Session::new()`
- tool whitelist
- permission enforcement
- output markdown
- manifest JSON
- lane events / blocker / derived state

所以不能把：

- bash background
- subagent delegation

混成同一件事。

在 `claw-code` 內，這兩條路徑代表的是兩種不同抽象：

- 一個是 OS process backgrounding
- 一個是 LLM worker orchestration

## 7. CLI surface 與 runtime 成熟度的落差

從 `rust/README.md` 與 `crates/commands/src/lib.rs` 可看到：

- `/parallel`
- `/agent`
- `/subagent`
- `/team`
- `/cron`

這些都已經出現在 user-facing command surface 上。

更具體地說，`commands/src/lib.rs` 已經把：

- `/cron`
- `/team`
- `/parallel`
- `/agent`
- `/subagent`

都放進 slash command spec。

這代表：

- repo 作者很重視讓 CLI 表面呈現 agentic workflow

但如果往 runtime 下鑽：

- `subagent` 的執行路徑比較成熟
- `task/team/cron` 更像 lifecycle registry

所以目前較合理的解讀是：

- CLI surface 告訴你作者想把產品帶去哪裡
- runtime maturity 告訴你哪些部分已經真的跑起來

兩者不能簡單等號。

### 7.1 一個更保守但更準確的說法

截至本次檢視的 commit，比較穩的說法是：

- `subagent` 是較成熟的 runtime path
- `task/team/cron` 已經進入 CLI vocabulary，但 runtime 仍偏 registry-oriented
- CLI surface 告訴你作者希望它成為一個 agentic harness
- runtime 細節則告訴你目前哪些部分真的比較像完整 worker system

## 8. 對 `claw-code` 的總體判斷

截至本次檢視的 commit，可用下面幾句話總結：

1. `claw-code` 是有研究價值的公開 agent harness 樣本。
2. 它的 subagent path 是真實的 background LLM worker，而不是假裝出來的語義角色。
3. 它的 task/team/cron 目前主要是 registry / orchestration metadata，而不是完整 worker fleet。
4. 它把 shell background 與 LLM worker delegation 分成兩條不同機制。
5. 它的哲學文件暗示，真正完整的 coordination system 可能部分位於 repo 外部伴隨系統中。

因此：

- 若研究目標是「subagent runtime 長什麼樣」，它很有價值。
- 若研究目標是「Claude 官方產品現在怎麼做」，則不能把它直接當官方真相。
