# Gemini CLI 單次非互動呼叫指南

## 文件目的

這份文件記錄 `Gemini CLI` 在「單次、獨立、非互動」情境下的使用方式，目標是讓它可以像一般 shell command 一樣被腳本、batch workflow、或 CI 任務直接呼叫。

本文特別區分：

- 官方文件明確記載的行為
- 我在本機實測確認的行為

避免把文件推論和本機觀察混在一起。

## 適用範圍

本文說的「單次使用」指的是：

- 不進入互動 TUI
- 直接從 shell 啟動一次
- 執行完輸出結果後結束行程

在 `Gemini CLI` 裡，這個模式的正式入口是：

```bash
gemini -p 'your prompt here'
```

重點：

- `Gemini CLI` 沒有像 `codex exec` 那樣的獨立 `exec` 子命令。
- 官方文件把這種模式稱為 `non-interactive` 或 `headless mode`。
- 若只寫 `gemini 'prompt'`，預設仍是互動模式；要單次執行，必須明確使用 `-p` 或 `--prompt`。

## 本機驗證環境

以下行為已於本機驗證：

- 日期：`2026-04-09`
- `gemini --version`：`0.36.0`
- 安裝來源：Homebrew `gemini-cli`

## 最小可用用法

### 1. 最基本的單次呼叫

```bash
gemini -p 'Summarize this repository in 5 bullet points.'
```

這會：

- 以非互動模式執行
- 產生一個回應
- 輸出後結束

### 2. 給腳本用的 JSON 輸出

```bash
gemini \
  -p 'Return exactly OK' \
  --approval-mode plan \
  --output-format json
```

本機實測輸出格式為單一 JSON 物件，核心欄位包括：

- `session_id`
- `response`
- `stats`

腳本通常只需要讀 `response`。

### 3. 給串流處理用的事件流輸出

```bash
gemini \
  -p 'Return exactly OK' \
  --approval-mode plan \
  --output-format stream-json
```

本機實測會輸出多行 JSON event，例如：

- `init`
- `message`
- `result`

這比較適合：

- 即時監看
- 自訂 client
- 需要邊收邊處理輸出的 pipeline

### 4. 把 stdin 當成上下文輸入

```bash
printf 'Alpha beta gamma' | \
gemini \
  -p 'Return the stdin word count only.' \
  --approval-mode plan \
  --output-format json
```

官方 help 明確寫到：

- `--prompt` 會在非互動模式下執行
- 若有 stdin，prompt 會附加在 stdin 後一起送入模型

實測結果也符合這個行為。

## Gemini 3.1 Pro Preview 的 reasoning / thinking 預設

如果你問的是：

- `gemini-3.1-pro-preview` 的預設 reasoning 強度是不是像 OpenAI 的 `medium`

答案是否定的。

截至本文整理時，官方文件顯示：

- `Gemini 3.1 Pro` 支援的 thinking level 是 `LOW`、`MEDIUM`、`HIGH`
- 預設不是 `MEDIUM`
- 對 `Gemini 3 / 3.1 Pro` 來說，預設是 `HIGH`
- `Gemini 3 / 3.1 Pro` 不能把 thinking 完全關掉

這點和 OpenAI 的 `reasoning_effort` 概念相近，但名稱不同：

- Gemini 原生 API 主要用 `thinking_level`
- OpenAI compatibility 介面可用 `reasoning_effort`

官方 OpenAI compatibility 文件給出的對應關係，對 `Gemini 3.1 Pro` 可整理為：

- `reasoning_effort="low"` -> `thinking_level="low"`
- `reasoning_effort="medium"` -> `thinking_level="medium"`
- `reasoning_effort="high"` -> `thinking_level="high"`
- 若未指定 `reasoning_effort`，Gemini 會使用模型自己的預設 level
- 對 `Gemini 3.1 Pro` 而言，這個預設 level 就是 `HIGH`

對 `Gemini CLI` 單次呼叫來說，還要再補一個實務差異：

- `Gemini CLI` 沒有像 OpenAI client 那樣的獨立 `--reasoning-effort` 旗標
- 也沒有一個單獨的 `--thinking-level` 啟動參數
- 若你要在 CLI 層調整 thinking，官方方向是走 `Advanced Model Configuration`
- 也就是透過 model config / alias / override，把 `generateContentConfig.thinkingConfig` 傳到底層模型

因此，若你在 `Gemini CLI` 中直接指定：

```bash
gemini -m gemini-3.1-pro-preview -p '...'
```

而沒有額外設定 thinking 相關參數，應視為使用模型預設，也就是 `HIGH`，不是 `MEDIUM`。

## 建議的腳本化模式

### 1. 穩定取得最終答案

