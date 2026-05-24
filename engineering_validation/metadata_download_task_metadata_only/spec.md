# metadata_download_task_metadata_only Spec

## 1) Scope

- 將 metadata 下載任務流程搬回 `~/Desktop/Outline_COT`。
- 與 raw dataset 對齊，來源固定為：
  - `/Users/xjp/Desktop/Outline_COT/data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/hf_meow_raw_high261.full.jsonl`
- 不改 `NLP_PRISMA_Reviews` 任何 code。

## 2) Inputs / outputs

### 輸入
- `INPUT_ROOT`：預設為 HF raw full JSONL（上方路徑）。
- 可用 `PAPER_NAME` 限定單篇。
- `LIMIT` 預設 `20`，表示剔除已有 abstract 後，取前 `20` 筆需要補 metadata 的 ref 記錄。若要全量，請明確設 `LIMIT=`（空值）以關閉上限。
- legacy mode：若 `INPUT_ROOT` 是目錄，維持原有 `reference_oracle` 目錄格式。

### 輸出
- `FILTER_ROOT/filtered_input/<paper>/reference_oracle.jsonl`
- `SUMMARY_PATH`
- `LOG_ROOT/<run_id>.log`

## 3) 行為需求

1. 預設參數
   - `INPUT_ROOT` 指向 HF raw dataset。
   - `LIMIT=20`
   - `RUN_COLLECT=false`
   - `FILTER_MISSING_ONLY=true`
2. 濾除邏輯
   - legacy mode：沿用原先 `refs`/`reference_oracle` 邏輯。
   - hf raw mode：讀 `raw.ref_meta`（或 top-level `ref_meta`）並篩出缺抽象的 key。
- `LIMIT` 在 hf raw mode 對應「剔除已具 abstract 的 reference 後，取前 N 筆仍缺 abstract 的 reference」，不是 survey/review 筆數。
3. 不做 collector 時
- `RUN_COLLECT=false` 時只做 filtered refs 與 summary。
3. 做 collector 時
   - `RUN_COLLECT=true` 時，使用 `COLLECT_SCRIPT` 對 `reference_oracle` 逐筆做實際 metadata 下載。
   - 預設 API provider 順序為 `arxiv,semantic_scholar,openalex,crossref,dblp,pubmed,ieee`（若可用；`IEEE` 需要 `IEEE_API_KEY` 或 `IEEE_XPLORE_API_KEY` 才能啟用）。
   - `dblp`、`pubmed`、`ieee` 會在設定的 provider order 內參與嘗試；未設定 key 的 `ieee` 會被記錄為 provider error 並跳過。
   - collector 預設單線程執行（`COLLECT_MAX_WORKERS=1`）；設 `COLLECT_MAX_WORKERS=N` 可並行，每個 paper 佔一個 worker thread。
   - 輸出檔案是 `run_root/<paper>/metadata/title_abstracts_metadata.jsonl`。
4. 可重複跑與 debug
   - 支持 `PAPER_NAME`, `LIMIT`, `RUN_ID`, `RUN_ROOT` 覆蓋。

## 4) 失敗條件

- `INPUT_ROOT` 不存在或不是檔案/目錄。
- 參數布林值格式不合法。
- `RUN_COLLECT=true` 但 `COLLECT_SCRIPT` 不存在。

## 5) 接受標準

- 腳本預設 1 次僅掃描前 20 筆「缺 abstract 的」HF raw reference（除非 `LIMIT` 覆蓋）。
- summary 可正確輸出 `selected_rows`、`source_rows`、每 paper 統計。
- 生成 `filtered_input` 供後續 collector。
