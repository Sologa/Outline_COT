# Superpowers Skills 中文說明

## 文件目的

這份文件整理 `obra/superpowers` 在本機安裝後的所有 skill，說明它們各自負責什麼、何時該用，以及它們強調的工作方式。

本文是基於目前已安裝到 `~/.codex/skills/` 的版本整理，不是單純轉述遠端 README。

## 安裝結果

已安裝的 Superpowers skills 共 14 個：

1. `brainstorming`
2. `dispatching-parallel-agents`
3. `executing-plans`
4. `finishing-a-development-branch`
5. `receiving-code-review`
6. `requesting-code-review`
7. `subagent-driven-development`
8. `systematic-debugging`
9. `test-driven-development`
10. `using-git-worktrees`
11. `using-superpowers`
12. `verification-before-completion`
13. `writing-plans`
14. `writing-skills`

## 整體定位

Superpowers 不是功能型工具包，而是一組「工程流程 skill」。它主要不是幫你呼叫某個 API，而是要求 agent 在設計、規劃、實作、除錯、驗證、code review、收尾等不同階段遵守比較嚴格的流程。

可以把它理解成一套偏強制的工程作業法：

- 先設計，再規劃，再實作
- 先找 root cause，再修 bug
- 先寫 failing test，再寫實作
- 先驗證，再宣稱完成
- 大任務要拆，獨立任務要平行化

## 分類總覽

### 1. 流程入口與總控

- `using-superpowers`

### 2. 設計與規劃

- `brainstorming`
- `writing-plans`
- `executing-plans`
- `subagent-driven-development`

### 3. 工程紀律

- `systematic-debugging`
- `test-driven-development`
- `verification-before-completion`
- `using-git-worktrees`

### 4. 協作與收尾

- `dispatching-parallel-agents`
- `requesting-code-review`
- `receiving-code-review`
- `finishing-a-development-branch`

### 5. Skill 自身開發

- `writing-skills`

## 各 skill 功用說明

### `using-superpowers`

- 功用：這是整套 Superpowers 的入口 skill，用來規定「任何任務開始前，都要先檢查是否有相關 skill 應該被使用」。
- 適用時機：理論上是每次對話一開始都要先套用，用來決定後續該走哪個 skill。
- 核心重點：它強調 skill 的優先順序、使用規則、平台對應方式，以及「只要有 1% 機率適用，就要先檢查 skill」。
- 實務意義：它像是一個總開關，會把 agent 從「直接做事」改成「先選對流程再做事」。

### `brainstorming`

- 功用：把模糊需求整理成明確設計，要求先理解需求、釐清限制、比較方案，再寫設計文件。
- 適用時機：任何創作型或需求成形中的任務，例如新增功能、修改行為、設計元件、規劃新模組。
- 核心重點：禁止在設計核准前直接進入實作；要先探索現有專案、逐題問問題、提出 2 到 3 個方案、取得使用者同意，再把 spec 寫進 `docs/superpowers/specs/`。
- 實務意義：它不是拿來寫 code，而是拿來避免「需求沒講清楚就直接開工」。

### `writing-plans`

- 功用：把已經確認過的 spec 或需求，轉成可執行的 implementation plan。
- 適用時機：當設計已經確認，但還沒開始改 code，尤其是多步驟、跨多檔案、需要分任務執行的工作。
- 核心重點：要求把檔案路徑、測試方式、每一步的實作內容、命令與預期結果都寫清楚，不能留 `TODO`、`TBD` 或模糊描述。
- 實務意義：它要產出的是「別的工程師或 agent 拿到就能直接照做」的執行計畫，而不是高層次摘要。

### `executing-plans`

- 功用：依照既有 plan 逐步執行工作，強調先讀 plan、先質疑 plan、再逐步實作與驗證。
- 適用時機：已經有 written plan，而且希望由同一個 agent 依序完成。
- 核心重點：先 review 計畫本身是否合理；執行時每個 task 都要標記進度、跑驗證；全部完成後必須轉入 `finishing-a-development-branch` 做收尾。
- 實務意義：它適合順序性比較高、耦合度較高、不適合大規模平行分拆的實作工作。

