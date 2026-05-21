# Reference-Only Outline Induction IR Definition

## 中文定義

### 1. 這個東西是什麼

`reference-only outline induction IR` 是一種**可稽核的中介表示**，用來描述：

- 一篇 literature review 的**候選階層式 outline**
- 如何**只根據 review title 與 reference metadata**
- 在**不依賴 gold outline、COT、或既有章節結構**的前提下
- 被誘導、分群、排序與保留

這個 artifact 不是最終要給人閱讀的 review outline，而是**一個中間層的結構化證據帳本**。
它的核心功能不是「把 outline 寫漂亮」，而是「把 outline 為什麼可以從 references 長出來」這件事表達成一份可檢查、可對帳、可修補的 YAML。

### 2. 它不是什麼

它**不是**：

- `outline.json` 的重寫版
- `COT.md` 的改寫版
- gold section structure 的投影
- 一份渲染好的大綱
- 一份自由發揮的 taxonomy 草稿
- 一份依賴論文全文 narrative 才能成立的分析

它必須避免：

- 從 `outline.json` 偷看 hierarchy
- 從 `COT.md` 借用 section names 或 section order
- 用 IMRaD 或任意慣例模板硬套結構
- 用不存在於 reference metadata 的 claim 來合理化 node

### 3. 它的輸入是什麼

合法輸入只有兩種：

- review title
- supplied reference metadata

其中 reference metadata 應是**逐篇 reference 的結構化資訊**，最少要能辨識 reference 身分，最好包含：

- `key`
- `title`
- `abstract`
- `published_date`
- `source`
- `source_id`
- `match_status`

如果某篇 reference metadata 很弱，該 reference 仍可保留在輸入中；但它可以被放入 `unassigned_refs`，而不是被硬塞進錯誤 node。

### 4. 它的任務是什麼

它的任務是建立一份**reference-grounded section induction ledger**，也就是：

- 提出一組 candidate nodes
- 決定每個 node 的層級與標題候選
- 說明 node 的功能角色
- 把每個 reference 指派到某個 node，或保留為未指派
- 為 node 的順序提供理由
- 為每個 reference 的指派提供個案化理由

換句話說，它是在回答：

> 如果我只能看 review title 和 references metadata，最合理、最可稽核、最不偷看 gold 的 outline induction 結構會長什麼樣子？

### 5. 它的輸出型態是什麼

輸出必須是**YAML only**。
不可在 YAML 前後加任何說明文字。
不可輸出 `rendered_outline`。

固定 top-level keys 為：

- `artifact_type`
- `artifact_alias`
- `source_mode`
- `paper_id`
- `title`
- `inputs`
- `nodes`
- `ref_assignment_ledger`
- `unassigned_refs`

固定常數語義為：

- `artifact_type = reference_grounded_outline_induction_ir`
- `artifact_alias = section_aligned_taxonomy_ledger`
- `source_mode = reference_only`

### 6. `inputs` 的語義

`inputs` 不承載原始資料本身，而是承載** provenance-level truth flags**：

- `inputs.title: true`
- `inputs.reference_metadata: true`
- `inputs.gold_outline: false`

它的意思是：

- 這份 artifact 確實使用了 title
- 確實使用了 reference metadata
- 沒有把 gold outline 當作生成依據

### 7. `nodes` 的語義

`nodes` 是一份 candidate hierarchy 的 node list。
每個 node 都至少必須有：

- `node_id`
- `level`
- `title_candidate`
- `node_role`
- `parent`
- `refs_complete`

欄位含義如下：

- `node_id`
  - 該 node 的穩定識別碼
- `level`
  - 該 node 在 candidate hierarchy 中的層級
- `title_candidate`
  - 根據 title + reference metadata 誘導出的節點標題候選
- `node_role`
  - 該 node 在整體結構中的功能，例如 theme、container、framing node、evaluation theme 等
- `parent`
  - 父節點 ID；top-level node 必須是 `null`
- `refs_complete`
  - 被完整歸入該 node 的 reference keys 清單

常見 optional fields：

- `inclusion_rule`
  - 說明什麼類型的 references 應被納入這個 node
- `ordering_reason`
  - 說明這個 node 為什麼出現在此排序位置
- `preserve_reason`
  - 當空節點被保留時，說明它為什麼仍應存在

### 8. `ref_assignment_ledger` 的語義

`ref_assignment_ledger` 是 reference assignment 的總帳。
每筆至少要有：

- `ref_key`
- `assigned_to`
- `assignment_reason`

欄位含義如下：

- `ref_key`
  - 一個輸入 reference 的唯一 key
- `assigned_to`
  - 該 reference 被指派到哪些 node
  - 預設偏好單一歸屬
  - 如果是未指派 reference，應為空 list
