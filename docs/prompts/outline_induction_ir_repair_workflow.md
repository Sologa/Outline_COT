# Outline Induction IR Repair Workflow

This file is for humans and agents. It defines how to repair audited `outline_induction_ir.yaml` artifacts after a batch generation pass.

Use this workflow when:
- the IR already exists under `data/paper_sets/meow_refs/<paper_id>/outline_induction_ir.yaml`
- you have audit findings for that file
- you want Codex to edit the existing YAML instead of regenerating the whole artifact

Use the following files as the fixed repair baseline:
- [outline_induction_ir_user.txt](/Users/xjp/Desktop/Outline_COT/prompts/outline_induction_ir_user.txt)
- [outline_induction_ir_audit_2026-04-05.md](/Users/xjp/Desktop/Outline_COT/data/outline_induction_ir_audit_2026-04-05.md)

## Why New Conversations

The recent IR batch was generated with [run_outline_induction_ir_loop.sh](/Users/xjp/Desktop/Outline_COT/scripts/run_outline_induction_ir_loop.sh), which calls `codex exec --ephemeral`. In practice, those generation sessions are not reusable as persistent repair threads.

For that reason, the repair workflow is:
- one paper per new Codex conversation
- targeted editing of the existing YAML
- re-audit immediately after each repair

Do not:
- repair 5 papers in one conversation
- ask Codex to batch-fix all files at once
- treat this as a full regeneration task unless the file has lost auditability

## Repair Order

Repair the current audited batch in this order:

1. `2510.01145`
2. `2503.04799`
3. `2312.05172`
4. `2310.07264`
5. `2511.13936`

Rationale:
- start with the worst provenance and taxonomy failures first
- leave the strongest file for last because it is a small-fix candidate

## Acceptance Criteria

Each repaired file should satisfy all of the following before you move to the next paper:

- schema still passes
- `ref_assignment_ledger` matches `refs_complete`
- reference universe no longer clearly conflicts with the provenance snapshot, or the remaining mismatch is explicitly explained
- catch-all nodes are split or narrowed
- boilerplate `assignment_reason` is replaced with case-specific reasoning
- weak or low-evidence references are moved to `unassigned_refs`

If a repaired file still has a severe provenance mismatch after targeted editing, do not keep patching locally. Escalate that paper to a constrained single-paper regeneration flow.

## Copy-Ready Repair Prompt

Use this prompt in a new Codex conversation. Replace `{paper_id}` with the target paper.

```text
先讀 `AGENTS.md`。

再讀 `prompts/outline_induction_ir_user.txt`，把它當成這份 artifact 的生成規格，而不是要你重新生成整份 YAML 的 payload。

再讀 `data/outline_induction_ir_audit_2026-04-05.md`。

任務：
針對 `data/paper_sets/meow_refs/{paper_id}/outline_induction_ir.yaml` 做定向改稿，直接修正既有檔案，使它更接近一份真正可審計的 reference-only outline induction IR。

這不是重生成任務。
這次要做的是 edit existing artifact，不是從頭另寫一份新 IR。

工作方式：
- 先讀目前的 `data/paper_sets/meow_refs/{paper_id}/outline_induction_ir.yaml`
- 從 audit 檔中抽出屬於 `{paper_id}` 的 findings，當成硬性修正目標
- 必要時檢查本地可用的 title / reference metadata / provenance artifacts，確認 reference set、key、title、與輸入邊界是否一致
- 不可使用 `outline.json` 或 `COT.md` 來決定 taxonomy、node hierarchy、section titles、或 assignment
- 你可以用 `outline.json` 或 `COT.md` 做 provenance 風險排查，但不能把它們當答案來回填

硬性要求：
- 保留 top-level YAML schema 不變
- 不可新增 `rendered_outline`
- 每個 reference 必須要嘛出現在某個 node 的 `refs_complete`，要嘛出現在 `unassigned_refs`
- `ref_assignment_ledger` 必須和 `refs_complete` 真正一致
- 若 provenance snapshot 與實際 reference set 不一致，要先修正 reference universe，再修 taxonomy
- 優先提高 taxonomy precision，而不是維持 node 數量或 assignment 密度
- 對 metadata 薄弱、key 品質差、或無法可靠歸類的 refs，寧可放進 `unassigned_refs`
- `assignment_reason` 必須改成 case-specific，不能繼續用 boilerplate
- 若 leaf node 太寬，必須拆分；若無法合理拆分，則要縮減其 refs 並增加 `unassigned_refs`
- 若某些 refs 只是 protocol / demographic / background / placeholder sources，不可硬塞進窄的內容 taxonomy node

請特別優先修正：
- audit 中標成 high-priority 的問題
- reference count / reference universe mismatch
- catch-all nodes
- cue-triggered assignments
- sibling boundary 不清造成的錯分
- placeholder 或低品質 key 被當成正常可分配 reference 的問題
- 幾乎全篇 boilerplate 的 `assignment_reason`

完成後請回報：
- 你改了哪些類型的問題
- top-level node 數量是否改變
- assigned references 數量
- unassigned references 數量
- 你仍然覺得最不穩定的 1-3 個 node
- 哪些 audit finding 你認為已解決，哪些仍未完全解決
```

