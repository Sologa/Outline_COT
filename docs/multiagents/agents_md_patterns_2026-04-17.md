# 公開 `AGENTS.md` 樣本分析（2026-04-17）

本文件研究的是一個比較窄但實際的問題：

> 公開世界裡，別人是否會在 `AGENTS.md` 直接寫 multi-agent / subagent / delegation 規則？

短答案是：

- **會**
- 但 **不是普遍預設**

下面把這件事拆開來看。

## 1. 為什麼 `AGENTS.md` 值得研究

在很多 agentic coding workflow 裡，`AGENTS.md` 已經逐漸變成：

- repo-level instructions
- tool preference
- coding / testing / git 規則
- agent routing surface

如果有人真的把 subagent / delegation 寫進 `AGENTS.md`，那表示：

- multi-agent 不只是 runtime feature
- 它已經開始變成 repo policy surface

這對本 repo 很重要，因為我們正在把「何時 direct execution、何時 subagent、何時 `codex exec`」寫進 repo-level rule。

## 2. 樣本來源與方法限制

本次樣本主要來自：

- 公開 gist
- 公開 template
- 與 Codex subagent 相關的 helper repo / README

這不是嚴格統計樣本，因此不能拿來做普遍性推論。它的價值在於：

- 找到可觀察到的公開做法
- 分類其風格
- 判斷「這件事到底有沒有人在做」

## 3. 我看到的幾種類型

### 3.1 Generic onboarding 型

這是最常見的 `AGENTS.md` 形狀。典型內容包括：

- 專案介紹
- build / test / lint 指令
- code style
- do / don't
- git 規則
- 回覆風格

代表樣本：

- `davidondrej` default `AGENTS.md` template
  <https://gist.github.com/davidondrej/3c590b1db96443ccd66220c5d88620b9>

這類文件的特點是：

- 把 agent 當成「repo contributor」
- 不特別把 multi-agent orchestration 視為 repo policy 的一部分

### 3.2 Policy-first orchestration 型

這類文件不一定用一堆角色名稱，但會明確規定：

- 何時該用 subagent
- 何時該做 research offload
- 何時該保持主 context 乾淨

代表樣本：

- `cesarferreira/AGENTS.md` gist
  <https://gist.github.com/cesarferreira/7e22bcd73b8a7f3641ace6f4135ba888>

這類做法的重點是：

- 把 subagent 視為 context management tool
- 把 delegation 寫成工作規則，而不是偶發技巧

這和本 repo 目前的方向最接近。

### 3.3 Role-first orchestration 型

這類文件傾向把整個工作流寫成多個命名角色，例如：

- planner
- executor
- reviewer
- critic

代表樣本：

- `pagelab/AGENTS.MD` gist
  <https://gist.github.com/pagelab/2abdd6459ccb392e8ac7ee7c87436a6f>

這類做法的特點是：

- 人比較容易理解角色分工
- 但文件很容易從 repo policy 變成一套完整操作哲學
- 對一般 repo 來說，通常偏重

如果底層 runtime 沒有很強的 agent support，role-first 文件也可能流於敘事。

### 3.4 Tool-routing / helper-routing 型

這類文件不一定直接講 subagent，但會明確指定某些工作應該交給外部 helper / MCP / search agent。

代表樣本：

- `cau1k/AGENTS.md` gist
  <https://gist.github.com/cau1k/18eee80e5bfaf34ed6e29f7b38a1479c>

這類文件的特徵是：

- 把 `AGENTS.md` 當成 router
- 指定某種任務優先交給哪個 helper

它不完全等於 native subagent 寫法，但在實務上非常接近 agent-routing。

### 3.5 File-based agent registry / delegate syntax 型

這類做法更進一步，直接把：

- agent persona
- profile
- approval mode
- sandbox mode
- delegate syntax

這些東西結合起來，並明言可把 delegate 語句寫進 repo 的 `AGENTS.md`。

代表樣本：

- `leonardsellem/codex-subagents-mcp`
  <https://github.com/leonardsellem/codex-subagents-mcp>

這類做法很有代表性，因為它說明了：

- `AGENTS.md` 不只是 instruction file
- 在某些工作流中，它已經被當成 orchestration policy surface

## 4. 這些樣本共同透露什麼

### 4.1 透露了一個趨勢

`AGENTS.md` 正在從「純 onboarding 文件」往下面幾種用途擴張：

- tool preference
- routing surface
- delegation policy
- repo-specific operating manual

### 4.2 但還沒有形成通用規範

本次快速搜尋中，直接用 GitHub code search 找：

- `path:AGENTS.md subagent`
- `path:AGENTS.md multi-agent`

沒有立刻看到大量 repo-root 樣本。

這表示：

- 這個模式是真實存在的
- 但還沒有普及到可以視為一般預設

### 4.3 為什麼這件事重要

如果某個 pattern 已經在公開世界裡存在，即使還不普遍，它也具有兩種價值：

1. **正當性**
   代表這不是只有單一使用者在玩的小技巧。

2. **可設計性**
   代表我們可以開始認真討論：什麼寫法是好的，什麼寫法只是把 prompt engineering 塞進 repo 規則。

## 5. 對本 repo 最有用的設計方向

根據本次樣本分析，本 repo 不適合採用太重的 role-first 設計，原因是：

- repo 的主任務是研究與比較，不是長時間軟體工廠式協作
- 我們需要的是 execution mode policy，不是角色戲劇化
- 我們更重視 provenance、artifact、results-first workflow

因此，本 repo 最適合的是：

- **policy-first**
- **execution-mode aware**
- **delegation with verification**

這正是 [AGENTS.md](../../AGENTS.md) Section 10 現在的方向。

## 6. 實際可重用的寫法原則

如果未來要在其他 repo 寫多代理版本的 `AGENTS.md`，目前最可重用的原則是：

### 6.1 不要先寫角色，先寫決策規則

先定義：

- 哪些任務 direct execution
- 哪些任務 native subagent
- 哪些任務 manual `codex exec`

這比先定義 `Planner` / `Reviewer` / `Executor` 更穩。

### 6.2 委派規則要和驗證規則綁在一起

只寫「什麼時候 delegate」是不夠的。

還要同時寫：

- delegated output 不是 final claim
- 主代理要做 source verification
- 推論與已確認事實要分開報告

### 6.3 `AGENTS.md` 不應假裝創造底層能力

如果底層沒有 native subagent 工具，`AGENTS.md` 寫了也不會憑空產生 orchestration system。

所以好的寫法應該是：

- 承認底層能力的存在或不存在
- 在此基礎上設計 policy

而不是寫成一份看起來很酷、但實際跑不起來的指揮手冊。

## 7. 本文件的工作結論

截至本次研究，可以保守地寫成：

1. 公開世界裡，確實有人把 delegation / subagent / orchestration 規則直接寫進 `AGENTS.md`。
2. 這類寫法比較常見於 gist、template、helper repo，而不是一般 repo 的通用預設。
3. 對本 repo 來說，最值得吸收的是 **policy-first** 寫法，而不是過重的 role-first 設計。

這也是為什麼本 repo 最終選擇在 [AGENTS.md](../../AGENTS.md) 裡寫「Execution and Orchestration Policy」，而不是先發明一組命名角色。