- `assignment_reason`
  - 個案化的指派理由
  - 必須指出**正向 metadata evidence**
  - 在必要時要說明為什麼沒有選相鄰 sibling nodes

這個 ledger 的目的不是摘要 paper，而是保證：

- 每個 reference 的去向可查
- 每個 assignment 可被 challenge
- 後續 repair 可以精確修單筆 reference，而不是整份檔重寫

### 9. `unassigned_refs` 的語義

`unassigned_refs` 是一份明確的保守區。

一個 reference 應進入 `unassigned_refs`，當：

- metadata 太薄
- metadata 過於泛化
- 無法區分多個相近 sibling nodes
- 任何合理指派都會顯得過度自信

`unassigned_refs` 不是失敗，而是**忠於證據邊界**的表現。

### 10. 指派原則

這份 IR 的 reference assignment 應遵守：

- 偏好 single-home assignment
- 除非 metadata 明確支持多重角色，否則不要 multi-home
- 弱證據時寧可 unassigned，不要硬配
- generic cues 不足以支撐狹窄葉節點

以下訊號通常**不夠**單獨決定狹窄 node：

- `pre-training`
- `architecture`
- `large language model`
- `survey`
- `benchmark`

除非 reference metadata 同時提供更具鑑別性的主題證據。

### 11. node 設計原則

一個好的 node 必須：

- 有可辨識的主題邊界
- 可由 reference metadata 支撐
- 與相鄰 siblings 有可說明的區隔
- 標題夠短、夠 audit-friendly
- 若是 leaf node，應該具有 discriminative power

一個不好的 node 通常是：

- 太廣，任何 foundation paper 都能進
- 太像模板節名
- 太依賴 gold hierarchy 才成立
- 沒有 refs，卻又不是 grouping/framing node

### 12. 排序原則

node 順序不能只是「看起來合理」。
只要不是顯而易見的 trivial order，就要提供 `ordering_reason`。

排序的合理來源可以包括：

- 從背景到專題
- 從方法到現象
- 從經典到前沿
- 從資源到模型到評估
- 從共通 framing 到分化主題

但不可以只是：

- 因為 gold outline 長這樣
- 因為一般 review 都這樣寫

### 13. 稽核標準

一份合格的 `reference-only outline induction IR` 至少要滿足：

- YAML 可解析
- top-level keys 完整
- 每個 node 的 required fields 完整
- 每個 ledger item 的 required fields 完整
- 沒有 `rendered_outline`
- `inputs.gold_outline = false`
- 每個輸入 reference 都有去向：
  - 出現在某個 node 的 `refs_complete`
  - 或出現在 `unassigned_refs`
- `ref_assignment_ledger` 能覆蓋每個輸入 `ref_key`

### 14. 一句話定義

中文一句話版：

> `reference-only outline induction IR` 是一份只依據 review title 與 reference metadata 建立的、可稽核的 YAML 中介表示，用來記錄候選 outline 節點、reference 指派、未指派項目，以及這些結構決策的證據理由。

---

## English Definition

### 1. What This Is

A `reference-only outline induction IR` is an **auditable intermediate representation** that describes:

- a candidate hierarchical outline for a literature review,
- induced **only from the review title and supplied reference metadata**,
- without relying on any gold outline, stored `COT.md`, or previously extracted section structure.

It is not the final human-facing outline.
It is a **structured evidence ledger** that records how an outline could be induced from the references alone.

### 2. What This Is Not

It is **not**:

- a rewrite of `outline.json`
- a rewrite of `COT.md`
- a projection of the gold section structure
- a rendered outline
- a free-form taxonomy draft
- an analysis that depends on full-paper narrative context

It must not:

- peek at `outline.json` for hierarchy
- borrow section names or ordering from `COT.md`
- impose IMRaD or any other default scaffold unless the metadata itself supports it
- justify nodes with claims that are absent from the supplied metadata

### 3. What the Allowed Inputs Are

The only legal inputs are:

- the review title
- the supplied reference metadata

Reference metadata should be structured per reference.
At minimum, each entry should allow identity tracking; ideally it includes:

- `key`
- `title`
- `abstract`
- `published_date`
- `source`
- `source_id`
- `match_status`

If a reference is metadata-thin, it may still remain in the input set; it can be placed into `unassigned_refs` instead of being forced into a weak node.

### 4. What the Artifact Must Do

The artifact must function as a **reference-grounded section induction ledger**.
That means it must:

- propose candidate nodes
- define each node’s hierarchical role
- assign each reference to a node or leave it unassigned
- justify node ordering
- justify each reference assignment

In other words, it answers:

> If the model is allowed to see only the review title and reference metadata, what is the most defensible and auditable outline-induction structure it can produce?

### 5. What the Output Format Is

