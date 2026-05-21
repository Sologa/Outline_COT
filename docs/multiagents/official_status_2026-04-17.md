# Multi-Agent 官方現況（2026-04-17）

本文件整理 2026-04-17 當日核對的官方文件，目的不是做產品宣傳，而是釐清：

- 各家目前到底有哪些 multi-agent surface
- 它們彼此差在哪裡
- 哪些是正式穩定能力，哪些仍屬 experimental / research preview
- 這些差異對本 repo 的工作流意味著什麼

## 1. 研究範圍與方法

本文件只使用官方文件，不把第三方 repo、社群傳聞、或某個 CLI 的表面命令列當成官方真相。

使用來源：

- Codex subagents
  <https://developers.openai.com/codex/subagents>
- Codex config reference
  <https://developers.openai.com/codex/config-reference>
- OpenAI agents orchestration
  <https://developers.openai.com/api/docs/guides/agents/orchestration>
- Claude Code subagents
  <https://code.claude.com/docs/en/sub-agents>
- Claude Code Agent Teams
  <https://code.claude.com/docs/en/agent-teams>
- Anthropic Managed Agents multi-agent sessions
  <https://platform.claude.com/docs/en/managed-agents/multi-agent>

## 1.1 快速證據點

如果之後只想快速確認本次最重要的官方訊息，先看這一節。

### Codex

- `features.multi_agent` 在 config reference 中被列為 stable，且預設開啟。
- multi-agent collaboration tools 明列為：
  - `spawn_agent`
  - `send_input`
  - `resume_agent`
  - `wait_agent`
  - `close_agent`
- Codex subagents 文件明言：
  - current releases enable subagent workflows by default
  - subagent activity 目前可在 app 與 CLI 中看到
  - 只有在使用者明確要求時才會啟動 subagent
- OpenAI orchestration 文件明言：
  - start with one agent whenever you can
  - 只有當 contract 明顯改變時才值得新增 specialist

### Claude

- Claude Code subagents 文件明言：
  - subagent 有自己的 context window
  - 可有自訂 prompt / tools / permissions
  - subagents cannot spawn other subagents
- Claude Code Agent Teams 文件明言：
  - experimental
  - disabled by default
  - 使用 shared task list 與 teammate 直接互通
- Anthropic Managed Agents multi-agent 文件明言：
  - Research Preview
  - same container / filesystem
  - each agent has its own session thread
  - tools and context are not shared
  - only one level of delegation is supported

## 2. Codex：官方如何描述 multi-agent

### 2.1 Codex 的能力表面

Codex 官方目前已經有獨立的 `Subagents` 文件與 config reference。

根據官方文件，目前可確認：

- Codex 可以在平行路徑上啟動 specialized agents，並在主回覆前收斂結果。
- Subagent activity 已經在 Codex app 和 CLI 中可見。
- `features.multi_agent` 在 config reference 中被列為 stable，且預設開啟。
- Config reference 明確列出 multi-agent collaboration tools：
  - `spawn_agent`
  - `send_input`
  - `resume_agent`
  - `wait_agent`
  - `close_agent`

這代表：

- Codex 的 multi-agent 不是社群 hack，也不是單純 prompt convention。
- 它已經是官方文件化、工具化、且在設定層可見的產品能力。

補充一點：

- Codex subagents 文件還明講 visibility 目前在 app 與 CLI 內可見，IDE Extension 的可見性仍在補齊中。
- 這說明 OpenAI 對 subagent 的產品化不只停在 runtime / API 層，也已經進入主要互動表面。

### 2.2 Codex 官方對「什麼時候該用 subagent」的態度

Codex subagents 文件強調：

- 只有當使用者明確要求時，Codex 才會啟動 subagent workflow。
- Subagents 會增加 token 消耗，因為每個 agent 都會進行自己的 model / tool work。
- 典型適用場景是 highly parallel 的複雜任務，例如 codebase exploration、multi-step feature plan 的不同子項。

