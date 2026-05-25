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
4. 做 collector 時
   - `RUN_COLLECT=true` 時，使用 `COLLECT_SCRIPT` 對 `reference_oracle` 逐筆做實際 metadata 下載。
   - 預設 API provider 順序為 `semantic_scholar,crossref,dblp,pubmed`。
   - `openalex`、`arxiv`、`ieee` 仍可透過 `SOURCE_ORDER` 啟用；OpenAlex 每日 quota 很低，`ieee` 需要 `IEEE_API_KEY` 或 `IEEE_XPLORE_API_KEY` 才能啟用。
   - collector 預設 `COLLECT_MAX_WORKERS=2`；每個 paper 佔一個 worker thread，但所有 worker 共用 provider-level throttle。
   - `COLLECT_PROVIDER_DELAYS` 預設 `semantic_scholar=1.5,crossref=1.0,dblp=1.0,pubmed=0.5,openalex=90.0,arxiv=3.2,ieee=1.0`；OpenAlex 若手動 opt-in，預設也會被限到接近每日 1000 次的安全節奏。
   - `COLLECT_RATE_LIMIT_BACKOFF` 預設 `30.0` 秒；收到 `Retry-After` 時以此為上限，未收到時用此值做 429 backoff。
   - provider query cache 以 `(provider, normalized_title)` 為 key，避免相同 title 重複查詢。
   - 429 會套用 provider-level backoff；若回應有 `Retry-After`，優先採用該值。
   - provider 回傳 title/ID metadata 但 abstract 為空時，該 candidate 只作為 fallback；collector 會繼續查後續 provider，優先輸出有 abstract 的 candidate。
   - `METADATA_API_MAILTO` 會加入 OpenAlex/Crossref query 與 User-Agent；`SEMANTIC_SCHOLAR_API_KEY` 或 `S2_API_KEY` 會加入 Semantic Scholar request；`OPENALEX_API_KEY` 會加入 OpenAlex request。
   - `METADATA_ENV_FILE` 可指向 `.env` 檔，腳本只會載入 metadata provider 相關 key。
   - 預設 `RESUME=true`，既有 output 中已有 non-empty abstract 的 rows 會重用，unresolved rows 會重試。
   - 預設 `COLLECT_USE_STAGING=true`，active collector output 先寫到 `.local/metadata_download_staging/<RUN_ID>`，逐篇驗證後才發佈到 `OUTPUT_ROOT`。
   - 輸出檔案是 `OUTPUT_ROOT/<paper>/metadata/title_abstracts_metadata.jsonl`；若未覆蓋 `OUTPUT_ROOT`，則等同 `run_root/<paper>/metadata/title_abstracts_metadata.jsonl`。
   - 每篇 collector temp output、staged output、final output 的 row count 都必須等於對應 filtered input 的 row count；若不一致，run 必須失敗。
5. metadata/abstract 驗證
   - 提供 `scripts/download/verify_title_abstract_metadata.py` 做本地 artifact 驗證，不重新呼叫 API。
   - verifier 必須先驗證 row count、row order、`key` 對齊；任何 `structural_*` 狀態都代表 artifact/pipeline 失敗。
   - 對非空 abstract，verifier 只用 input 端一致可用的欄位做自動內容檢查：normalized `title` 為主，`year` 為輔助。
   - `doi`、provider id、provider URL、provider raw payload 可作 provenance，但不能視為 input ground truth，因為原始 `reference_oracle.jsonl` 並不穩定提供這些欄位。
   - verifier 輸出 aggregate summary JSON 與 per-row JSONL；title mismatch、year mismatch、fuzzy-only match 必須保留為 suspicious/review 狀態，不能被報成 verified。
   - 可選 OpenAI title-only adjudicator 只處理 verifier 標出的 suspicious/review rows，且只把 input title 與 metadata title 放入 prompt。
   - OpenAI adjudicator 必須 async 執行、支援 resume、checkpoint、progress output，避免長時間 API run 中斷後損失進度。
   - OpenAI adjudication 只輸出 sidecar JSONL/summary；不得直接覆寫 metadata abstract 或把 model 判斷當作 DOI/author 層級真值。
   - GPT 判定 `different`/`uncertain` 的 rows 可用 repair script 重下載；repair 必須只替換 selected rows，保留 per-paper row order 與 key identity。
   - repair 必須先寫 `.local` staging，驗證 staged/final row count，再 publish final metadata。
   - repair 若 strict title gate 找不到可靠 abstract，必須清成 unresolved blank，不能保留先前錯配 abstract。
   - 已重下載後仍未對上的 rows 必須支援 `--clear-only` 強制清空，並保留 `_metadata_mismatch_repair` provenance。
6. verified metadata 融合
   - 提供 `scripts/download/merge_verified_metadata_into_hf_raw.py` 把通過驗證的 metadata abstract 寫入 HF raw dataset 的 derived copy。
   - merge input 必須是原始 HF raw JSONL、metadata run root、verification rows，以及可選 OpenAI title-only adjudication sidecar。
   - merge 接受條件只有 `verified_title_year`、`verified_title_only`，或 OpenAI adjudication `same`；其餘 suspicious/review/unresolved rows 不得寫入 derived raw。
   - merge 只能填補原本 blank 的 `raw.ref_meta[].abstract`；不得覆蓋原本已存在的 abstract。
   - merge 必須用 `paper/key/normalized_title` 對齊，避免只靠 key 將錯 title 的 abstract 融入。
   - merge 必須保留 provenance 欄位，包括 provider、provider id/url、candidate title/year、title similarity、verification status、adjudication、source run id 與 merge timestamp。
   - merge 必須寫出 report JSON 與 per-row action JSONL；report 至少包含原始/最終 ref row count、原始/最終 non-empty abstract count、填入數、existing abstract skip 數、unverified skip 數與 key/title mismatch 數。
   - 原始 `hf_meow_raw_high261.full.jsonl` 不得被修改；輸出必須是明確命名的 derived JSONL。
7. 可重複跑與 debug
   - 支持 `PAPER_NAME`, `LIMIT`, `RUN_ID`, `RUN_ROOT` 覆蓋。

## 4) 失敗條件

- `INPUT_ROOT` 不存在或不是檔案/目錄。
- 參數布林值格式不合法。
- `RUN_COLLECT=true` 但 `COLLECT_SCRIPT` 不存在。
- staged metadata output row count 與 filtered input 不一致。
- 發佈到 final `OUTPUT_ROOT` 後，final metadata output row count 與 filtered input 不一致。
- 任何 expected rows > 0 的 per-paper final metadata output 是 0-byte。

## 5) 接受標準

- 腳本預設 1 次僅掃描前 20 筆「缺 abstract 的」HF raw reference（除非 `LIMIT` 覆蓋）。
- summary 可正確輸出 `selected_rows`、`source_rows`、每 paper 統計。
- 生成 `filtered_input` 供後續 collector。
- collector 不會因 worker 並行而對同一 provider 無節制發送 request。
- rerun 不會覆蓋已成功補到 abstract 的 rows；未成功 rows 可被 retry。
- 長時間 collector 不直接把 active per-row writes 寫進 Drive-synced `results/`；必須先 staging，再驗證並發佈。
- log 的 `total_written` 不能單獨作為完成依據；接受前必須從 disk 重新計算 final artifact row counts。
- merge derived copy 前必須完成 title verification；merge 後 raw/derived JSONL 行數與 ref row count 必須一致，且 merge report 的 `filled_new_abstracts` 必須等於 per-row action JSONL 的 `filled` 行數。
