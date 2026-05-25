# metadata_download_task_metadata_only Runbook

## 0. 一定先確認

- 工作目錄：`~/Desktop/Outline_COT`
- 不要讀寫 `NLP_PRISMA_Reviews`

## 1. Debug（預設）

```bash
cd /Users/xjp/Desktop/Outline_COT
export RUN_ID=metadata_debug
export LIMIT=20
export RUN_COLLECT=false
./engineering_validation/metadata_download_task_metadata_only/run_metadata_task.sh
```

預期結果：
- 只會在 debug 中生成 filtered refs，不呼叫 collector。
- 可在 `logs/metadata_debug.log` 和 `metadata_download_filter_summary.json` 查看「先剔除已有 abstract，後取 20 筆」的範圍結果。

## 1b. Smoke API 下載（20 筆 ref）

```bash
cd /Users/xjp/Desktop/Outline_COT
export RUN_ID=metadata_debug
export LIMIT=20
export RUN_COLLECT=true
export FILTER_MISSING_ONLY=true
export COLLECT_MAX_WORKERS=2
export SOURCE_ORDER="semantic_scholar,crossref"
export METADATA_ENV_FILE=/Users/xjp/Desktop/NLP_PRISMA_Reviews/.env
export RESUME=false
export COLLECT_RATE_LIMIT_BACKOFF=10
./engineering_validation/metadata_download_task_metadata_only/run_metadata_task.sh
```

- 會先過濾掉已有 abstract，取前 20 筆缺 abstract 的 reference（或更少，取決於 `PAPER_NAME`）。
  - 會透過 API 實際下載/補齊 metadata。
  - `COLLECT_MAX_WORKERS=2` 會以 paper 為單位並行，但 provider request 會共用 throttle。
  - OpenAlex 不在預設 smoke/full-run order；若手動加回，先確認每日 quota 與 `openalex=90.0` 等級的 provider delay。
  - 若要進入 OpenAlex/Crossref polite pool，設定 `METADATA_API_MAILTO`。
  - 若有 Semantic Scholar key，設定 `SEMANTIC_SCHOLAR_API_KEY` 或 `S2_API_KEY`。
- 預設 `COLLECT_USE_STAGING=true`，collector 先寫到 `.local/metadata_download_staging/<RUN_ID>`，驗證後才發佈到 `results/`。
- 輸出 metadata 位於 `results/engineering_validation/metadata_download_task_metadata_only/.../<paper>/metadata/title_abstracts_metadata.jsonl`

## 2. 擴展到全量（必要時）

```bash
cd /Users/xjp/Desktop/Outline_COT
export LIMIT=
export RUN_COLLECT=true
export COLLECT_SCRIPT=/Users/xjp/Desktop/Outline_COT/scripts/download/collect_title_abstracts_priority.py
export COLLECT_MAX_WORKERS=2
export SOURCE_ORDER="semantic_scholar,crossref,dblp,pubmed"
export METADATA_ENV_FILE=/Users/xjp/Desktop/NLP_PRISMA_Reviews/.env
export RESUME=true
./engineering_validation/metadata_download_task_metadata_only/run_metadata_task.sh
```

預設 provider delays：

```bash
export COLLECT_PROVIDER_DELAYS="semantic_scholar=1.5,crossref=1.0,dblp=1.0,pubmed=0.5,openalex=90.0,arxiv=3.2,ieee=1.0"
export COLLECT_RATE_LIMIT_BACKOFF=30
```

`openalex`、`arxiv` 與 `ieee` 不在 full-run 預設 order；只在明確需要時加回 `SOURCE_ORDER`。

全量或長時間 repair run 不要把 active collector output 直接寫入 `results/`。如果需要覆蓋既有 run 的 metadata 檔，設定：

```bash
export RUN_ROOT=/Users/xjp/Desktop/Outline_COT/.local/metadata_download_runs/<repair_run_id>
export OUTPUT_ROOT=/Users/xjp/Desktop/Outline_COT/results/engineering_validation/metadata_download_task_metadata_only/<target_run_id>
export COLLECT_STAGING_ROOT=/Users/xjp/Desktop/Outline_COT/.local/metadata_download_staging/<repair_run_id>
export COLLECT_USE_STAGING=true
```