## First-Paper Prompt

Start with the worst file first:

```text
先讀 `AGENTS.md`。

再讀 `prompts/outline_induction_ir_user.txt`，把它當成這份 artifact 的生成規格，而不是要你重新生成整份 YAML 的 payload。

再讀 `data/outline_induction_ir_audit_2026-04-05.md`。

任務：
針對 `data/paper_sets/meow_refs/2510.01145/outline_induction_ir.yaml` 做定向改稿，直接修正既有檔案，使它更接近一份真正可審計的 reference-only outline induction IR。

這不是重生成任務。
這次要做的是 edit existing artifact，不是從頭另寫一份新 IR。

工作方式：
- 先讀目前的 `data/paper_sets/meow_refs/2510.01145/outline_induction_ir.yaml`
- 從 audit 檔中抽出屬於 `2510.01145` 的 findings，當成硬性修正目標
- 必要時檢查本地可用的 title / reference metadata / provenance artifacts，確認 reference set、key、title、與輸入邊界是否一致
- 不可使用 `outline.json` 或 `COT.md` 來決定 taxonomy、node hierarchy、section titles、或 assignment
- 你可以用 `outline.json` 或 `COT.md` 做 provenance 風險排查，但不能把它們當答案來回填

硬性要求：
- 保留 top-level YAML schema 不變
- 不可新增 `rendered_outline`
- 每個 reference 必須要嘛出現在某個 node 的 `refs_complete`，要嘛出現在 `unassigned_refs`
- `ref_assignment_ledger` 必須和 `refs_complete` 真正一致
- 若 provenance snapshot 與實際 reference set 不一致，要先修正 reference universe，再修 taxonomy
- 優先提高 taxonomy precision，而不是維持 node 數量或 assignment 密度
- 對 metadata 薄弱、key 品質差、或無法可靠歸類的 refs，寧可放進 `unassigned_refs`
- `assignment_reason` 必須改成 case-specific，不能繼續用 boilerplate
- 若 leaf node 太寬，必須拆分；若無法合理拆分，則要縮減其 refs 並增加 `unassigned_refs`
- 若某些 refs 只是 protocol / demographic / background / placeholder sources，不可硬塞進窄的內容 taxonomy node

請特別優先修正這篇在 audit 中提到的問題：
- provenance snapshot 是 94 refs，但目前 IR 覆蓋 113 unique refs
- `n_asr_models` 吸了 84 refs，已成 catch-all bucket
- `n_african_resources` 混入 PRISMA、World Bank、WPR、Nations Online 這類 framing / demographic sources
- `NationsOnline2025` 和 `nationsonline2025` 的 key boundary 不清

完成後請回報：
- 你改了哪些類型的問題
- top-level node 數量是否改變
- assigned references 數量
- unassigned references 數量
- 你仍然覺得最不穩定的 1-3 個 node
- 哪些 audit finding 你認為已解決，哪些仍未完全解決
```

## Copy-Ready Re-Audit Prompt

Run this immediately after repairing a paper.

```text
先讀 `AGENTS.md`。

再讀 `prompts/outline_induction_ir_user.txt`。

再讀 `data/outline_induction_ir_audit_2026-04-05.md`，但只把它當成前一輪問題清單，不要重複抄寫舊結論。

任務：
重新審核 `data/paper_sets/meow_refs/{paper_id}/outline_induction_ir.yaml`，確認這份修正版是否已修掉前一輪 audit 的主要問題。

要求：
- findings first
- 優先檢查前一輪 audit 提到的問題是否真的解決
- 檢查 schema、reference coverage、ledger consistency、taxonomy precision、assignment quality、provenance closure
- 若仍有問題，請指出剩餘問題是：
  - `blocking`
  - `important but non-blocking`
  - `minor`
- 不要直接修改檔案

最後請輸出：
- 已解決的問題
- 尚未解決的問題
- 整體判定：
  - `still not usable`
  - `usable with revisions`
  - `strong`
```