最建議的腳本化模式是：

```bash
gemini \
  -p 'Return exactly OK' \
  --approval-mode plan \
  --output-format json >out.json 2>err.log
```

理由：

- `stdout` 可直接保留為乾淨 JSON
- `stderr` 保留診斷訊息
- 後續可以穩定用 `jq -r '.response' out.json`

例如：

```bash
gemini \
  -p 'Return exactly OK' \
  --approval-mode plan \
  --output-format json >out.json 2>err.log

jq -r '.response' out.json
```

### 2. 不要把 `stdout` 和 `stderr` 混在一起解析

本機實測確認：

- `--output-format json` 的 JSON 內容在 `stdout`
- keychain / credential fallback 訊息在 `stderr`

因此不建議：

```bash
gemini ... 2>&1 | jq ...
```

這很容易因為診斷訊息混入而破壞 JSON。

### 3. 若只做研究或分析，優先用 `--approval-mode plan`

```bash
gemini \
  -p 'Analyze the repository structure only. Do not modify files.' \
  --approval-mode plan \
  --output-format json
```

`plan` 模式適合：

- 研究
- 唯讀分析
- 先規劃再實作

但要注意：官方文件也指出，在非互動環境中，如果流程從 plan 轉入實作，CLI 可能自動切到 `YOLO mode` 以避免卡在 approval prompt。

所以：

- `--approval-mode plan` 很適合分析型任務
- 若你要求嚴格唯讀，不能只靠 `plan`
- 應搭配 policy engine 明確 `deny` 寫入或 shell tool

## 嚴格唯讀建議

若你要把 `Gemini CLI` 當成「只能看、不能改」的單次分析器，建議加 policy。

範例：

```toml
# ~/.gemini/policies/headless-readonly.toml

[[rule]]
toolName = ["write_file", "replace", "run_shell_command"]
decision = "deny"
interactive = false
priority = 1000
```

執行方式：

```bash
gemini \
  --policy ~/.gemini/policies/headless-readonly.toml \
  --approval-mode plan \
  -p 'Analyze only. Do not modify files.' \
  --output-format json
```

這比單純依賴 prompt 文字說明更可靠。

## Sandboxing

若你需要沙箱執行，可加：

```bash
gemini -s -p 'analyze the code structure'
```

官方文件也支援透過環境變數控制：

```bash
export GEMINI_SANDBOX=true
gemini -p 'run the test suite'
```

官方文件列出的 `GEMINI_SANDBOX` 可接受值包含：

- `true`
- `docker`
- `podman`
- `sandbox-exec`
- `runsc`
- `lxc`

## 認證與 Headless Mode

官方文件對 headless mode 的規則很清楚：

- 如果已經有快取的認證，headless mode 會直接沿用
- 如果沒有既有認證，必須改用環境變數方式設定認證

也就是說，第一次在純腳本環境跑 `gemini -p ...` 前，最好先確認：

- 你已完成互動登入並有 cached credentials
- 或你已正確設定 `Gemini API Key` / `Vertex AI` 環境變數

## 工作目錄與上下文

### 1. 指定工作目錄

`Gemini CLI` 本身沒有像 `codex -C DIR` 那樣的單一 `cd` flag。

因此單次使用時，最直接的方法是：

```bash
cd /path/to/project && gemini -p 'analyze this repository'
```

### 2. 額外納入目錄

官方 help 提供：

```bash
gemini \
  --include-directories ../shared,../references \
  -p 'use both codebases when answering'
```

這適合：

- 主要工作目錄之外還要讓模型讀其他目錄
- mono-repo / 多 repo / shared docs 情境

### 3. 使用新 git worktree

官方 help 提供：

```bash
gemini --worktree -p 'implement the fix'
```

如果有提供名稱，就會用指定名稱；沒提供名稱則自動生成。

## GEMINI.md 與 AGENTS.md

官方文件說明 `Gemini CLI` 會載入階層式的 `GEMINI.md` 作為上下文。

如果你想讓它也讀 `AGENTS.md`，可以在 `settings.json` 設定：

```json
{
  "context": {
    "fileName": ["AGENTS.md", "GEMINI.md"]
  }
}
```

這對把 `Gemini CLI` 的工作流對齊 `Codex` 很有幫助。

## 本機實測補充觀察

以下是本機 `gemini-cli 0.36.0` 的實測觀察，不等同於官方保證，但對腳本化很重要：

### 1. `stdout` / `stderr` 分流正常

實測命令：

```bash
gemini \
  -p 'Return exactly OK' \
  --output-format json \
  --approval-mode plan >out.json 2>err.log
```

觀察結果：

- `out.json` 是乾淨的 JSON
- `err.log` 包含 keychain 與 credential 診斷

