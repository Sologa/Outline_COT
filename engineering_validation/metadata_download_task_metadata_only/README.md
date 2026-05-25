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
- 預設 `COLLECT_USE_STAGING=true`，collector 會先寫到 `.local/metadata_download_staging/<RUN_ID>`，逐篇驗證 row count 後才發佈到 `results/`。
- 任何 staged/final JSONL row count 與 filtered input 不一致時，run 必須 fail；不要只因 log 出現 `total_written` 或 `[done]` 就宣稱結果可用。
- 可選 API identity：`METADATA_API_MAILTO` 會放入 OpenAlex/Crossref query 與 User-Agent；`SEMANTIC_SCHOLAR_API_KEY` 或 `S2_API_KEY` 會送到 Semantic Scholar；`OPENALEX_API_KEY` 會送到 OpenAlex。
- 可選 `METADATA_ENV_FILE=/path/to/.env` 只會載入 metadata provider 相關 key，不會載入一般實驗設定。

執行入口：
- `./run_metadata_task.sh`

輸出：
- `filtered_input/<paper_id>/reference_oracle.jsonl`：待補 metadata 的參考文獻（每筆 jsonl 一條）
- `/<paper_id>/metadata/title_abstracts_metadata.jsonl`：`RUN_COLLECT=true` 時，透過 API 寫入的 metadata（已依參考鍵寫入）
- `metadata_download_filter_summary.json`：總體統計與 per-paper 報表
- `logs/<run_id>.log`

metadata/abstract 內容驗證：
- `scripts/download/verify_title_abstract_metadata.py --run-root <run_root>` 會比對 `filtered_input` 與 metadata output。
- 這個 verifier 的統一自動依據是 `key`/row order、normalized `title`，以及可用時的 `year`；它不把 provider 回傳的 DOI/provider id 視為 input ground truth。
- 非空 abstract 只有在 provider/output title 對上 input title 時才會列為 `verified_title_year` 或 `verified_title_only`；title mismatch、year mismatch、fuzzy-only title match 會列入 suspicious / review bucket。
- verifier 會輸出 `_verification/metadata_title_verification_summary.json` 和 `_verification/metadata_title_verification_rows.jsonl`，供後續抽樣人工核對。
- `scripts/download/adjudicate_metadata_title_pairs_openai.py --run-root <run_root>` 可用 `gpt-5-nano` 對 suspicious/review rows 做 title-only adjudication；prompt 只包含 input title 與 metadata title，不包含 abstract/provider/DOI。
- OpenAI adjudication 輸出 `_verification/metadata_title_pair_openai_adjudication.jsonl` 和 summary JSON；它只能把 title-only 可疑項分成 `same`/`different`/`uncertain`，不能替代 DOI/author 層級驗證。
- `scripts/download/repair_metadata_mismatches.py --run-root <run_root>` 會重下載 GPT 判定 `different`/`uncertain` 的 rows。若 strict title gate 找不到可靠 abstract，該 row 會被改成 unresolved blank；已重下載仍未對上的 rows 可用 `--clear-only` 強制清空。
- `scripts/download/merge_verified_metadata_into_hf_raw.py` 會把通過驗證的 metadata abstract 融合回 HF raw dataset 的 derived copy。接受條件只有兩種：verifier status 為 `verified_title_year` / `verified_title_only`，或 OpenAI title-only adjudication 為 `same`。它只填原本 blank 的 `raw.ref_meta[].abstract`，不覆蓋既有 abstract，也不修改原始 `hf_meow_raw_high261.full.jsonl`。
- merge script 會為新增 abstract 加上 `metadata_source=verified_api`、provider、candidate title/year、verification/adjudication 與 run id provenance，並輸出 merge report / per-row action JSONL 供查核。

安全規則：
- `results/` 是 Google Drive sync 區，不適合長時間 active collector 直接寫 per-row output。
- active collector output 必須先落在 `.local` staging；發佈到 `results/` 前後都要重新讀 disk 驗證 row count。