run 結束時必須看到 `[validate] ... expected_rows=... final_rows=...` 且兩者相等，才可把結果視為完成。

## 3. 只處理單篇

```bash
cd /Users/xjp/Desktop/Outline_COT
export PAPER_NAME=2305.03803
export LIMIT=20
./engineering_validation/metadata_download_task_metadata_only/run_metadata_task.sh
```

> NOTE: `LIMIT=20` 在本流程裡是「剔除已有 abstract 後的前 20 筆缺 abstract reference」上限（不是 20篇 survey/review）。

## 4. 手工核對 output

- `run_root` 下 `filtered_input/<paper>/reference_oracle.jsonl`
- `run_root/<paper>/metadata/title_abstracts_metadata.jsonl`
- `metadata_download_filter_summary.json`
- `logs/<run_id>.log`

必查：

```bash
find <output_root> -path '*/metadata/title_abstracts_metadata.jsonl' -type f -print0 | xargs -0 wc -l
```

逐篇 row count 必須等於 `metadata_download_filter_summary.json` 或對應 filtered input 的 `selected_rows`。任何 0-byte final metadata 檔都視為失敗，需要用 `.local` staging 補跑，不可直接報完成。

## 5. title/abstract 內容驗證

row count 只能證明 artifact 完整；abstract 是否可能屬於正確論文，必須另外用 title/year 對照。

```bash
cd /Users/xjp/Desktop/Outline_COT
python3 scripts/download/verify_title_abstract_metadata.py \
  --run-root results/engineering_validation/metadata_download_task_metadata_only/<run_id>
```

預設會寫出：

- `<run_root>/_verification/metadata_title_verification_summary.json`
- `<run_root>/_verification/metadata_title_verification_rows.jsonl`

status 解讀：

- `verified_title_year`：normalized input title 與 metadata/provider title 相同，且 year 相同。
- `verified_title_only`：normalized title 相同，但至少一邊沒有 year。
- `unresolved_blank`：abstract 仍為空，沒有內容錯配風險，但也沒有補到 abstract。
- `needs_review_fuzzy_title`：title 相似但不是 normalized exact match，需要人工看。
- `suspicious_title_mismatch`：有 abstract 但 title 對不上，不能接受為正確 abstract。
- `suspicious_year_mismatch`：title 對上但 year 不同，需要人工看，因為 citation 年份也可能不準。
- `structural_*`：row count、row order 或 key 對齊出錯；這是 pipeline/artifact 失敗。

嚴格模式可讓 content suspicious/review 也用非 0 exit code：

```bash
python3 scripts/download/verify_title_abstract_metadata.py \
  --run-root results/engineering_validation/metadata_download_task_metadata_only/<run_id> \
  --strict
```

注意：目前 input 統一可比對的 bibliographic 欄位主要是 `title`，`year` 只是輔助；`doi`、provider id、provider URL 只能作為 provenance，不能當作和 input 對照的 ground truth。

## 6. OpenAI title-only adjudication

對 `verify_title_abstract_metadata.py` 標出的 suspicious/review rows，可用 `gpt-5-nano` 做第二層 title-only 審核。

先 dry-run 確認待審數：

```bash
python3 scripts/download/adjudicate_metadata_title_pairs_openai.py \
  --run-root results/engineering_validation/metadata_download_task_metadata_only/<run_id> \
  --dry-run
```

正式跑：

```bash
python3 scripts/download/adjudicate_metadata_title_pairs_openai.py \
  --run-root results/engineering_validation/metadata_download_task_metadata_only/<run_id> \
  --env-file /Users/xjp/Desktop/Outline_COT/.env \
  --model gpt-5-nano \
  --concurrency 8 \
  --timeout 45 \
  --checkpoint-every 10 \
  --progress-every 10 \
  --no-resume
```

若中斷後續跑，移除 `--no-resume` 讓腳本重用已完成 rows。

輸出：

- `<run_root>/_verification/metadata_title_pair_openai_adjudication.jsonl`
- `<run_root>/_verification/metadata_title_pair_openai_adjudication_summary.json`

限制：