### 2. 可能出現 keychain fallback 訊息

本機實測常見訊息：

```text
Keychain initialization encountered an error: Cannot find module '../build/Release/keytar.node'
Using FileKeychain fallback for secure storage.
Loaded cached credentials.
```

這些都出現在 `stderr`，不會污染 JSON `stdout`。

### 3. `--output-format json` 適合「拿最後答案」

如果你的腳本只要最後結果，不需要事件流，優先選：

```bash
--output-format json
```

若你需要逐步接收事件，再用：

```bash
--output-format stream-json
```

## 推薦的單次呼叫模板

### 分析型任務

```bash
gemini \
  -p 'Analyze this repository and return 5 concise findings.' \
  --approval-mode plan \
  --output-format json >out.json 2>err.log
```

### 吃 stdin 的任務

```bash
cat input.txt | \
gemini \
  -p 'Summarize the stdin content in Chinese.' \
  --approval-mode plan \
  --output-format json >out.json 2>err.log
```

### 嚴格唯讀分析

```bash
gemini \
  --policy ~/.gemini/policies/headless-readonly.toml \
  --approval-mode plan \
  -p 'Inspect only. Do not modify files or run commands.' \
  --output-format json >out.json 2>err.log
```

## 官方來源網址

以下網址是本文整理時使用的主要官方來源。

### 1. CLI 指令總覽與命令列旗標

- `CLI commands`
  - https://geminicli.com/docs/reference/commands/

用途：

- `-p/--prompt`
- `--approval-mode`
- `--output-format`
- `--include-directories`
- `--worktree`
- `--resume`
- `--sandbox`

### 2. 認證與 headless mode

- `Authentication`
  - https://geminicli.com/docs/get-started/authentication/

用途：

- cached credentials 在 headless mode 的行為
- 沒有既有認證時應改用環境變數
- `Gemini API Key`
- `Vertex AI`

### 3. Plan Mode

- `Plan Mode`
  - https://geminicli.com/docs/cli/plan-mode/

用途：

- `--approval-mode plan`
- plan 模式的工具限制
- 非互動模式下從 plan 轉 implementation 的自動行為

### 4. Sandboxing

- `Sandboxing in the Gemini CLI`
  - https://geminicli.com/docs/cli/sandbox/

用途：

- `-s/--sandbox`
- `GEMINI_SANDBOX`
- sandbox expansion
- 常見沙箱後端與疑難排解

### 5. Policy Engine

- `Policy engine`
  - https://geminicli.com/docs/reference/policy-engine/

用途：

- 用規則控制工具允許 / 拒絕 / 詢問
- `interactive = false` 的 headless policy
- `commandPrefix`
- `allowRedirection`
- mode-specific rules

### 6. 專案上下文與 `GEMINI.md`

- `Provide context with GEMINI.md files`
  - https://geminicli.com/docs/cli/gemini-md/

用途：

- `GEMINI.md` 階層式上下文
- `context.fileName`
- 把 `AGENTS.md` 加進上下文檔名清單

### 7. System prompt override

- `System Prompt Override (GEMINI_SYSTEM_MD)`
  - https://geminicli.com/docs/cli/system-prompt/

用途：

- 若要在單次或持續性工作流中覆蓋預設 system prompt，可從這裡查正式機制

### 8. 官方 GitHub repo

- `google-gemini/gemini-cli`
  - https://github.com/google-gemini/gemini-cli

用途：

- 安裝來源
- release / issue / 實作參考
- 補充 README 與 schema 路徑

### 9. Gemini thinking / reasoning 官方說明

- `Thinking`
  - https://ai.google.dev/gemini-api/docs/thinking
- `Thinking on Vertex AI`
  - https://cloud.google.com/vertex-ai/generative-ai/docs/thinking

用途：

- `Gemini 3.1 Pro` 支援的 `thinking_level`
- 預設 thinking level
- 哪些模型能不能關閉 thinking
- `thinking_level` 與 `thinking_budget` 的差異

### 10. Gemini OpenAI compatibility

- `OpenAI compatibility`
  - https://ai.google.dev/gemini-api/docs/openai

用途：

- `reasoning_effort` 與 Gemini `thinking_level` / `thinking_budget` 的對應
- 若未指定 `reasoning_effort` 時會使用模型預設 level / budget
- `reasoning_effort` 與 Gemini thinking 參數不能同時使用

## 註記

本文以官方文件加本機實測為準。

若之後 `Gemini CLI` 升版，建議優先重查：

- `CLI commands`
- `Authentication`
- `Plan Mode`
- `Policy engine`

因為這幾頁最直接影響單次非互動呼叫的可用性與安全模型。
