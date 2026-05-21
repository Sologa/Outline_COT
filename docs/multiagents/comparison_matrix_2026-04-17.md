# Multi-Agent 比較矩陣（2026-04-17）

本文件把目前研究到的幾種 execution mode 與 concrete system 放進同一張比較表，方便後續討論時不把不同層級的東西混在一起。

## 1. 抽象工作模式矩陣

這一張表先不管是哪個產品，純粹比較幾種工作模式。

| 模式 | 隔離單位 | 誰保留最終回答所有權 | 最適合的工作 | 主要代價 | 本 repo 的建議 |
| --- | --- | --- | --- | --- | --- |
| Direct execution | 當前 agent context | 主代理 | 短、小、緊耦合、critical-path | 主 context 污染快 | 小任務優先 |
| Native subagent | 獨立 LLM context | 通常仍是主代理 | bounded sidecar work、平行掃描、局部 review | token 成本、協調成本 | 研究側車工作優先 |
| Manual `codex exec` | process / job / artifact boundary | 主代理或操作者 | 長時間、批次、artifact-heavy、可重跑分析 | orchestration 負擔高 | 重研究優先 |
| Agent team | 獨立 session / teammate | team lead 或共享協調層 | 需要 peer-to-peer 討論與共享 task list 的複雜工作 | token 成本更高、管理更複雜 | 本 repo 非主要模式 |

## 2. 官方產品表面矩陣

| 系統 / surface | context isolation | worker 間可否直接互通 | 啟用狀態 | delegation 深度 | 最接近哪種抽象模式 |
| --- | --- | --- | --- | --- | --- |
| Codex subagents | 有 | 目前主要透過主協調層 | stable，預設開啟 | 可由主代理管理多個 subagent | Native subagent |
| Claude Code subagents | 有 | 否，只回主代理 | 正式文件化 | subagent 不能再 spawn subagent | Native subagent |
| Claude Code Agent Teams | 有 | 可以 | experimental，預設關閉 | 多 session 協作 | Agent team |
| Anthropic Managed multi-agent sessions | 有（session thread） | 由 coordinator 管理 | Research Preview | 只支援 one level | Native subagent 與 team 之間的 API orchestration |

## 3. `claw-code` 對照矩陣

| `claw-code` 機制 | 實際上像什麼 | 是否有獨立 LLM context | 是否有 artifact | 成熟度判斷 |
| --- | --- | --- | --- | --- |
| `Agent` tool | background LLM worker | 有 | 有：manifest + output | 本 repo 中最成熟的 agent path |
| `TaskRegistry` | task metadata registry | 否 | 主要在記憶體 | 中繼狀態，不是 worker fleet |
| `TeamRegistry` | team grouping metadata | 否 | 主要在記憶體 | orchestration bookkeeping |
| `CronRegistry` | scheduled metadata registry | 否 | 主要在記憶體 | 尚未成為真正 scheduler |
| bash `run_in_background` | OS child process | 否 | 幾乎無 agent artifact | 只是 shell backgrounding |

## 4. 重要維度逐項比較

### 4.1 Context isolation

- Direct execution 幾乎沒有隔離，所有探索與結果都進入主 context。
- Native subagent 的核心價值在 context isolation。
- 手動 `codex exec` 是另一種隔離：不是 LLM context 隔離，而是 process / artifact 隔離。
- Claude Agent Teams 再往上一層，是多 session 隔離加上 teammate 間協調。

### 4.2 Coordination overhead

- Direct execution 幾乎沒有協調成本。
- Native subagent 有中等協調成本：要定義邊界、等結果、整合結論。
- Manual `codex exec` 的協調成本更偏 operator 側：命令、輸出路徑、重跑策略都要自己顧。
- Agent Teams 成本最高，因為除了 delegation，還有 shared task list、message routing、清理與關閉。

### 4.3 Provenance and auditability

- Direct execution 如果沒有刻意整理，很容易只剩聊天上下文。
- Native subagent 的 provenance 強度取決於平台與使用方式。
- Manual `codex exec` 天然適合留下 log、artifact、rerun command。
- `claw-code` 的 `Agent` path 特別值得注意，因為它用 manifest + output file 把 subagent state 落盤，這是相對強的可審計設計。

### 4.4 適合的任務形狀

**Direct execution**

- 小修正
- 短查證
- 緊耦合的同檔修改
- 主路徑上的立即決策

**Native subagent**

- repo 掃描
- multi-file comprehension
- 局部 review
- bounded provenance checks
- 非阻塞式 sidecar verification

**Manual `codex exec`**

- 跨 paper / 跨資料夾的大量讀取
- 批量報表
- 長時間 script
- 要保存輸出與重跑能力的工作

**Agent Teams**

- 需要同儕式討論
- 需要 worker 彼此互相 challenge
- 需要 shared task list
- 工作面向彼此獨立，但最終需 lead synthesis

## 5. 對本 repo 的最終映射

本 repo 的工作特性是：

- prompt provenance
- repo comprehension
- results-first evaluation
- cross-paper comparison
- heavy read-only analysis

因此最適合的對應是：

| 本 repo 任務 | 推薦模式 |
| --- | --- |
| 單點 prompt / path / CLI 規則確認 | Direct execution |
| 多檔案 provenance 對照 | Native subagent |
| 跨 paper 批量比對、重報表輸出 | Manual `codex exec` |
| 需要同儕式辯論與自治協作的情境 | 通常不需要 Agent Team；除非未來工作型態改變 |

## 6. 本文件的工作結論

對本 repo 來說，最重要的不是追求「哪個產品有最酷的 team UI」，而是把 execution mode 選對。

可以濃縮成四句話：

1. 小而急的工作，主代理直接做。
2. bounded sidecar work，優先原生 subagent。
3. 長時間、批次、artifact-heavy 的工作，優先手動 `codex exec`。
4. 不論用哪種模式，最終的 source verification 與 provenance 整理都不能外包掉。