### `subagent-driven-development`

- 功用：用子代理人逐 task 執行 implementation plan，並在每個 task 後做雙層 review。
- 適用時機：手上已經有 plan，而且各 task 大致獨立，適合在同一個 session 內交給不同 subagent 分工。
- 核心重點：每個 task 會經過 implementer、spec reviewer、code quality reviewer 等角色；每做完一個 task 就先看是否符合 spec，再檢查 code quality，最後再進下一個 task。
- 實務意義：它是 `executing-plans` 的高配版，前提是平台支援 subagents，而且任務切分得夠清楚。

### `dispatching-parallel-agents`

- 功用：把互相獨立的問題切開，交給多個 agent 平行處理。
- 適用時機：同時有 2 個以上獨立問題，例如多個不相關的 failing tests、不同子系統各自出錯、不同類型的 bug 可以分頭查。
- 核心重點：每個 agent 的任務必須非常聚焦，而且彼此不能共享狀態或互相踩檔案；prompt 要明確寫出範圍、限制與回傳格式。
- 實務意義：它處理的是「如何正確平行化」，避免把一個模糊的大任務丟給多個 agent 後全部互相干擾。

### `systematic-debugging`

- 功用：提供嚴格的除錯流程，要求先找 root cause，再談修法。
- 適用時機：任何 bug、test failure、build failure、整合異常、效能問題或「行為不符合預期」的情況。
- 核心重點：它把除錯切成明確 phase，先讀錯誤訊息、穩定重現、檢查最近變更、縮小問題範圍，再提出修法；禁止未查明原因就亂 patch。
- 實務意義：它的目的是阻止 agent 採取「先改看看」的賭博式修 bug 方式。

### `test-driven-development`

- 功用：要求所有功能或 bugfix 都遵守 TDD，先寫測試、看它失敗，再寫最小實作。
- 適用時機：新增功能、修 bug、行為調整、重構。
- 核心重點：沒有 failing test 就不能寫 production code；如果先寫了 code，skill 的態度是刪掉重來；整個流程必須走 `RED -> GREEN -> REFACTOR`。
- 實務意義：它不是只是鼓勵多寫測試，而是把測試放到實作之前，拿來約束設計與防止假修復。

### `verification-before-completion`

- 功用：在宣稱「已修好」「已完成」「可以 merge」之前，強制先跑驗證命令。
- 適用時機：任何要宣稱成功、完成、passing、ready for PR、ready to commit 的時候。
- 核心重點：不允許用「應該可以」「看起來沒問題」「理論上會過」這種話；一定要先跑完整驗證命令、讀輸出、確認 exit code 和失敗數，再做陳述。
- 實務意義：它是避免 agent 在沒有證據的情況下過早報喜，屬於防誇大、防自我感覺良好類的 skill。

### `using-git-worktrees`

- 功用：為新功能或實作計畫建立隔離工作區，避免污染目前 workspace。
- 適用時機：開始做一個新 feature、準備照 plan 實作、或需要在多個 branch 間平行工作時。
- 核心重點：它規定 worktree 目錄選擇順序、ignore 驗證、建立步驟、專案初始化與基線測試；不是單純 `git worktree add` 而已。
- 實務意義：它把「從乾淨隔離環境開始工作」變成流程的一部分，減少在主 workspace 上亂改的風險。

### `requesting-code-review`

- 功用：在重要實作節點主動要求 code review，提早抓出問題。
- 適用時機：完成 major feature 後、準備 merge 前、subagent-driven development 的每個 task 後，或修完複雜 bug 後。
- 核心重點：它要求用明確的 base/head SHA、需求摘要與變更說明來發出 review 請求，並且按嚴重度處理回饋。
- 實務意義：它的重點是「review 要早、要常、要基於準確上下文」，而不是等到全部做完才一次送審。