The output must be **YAML only**.
There must be no prose before or after the YAML.
It must not contain `rendered_outline`.

The required top-level keys are:

- `artifact_type`
- `artifact_alias`
- `source_mode`
- `paper_id`
- `title`
- `inputs`
- `nodes`
- `ref_assignment_ledger`
- `unassigned_refs`

The fixed semantic constants are:

- `artifact_type = reference_grounded_outline_induction_ir`
- `artifact_alias = section_aligned_taxonomy_ledger`
- `source_mode = reference_only`

### 6. Semantics of `inputs`

`inputs` does not carry the raw title or raw references themselves.
It records **provenance-level truth conditions**:

- `inputs.title: true`
- `inputs.reference_metadata: true`
- `inputs.gold_outline: false`

This means:

- the artifact did use the title,
- it did use reference metadata,
- and it did not use a gold outline as generation supervision.

### 7. Semantics of `nodes`

`nodes` is the list of candidate hierarchy nodes.
Each node must contain:

- `node_id`
- `level`
- `title_candidate`
- `node_role`
- `parent`
- `refs_complete`

Field meanings:

- `node_id`
  - a stable identifier for the node
- `level`
  - the node’s level in the candidate hierarchy
- `title_candidate`
  - the candidate section title induced from title + reference metadata
- `node_role`
  - the functional role of the node, such as theme, container, framing node, or evaluation theme
- `parent`
  - the parent node ID; top-level nodes must use `null`
- `refs_complete`
  - the list of reference keys fully assigned to that node

Common optional fields:

- `inclusion_rule`
  - what kinds of references belong in the node
- `ordering_reason`
  - why the node appears in that position
- `preserve_reason`
  - why an otherwise empty structural node is still worth preserving

### 8. Semantics of `ref_assignment_ledger`

`ref_assignment_ledger` is the master ledger of reference assignments.
Each item must contain:

- `ref_key`
- `assigned_to`
- `assignment_reason`

Field meanings:

- `ref_key`
  - the unique key of one input reference
- `assigned_to`
  - the list of node IDs to which the reference is assigned
  - single-home assignment is preferred
  - for an unassigned reference, this should be an empty list
- `assignment_reason`
  - a case-specific reason for the assignment
  - it must cite positive evidence from the supplied metadata
  - when needed, it should explain why nearby sibling nodes were not chosen

This ledger exists so that:

- every reference has a traceable destination,
- every assignment can be challenged,
- and repair can target one reference at a time instead of regenerating the whole file.

### 9. Semantics of `unassigned_refs`

`unassigned_refs` is an explicit conservative holding zone.

A reference should appear there when:

- the metadata is too thin,
- the metadata is too generic,
- sibling nodes are too difficult to distinguish,
- or any assignment would be overconfident relative to the evidence.

`unassigned_refs` is not a failure state.
It is evidence that the artifact respects its epistemic boundary.

### 10. Assignment Principles

Reference assignment should follow these rules:

- prefer single-home assignment
- only use multi-home assignment when the metadata directly supports more than one distinct thematic role
- prefer `unassigned_refs` over weak assignment
- generic cues should not be enough to justify a narrow leaf node

The following signals are usually **insufficient on their own**:

- `pre-training`
- `architecture`
- `large language model`
- `survey`
- `benchmark`

Unless the metadata also contains stronger discriminative thematic evidence.

### 11. Node Design Principles

A good node should be:

- thematically bounded,
- supportable from the supplied reference metadata,
- distinguishable from neighboring sibling nodes,
- concise and audit-friendly,
- and discriminative if it is a leaf node.

A weak node is usually:

- too broad,
- too template-like,
- dependent on hidden gold structure,
- or empty without being a real grouping or framing node.

### 12. Ordering Principles

Node order cannot be justified by “it looks reasonable.”
Whenever ordering is not trivial, the artifact should provide `ordering_reason`.

Valid sources of ordering logic include:

- background to specialization
- methods to phenomena
- classic to frontier
- resources to models to evaluation
- framing context to differentiated themes

Invalid sources of ordering logic include:

- “because the gold outline does this”
- “because reviews usually look like this”

### 13. Audit Criteria

A valid `reference-only outline induction IR` should satisfy at least the following:

- the YAML parses
- all required top-level keys exist
- every node contains the required fields
- every ledger item contains the required fields
- `rendered_outline` is absent
- `inputs.gold_outline = false`
- every input reference appears either:
  - in some node’s `refs_complete`, or
  - in `unassigned_refs`
- `ref_assignment_ledger` covers every input `ref_key`

### 14. One-Sentence Definition

One-sentence English version:

> A `reference-only outline induction IR` is an auditable YAML intermediate representation that uses only a review title and reference metadata to record candidate outline nodes, reference assignments, unassigned references, and the evidence-based reasons behind those structural decisions.
