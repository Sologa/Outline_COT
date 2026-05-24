# metadata_download_task_metadata_only

這個目錄是把 metadata 填補流程重建到 `Outline_COT`，只使用 local repo 的資料，不再引用 `NLP_PRISMA_Reviews`。

核心目標：
- 預設只處理 `data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/hf_meow_raw_high261.full.jsonl`。
- 預設 debug 流程 `LIMIT=20`（表示在剔除已具備 abstract 後的 20 筆缺 abstract reference）。
- 預設不跑 collector（`RUN_COLLECT=false`），只產生 filtered refs。
- `RUN_COLLECT=true` 時會真的透過 API 下載 metadata；預設 provider 順序為 `semantic_scholar,crossref,dblp,pubmed`。
- `openalex`、`arxiv` 與 `ieee` 仍支援但不在預設 full-run order；OpenAlex 每日 quota 很低，arXiv title search 容易 429，IEEE 需設定 `IEEE_API_KEY` 或 `IEEE_XPLORE_API_KEY`。
- collector 可用 `COLLECT_MAX_WORKERS` 控制同時 worker 數（預設 2），並用 `COLLECT_PROVIDER_DELAYS` 做跨 worker 的 provider-level 節流。
- `COLLECT_RATE_LIMIT_BACKOFF` 預設 30 秒，作為 429 backoff 上限與無 `Retry-After` 時的等待值，避免 smoke 卡在過長 provider 等待。
- provider 命中但沒有 abstract 時，不會立刻停止；collector 會保留該 metadata candidate 並繼續嘗試後續 provider，直到找到 abstract 或 provider 用完。
- 預設 `RESUME=true`，既有 output 中已有 abstract 的 key 會直接重用，未解出的 row 會重試。
- 可選 API identity：`METADATA_API_MAILTO` 會放入 OpenAlex/Crossref query 與 User-Agent；`SEMANTIC_SCHOLAR_API_KEY` 或 `S2_API_KEY` 會送到 Semantic Scholar；`OPENALEX_API_KEY` 會送到 OpenAlex。
- 可選 `METADATA_ENV_FILE=/path/to/.env` 只會載入 metadata provider 相關 key，不會載入一般實驗設定。

執行入口：
- `./run_metadata_task.sh`

輸出：
- `filtered_input/<paper_id>/reference_oracle.jsonl`：待補 metadata 的參考文獻（每筆 jsonl 一條）
- `/<paper_id>/metadata/title_abstracts_metadata.jsonl`：`RUN_COLLECT=true` 時，透過 API 寫入的 metadata（已依參考鍵寫入）
- `metadata_download_filter_summary.json`：總體統計與 per-paper 報表
- `logs/<run_id>.log`