- Prompt 只含兩個 title，不含 abstract、provider、DOI、URL。
- `same` 表示 title-only 判斷可接受為同一 work；`different` 應視為錯配 abstract；`uncertain` 需要人工看。
- 這仍然不是 DOI/author ground-truth verification。

## 7. 重下載沒對上的 rows

GPT title-only 判為 `different` 或 `uncertain` 的 rows 不應保留原 abstract。先 dry-run：

```bash
python3 scripts/download/repair_metadata_mismatches.py \
  --run-root results/engineering_validation/metadata_download_task_metadata_only/<run_id> \
  --dry-run
```

正式重下載：

```bash
python3 scripts/download/repair_metadata_mismatches.py \
  --run-root results/engineering_validation/metadata_download_task_metadata_only/<run_id> \
  --env-file /Users/xjp/Desktop/NLP_PRISMA_Reviews/.env \
  --staging-root /Users/xjp/Desktop/Outline_COT/.local/metadata_mismatch_repair/<repair_id> \
  --providers semantic_scholar,crossref,dblp,pubmed \
  --max-results 10 \
  --max-workers 4 \
  --min-title-similarity 0.95
```

行為：

- 只替換 adjudication sidecar 中 `different`/`uncertain` 的 rows。
- 先寫完整 per-paper JSONL 到 `.local` staging，驗證 row count，再 publish 到 final metadata。
- 若重下載找到 strict title match 的 abstract，寫入新 abstract。
- 若找不到可靠 match，改成 unresolved blank；不要保留舊錯配 abstract。
- 若重下載後 GPT 仍判不對，用 `--clear-only` 強制清空：

```bash
python3 scripts/download/repair_metadata_mismatches.py \
  --run-root results/engineering_validation/metadata_download_task_metadata_only/<run_id> \
  --staging-root /Users/xjp/Desktop/Outline_COT/.local/metadata_mismatch_repair/<repair_id> \
  --clear-only
```

repair 完成後必須重跑：

```bash
python3 scripts/download/verify_title_abstract_metadata.py --run-root <run_root>
python3 scripts/download/adjudicate_metadata_title_pairs_openai.py --run-root <run_root> --env-file /Users/xjp/Desktop/Outline_COT/.env
```

## 8. 融合 verified metadata 回 HF raw derived copy

只有通過 title verification 或 GPT title-only adjudication 的非空 abstract 可以融合回 HF raw dataset。融合時不要覆蓋原始檔，也不要覆蓋原本已存在的 abstract；輸出一份新的 derived JSONL。

```bash
python3 scripts/download/merge_verified_metadata_into_hf_raw.py \
  --input-jsonl /Users/xjp/Desktop/Outline_COT/data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/hf_meow_raw_high261.full.jsonl \
  --run-root results/engineering_validation/metadata_download_task_metadata_only/<run_id> \
  --output-jsonl /Users/xjp/Desktop/Outline_COT/data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/hf_meow_raw_high261.with_verified_metadata.jsonl \
  --report-json /Users/xjp/Desktop/Outline_COT/data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/hf_meow_raw_high261.with_verified_metadata.merge_report.json \
  --row-report-jsonl /Users/xjp/Desktop/Outline_COT/data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/hf_meow_raw_high261.with_verified_metadata.merge_rows.jsonl
```

接受條件：

- verifier status 為 `verified_title_year` 或 `verified_title_only`。
- 或 verifier 標成 suspicious/review，但 OpenAI title-only adjudication sidecar 判為 `same`。

merge 完成後必查：

```bash
wc -l \
  /Users/xjp/Desktop/Outline_COT/data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/hf_meow_raw_high261.full.jsonl \
  /Users/xjp/Desktop/Outline_COT/data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/hf_meow_raw_high261.with_verified_metadata.jsonl \
  /Users/xjp/Desktop/Outline_COT/data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/hf_meow_raw_high261.with_verified_metadata.merge_rows.jsonl
```

原始與 derived JSONL 行數必須一致；`merge_rows.jsonl` 中 `action=filled` 的行數必須等於 report 裡的 `filled_new_abstracts`；`final_ref_rows` 必須等於 `original_ref_rows`。若 `key_title_mismatch` 非 0，先人工查核再使用 derived copy。