### `receiving-code-review`

- 功用：規範收到 review feedback 時該怎麼處理，避免盲目接受或情緒性回應。
- 適用時機：收到 reviewer 建議、GitHub review comment、PR feedback、同事技術意見時。
- 核心重點：先完整理解，再對照 codebase 驗證，再決定接受、澄清或技術性反駁；禁止空泛附和，也禁止沒搞懂就開始改。
- 實務意義：它把 code review 視為技術評估流程，不是社交表演；適合處理那些可能有誤、描述不清或需要脈絡判斷的 review。

### `finishing-a-development-branch`

- 功用：在功能開發完成後，指導最後的收尾與整合流程。
- 適用時機：所有實作和測試都完成，準備決定是 merge、開 PR、保留 branch，還是直接丟棄工作時。
- 核心重點：先確認測試真的通過，再判斷 base branch，然後只提供四個結構化選項：本地 merge、推送並開 PR、保持現狀、丟棄工作；若需要清理 worktree，也在這一步完成。
- 實務意義：它讓開發結尾不再混亂，避免做完功能後不知道該如何有紀律地收尾。

### `writing-skills`

- 功用：用 TDD 的方式設計、驗證與改進 skill 本身。
- 適用時機：新增 skill、修改既有 skill、檢查 skill 是否真的能讓 agent 改變行為時。
- 核心重點：先設計 pressure scenario，觀察沒有 skill 時 agent 如何失敗，再寫 skill、重新驗證、補漏洞；也規範 `SKILL.md` 的 frontmatter、結構、描述寫法與檔案拆分方式。
- 實務意義：它是用來寫「流程文件」的流程文件，本質上是把 TDD 套用到 skill engineering。

## 建議怎麼理解這套 skill

如果只想快速抓重點，可以用下面這種方式記：

- `using-superpowers`：先決定要走哪條流程
- `brainstorming`：先設計
- `writing-plans`：把設計寫成可執行計畫
- `executing-plans` / `subagent-driven-development`：照計畫做
- `systematic-debugging`：遇到 bug 時先查原因
- `test-driven-development`：先測試再實作
- `verification-before-completion`：先驗證再說完成
- `using-git-worktrees`：先隔離 workspace
- `requesting-code-review` / `receiving-code-review`：review 要有來有回而且有技術判斷
- `finishing-a-development-branch`：最後收尾
- `dispatching-parallel-agents`：獨立問題平行拆
- `writing-skills`：用來寫新的 skill

## 實務上的限制

這些 skill 很多都帶有很強的流程假設，包含：

- 偏好先有 spec、再有 plan、再實作
- 偏好 TDD
- 偏好使用 worktree 隔離
- 偏好頻繁 review 與明確驗證
- 某些 skill 依賴 subagent 能力才會真正發揮完整效果

所以它們比較像「強流程工程風格」，不是每種任務都會覺得輕量。但如果你想讓 agent 做事時更像嚴格的工程師，而不是直接憑直覺動手，這套 skill 的價值就很高。

## 本機對應路徑

目前這些 skills 已安裝於：

- `~/.codex/skills/brainstorming`
- `~/.codex/skills/dispatching-parallel-agents`
- `~/.codex/skills/executing-plans`
- `~/.codex/skills/finishing-a-development-branch`
- `~/.codex/skills/receiving-code-review`
- `~/.codex/skills/requesting-code-review`
- `~/.codex/skills/subagent-driven-development`
- `~/.codex/skills/systematic-debugging`
- `~/.codex/skills/test-driven-development`
- `~/.codex/skills/using-git-worktrees`
- `~/.codex/skills/using-superpowers`
- `~/.codex/skills/verification-before-completion`
- `~/.codex/skills/writing-plans`
- `~/.codex/skills/writing-skills`

## 補充

安裝完成後，需要重啟 Codex，新的 skills 才會在新 session 中被完整發現與使用。
