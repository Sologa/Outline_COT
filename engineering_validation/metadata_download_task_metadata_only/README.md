# metadata_download_task_metadata_only

這個目錄是把 metadata 填補流程重建到 `Outline_COT`，只使用 local repo 的資料，不再引用 `NLP_PRISMA_Reviews`。

核心目標：
- 預設只處理 `data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/hf_meow_raw_high261.full.jsonl`。
- 預設 debug 流程 `LIMIT=20`（表示在剔除已具備 abstract 後的 20 筆缺 abstract reference）。
- 預設不跑 collector（`RUN_COLLECT=false`），只產生 filtered refs。
- `RUN_COLLECT=true` 時會真的透過 API 下載 metadata（arXiv/Semantic Scholar/OpenAlex/Crossref 先行，接著嘗試 `dblp`, `pubmed`, `ieee`；IEEE 需設定 `IEEE_API_KEY` 或 `IEEE_XPLORE_API_KEY`）。
- collector 可用 `COLLECT_MAX_WORKERS` 控制同時 worker 數（預設 1）；建議初始設定為 2~3，視 API 回應情況逐步上調。

執行入口：
- `./run_metadata_task.sh`

輸出：
- `filtered_input/<paper_id>/reference_oracle.jsonl`：待補 metadata 的參考文獻（每筆 jsonl 一條）
- `/<paper_id>/metadata/title_abstracts_metadata.jsonl`：`RUN_COLLECT=true` 時，透過 API 寫入的 metadata（已依參考鍵寫入）
- `metadata_download_filter_summary.json`：總體統計與 per-paper 報表
- `logs/<run_id>.log`