這透露兩個重要設計態度：

1. **subagents 是需要顯式授權的額外協調機制**
   它不是每個任務都該自動開的默認模式。

2. **成本與協調負擔是真實存在的**
   官方並沒有把 multi-agent 描述成無成本的最佳預設。

### 2.3 OpenAI 官方更上層的 orchestration 觀點

OpenAI 的 agents orchestration 文件不是在談 Codex 產品操作，而是在談一般 agent system 設計。

它給出兩種主要模式：

- `handoffs`
  specialist 取得下一段對話的所有權
- `agents as tools`
  manager 保持對最終回答的所有權，specialist 僅作為 bounded capability 被呼叫

官方同時強調：

- **Start with one agent whenever you can**
- 只有當 specialist 能明確改善 capability isolation、policy isolation、prompt clarity、或 trace legibility 時，才值得新增 agent

這一點非常重要，因為它直接支持本 repo 後來採用的 policy：

- 不要為了「看起來很 multi-agent」而濫開 agent
- 只有當工作邊界真的變了，才值得切出 specialist

另一個很實際的觀點是：

- `handoffs` 適合 specialist 接手下一段對話所有權
- `agents as tools` 適合 manager 保持最終回答所有權

本 repo 的大多數研究任務更接近後者，也就是：

- 主代理保留最終回覆
- specialist 只處理 bounded capability

### 2.4 對 Codex 的工作結論

截至 2026-04-17，可用一句話總結 Codex：

> Codex 已經有正式、可配置、且預設開啟的 multi-agent capability layer，但官方仍然把它描述成需要審慎使用的協調工具，而不是所有任務的默認答案。

這也是為什麼：

- 「Codex 有沒有對應 Claude multi-agent 的能力？」答案是有。
- 「是不是從此就不需要手動 `codex exec` 發包？」答案是否定的。

## 3. Claude：官方 multi-agent surface 其實不是一層

### 3.1 Claude Code subagents

Claude Code 的 subagents 文件描述的是：

- subagent 有自己的 context window
- 可以有自己的 system prompt
- 可以限制自己的 tools
- 可以有自己的 permissions
- 可以針對特定任務重複使用或自訂

官方文件還明確給出幾個關鍵限制：

- subagents 不會無限遞迴委派
- **subagents cannot spawn other subagents**
- 如果需要 nested delegation，應改從主對話鏈接，或改用 Skills

這意味著：

- Claude Code subagents 是「主 session 內的隔離 worker」
- 它不是 fully peer-to-peer 的 team 系統

官方文件也強調 context savings：
subagent 會在自己的窗口內做搜尋、讀檔、研究，再把摘要帶回主對話。

另外，Claude 文件也透露一個運行語義：

- 每次 subagent invocation 預設都是 fresh context
- 若要 resume 舊 subagent，需要保有對應 agent 的延續通道

這支持一個重要判斷：Claude 的 subagent 不是輕量角色切換，而是實際的子執行單元。

### 3.2 Claude Code Agent Teams

`Agent Teams` 是另一個層級的產品 surface，不應和 subagents 混為一談。

根據官方文件：

