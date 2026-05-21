# Multi-Agent 研究索引

最後核對日期：2026-04-17

這個目錄記錄目前在本 repo 內完成的 multi-agent 研究，重點是把三種不同層級的資訊拆開：

1. **官方產品現況**
   Codex、Claude Code、Anthropic Managed Agents 的正式文件與產品表面。

2. **第三方實作觀察**
   以 `Sologa/claw-code` 為研究樣本，觀察一個公開 agent harness 如何落地 subagent、task/team/cron、background shell 等機制。

3. **公開 `AGENTS.md` 實務**
   觀察別人會不會把 delegation / subagent / orchestration 規則直接寫進 `AGENTS.md`。

這份 `README.md` 只作為總覽。詳細內容拆在子文檔中，方便之後單獨更新。

## 1. 文件地圖

- [official_status_2026-04-17.md](./official_status_2026-04-17.md)
  官方文件層的研究。整理 Codex、Claude Code、Anthropic Managed Agents 的 multi-agent 能力與限制。

- [claw_code_deep_dive_2026-04-17.md](./claw_code_deep_dive_2026-04-17.md)
  `Sologa/claw-code` 的實作拆解。包含 subagent 啟動流程、manifest/output 落盤、task/team/cron registry、background shell 與 subagent 的差異。

- [agents_md_patterns_2026-04-17.md](./agents_md_patterns_2026-04-17.md)
  公開 `AGENTS.md` 樣本的分類與分析。重點是 delegation 是否會直接寫進 repo-level agent rules。

- [comparison_matrix_2026-04-17.md](./comparison_matrix_2026-04-17.md)
  把 `direct execution`、`Codex subagents`、手動 `codex exec`、Claude 的 subagents / Agent Teams / Managed multi-agent、以及 `claw-code` 的對應做法放進同一張矩陣。

## 2. 目前最重要的工作結論

### 2.1 關於 Codex

- Codex 目前確實有原生 multi-agent / subagent 能力。
- 目前比較準確的理解方式是：`subagents + orchestration`，而不是把它直接等同於 Claude Code 的 `Agent Teams` 產品表面。
- 在實務上，Codex 的 native subagents 不會淘汰手動 `codex exec` 發包；兩者適用於不同形狀的工作。

### 2.2 關於 Claude

- 「Claude 有 multi-agent」這句話本身是正確的。
- 但後續分析必須拆成至少三層：
  - `Claude Code subagents`
  - `Claude Code Agent Teams`
  - `Managed Agents multi-agent sessions`
- 這三者的 context isolation、協調方式、通信能力、以及啟用條件都不相同。

### 2.3 關於 `claw-code`

- `claw-code` 不是 Anthropic 官方 Claude Code 原始碼。
- 它是很有研究價值的公開實作樣本，但不能把它的 runtime 細節直接當成官方產品真相。
- 在這個 repo 裡，真正像 LLM worker 的是 `Agent` 路徑；`task/team/cron` 則更接近 in-memory lifecycle / orchestration metadata。

### 2.4 關於 `AGENTS.md`

- 公開世界裡，確實有人把 subagent / delegation 規則直接寫進 `AGENTS.md`。
- 但這不是普遍預設。更常見的 `AGENTS.md` 仍然是一般 repo onboarding、coding style、test command、git 規則。

## 3. 本 repo 已採用的落地結論

這輪研究的結果已經反映到 [AGENTS.md](../../AGENTS.md) 的 Section 10：

- 用 **policy-first** 而不是 role-first 的方式描述 multi-agent 工作流。
- 明確區分：
  - `direct execution`
  - `native subagent delegation`
  - `manual codex exec dispatch`
- 把 delegation 後的 verification 與 provenance preservation 視為主代理不可移轉的責任。

目前本 repo 的簡短操作準則是：

- 短、小、在主路徑上的工作：主代理直接做。
- bounded sidecar work：優先原生 subagent。
- 長時間、批次、artifact-heavy 的分析：優先手動 `codex exec`。
- delegated output 永遠不是最終真相；重要結論仍需回到 source artifact 核對。

## 4. 推薦閱讀順序

如果之後要快速重新進入這個議題，建議順序如下：

1. 先看 [comparison_matrix_2026-04-17.md](./comparison_matrix_2026-04-17.md)
   先建立全局地圖。

2. 再看 [official_status_2026-04-17.md](./official_status_2026-04-17.md)
   分清楚官方產品表面到底有哪些層。

3. 如果要研究 implementation shape，再看 [claw_code_deep_dive_2026-04-17.md](./claw_code_deep_dive_2026-04-17.md)

4. 如果要研究規範寫法與 repo policy surface，再看 [agents_md_patterns_2026-04-17.md](./agents_md_patterns_2026-04-17.md)

## 5. 維護原則

這組文檔在下列情況需要更新：

- Codex 官方 multi-agent 文件更新
- Claude Code subagents / Agent Teams 文件更新
- Anthropic Managed Agents multi-agent 文件更新
- `Sologa/claw-code` 的實作顯著變化
- 本 repo 的 [AGENTS.md](../../AGENTS.md) 執行政策改動

如果只是補充例子或小修正，更新對應子文檔即可；如果核心判斷改變，請同步更新這份索引頁的「目前最重要的工作結論」。