- Agent Teams 是 experimental
- disabled by default
- 需要顯式啟用 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`
- 一個 team 有：
  - team lead
  - 多個 teammates
  - shared task list
- teammates 彼此可以直接溝通，而不必所有訊息都經過 lead

官方還提供了和 subagents 的直接對照：

- subagents：結果只回主代理
- agent teams：teammates 可以互相發消息
- subagents：由主代理統一協調
- agent teams：有 shared task list 與較強的自我協調
- subagents：token cost 較低
- agent teams：token cost 更高

官方也明講：

- Agent Teams 不適合 sequential tasks
- 不適合同一個檔案上的緊密修改
- 不適合相依性很高的工作

也就是說，Claude 官方自己並沒有把 Agent Teams 描述成萬能模式；它其實更偏向高成本、高自治度的特定工具。

官方還明講 Agent Teams 在 session resumption、task coordination、shutdown behavior 上仍有已知限制。這代表它即使在官方產品層，也還不是完全成熟的無摩擦模式。

### 3.3 Anthropic Managed Agents multi-agent sessions

Anthropic 平台側另有一套 `Multiagent sessions` 文件。這一層不屬於 Claude Code 終端產品，而是 Managed Agents API 的 advanced orchestration surface。

目前官方文件表示：

- 這是 Research Preview
- 需要特殊 beta header
- coordinator 與被調用 agent 可以在同一個 session 內協作
- 所有 agent 共享同一個 container / filesystem
- 但每個 agent 在自己的 session thread 內運作，因此 conversation history 是隔離的
- tools and context are not shared
- 目前只支援 **one level of delegation**

這一層與 Claude Code Agent Teams 的差別在於：

- 一個是面向 Claude Code 終端使用者的 session/product surface
- 一個是面向 API / managed runtime 的 orchestration surface

所以如果後續有人說「Claude 有 multi-agent」，一定要進一步問：

- 他指的是 Claude Code subagents？
- Claude Code Agent Teams？
- 還是 Managed Agents API 的 multi-agent？

值得額外注意的是：

- Anthropic managed multi-agent 文件採用的核心抽象是 `coordinator + callable agents`
- delegation 深度目前受限為 one level

這和很多人直覺想像的「agent 可以一直再開 agent」不一樣；它更接近受控的 coordinator model。

## 4. Codex 與 Claude 的官方比較

### 4.1 相似處

- 兩者都承認 multi-agent 的主要價值在於 **context isolation** 與 **specialization**。
- 兩者都沒有把 multi-agent 描述成所有任務的默認最優路徑。
- 兩者都把工具、權限、prompt、角色說明視為 multi-agent 成功與否的重要邊界條件。

### 4.2 差異處

Codex 官方文件目前更偏：

- subagents
- orchestration patterns
- manager / specialist 的 ownership 分工

Claude 官方文件目前更清楚區分兩種產品表面：

- subagents
- Agent Teams

也就是說：

- Codex 官方較像是在提供 orchestration primitives
- Claude Code 官方則明確暴露了更高階的 `Agent Teams` 產品形態

### 4.3 對本 repo 的直接影響

本 repo 的工作重點是：

- repo comprehension
- prompt provenance
- cross-paper comparison
- heavy read-only analysis

因此本 repo 更需要的是：

- context isolation
- evidence collection
- bounded sidecar workers
- batch artifact generation

這使得本 repo 的最適合工作流是：

- **Direct execution**：短、小、critical-path
- **Native subagent**：bounded sidecar scanning / review / provenance checks
- **Manual `codex exec`**：重批次、重 artifact、重可重跑的研究流程

而不是直接追求 `Agent Teams` 式的高自治 team 模式。

## 5. 本文件的工作結論

截至 2026-04-17，官方文件層的結論可以寫成：

1. **Codex 有正式 multi-agent 能力。**
2. **Claude 也有 multi-agent，但要拆層理解。**
3. **Codex 與 Claude 都不支持「所有任務都該多代理化」這種結論。**
4. **對本 repo 來說，最重要的不是追求 team 表面，而是把 execution mode 選對。**

這也是 [AGENTS.md](../../AGENTS.md) Section 10 為什麼採 policy-first，而不是 role-first。

## 6. 後續更新時優先檢查的點

若之後要刷新這份文件，最值得優先檢查的是：

1. Codex 是否開始暴露更高階、接近 `Agent Teams` 的產品表面
2. Claude Code Agent Teams 是否從 experimental 轉為更穩定狀態
3. Anthropic Managed multi-agent 是否放寬 one-level delegation 限制
4. Codex / Claude 是否更改 subagent 是否需要 explicit ask 的策略
