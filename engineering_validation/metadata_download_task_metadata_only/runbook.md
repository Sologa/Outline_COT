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
export SOURCE_ORDER="arxiv,semantic_scholar,openalex,crossref,dblp,pubmed,ieee"
./engineering_validation/metadata_download_task_metadata_only/run_metadata_task.sh
```

- 會先過濾掉已有 abstract，取前 20 筆缺 abstract 的 reference（或更少，取決於 `PAPER_NAME`）。
  - 會透過 API 實際下載/補齊 metadata。
  - `ieee` 參與時未提供 `IEEE_API_KEY` / `IEEE_XPLORE_API_KEY` 會在 `_provider_errors` 留下 skipped reason。
  - `COLLECT_MAX_WORKERS` 可調大到 `2`、`3` 測速；建議先確認 rate limit 再放大。
- 輸出 metadata 位於 `results/engineering_validation/metadata_download_task_metadata_only/.../<paper>/metadata/title_abstracts_metadata.jsonl`

## 2. 擴展到全量（必要時）

```bash
cd /Users/xjp/Desktop/Outline_COT
export LIMIT=
export RUN_COLLECT=true
export COLLECT_SCRIPT=/Users/xjp/Desktop/Outline_COT/scripts/download/collect_title_abstracts_priority.py
export COLLECT_MAX_WORKERS=2
export SOURCE_ORDER="arxiv,semantic_scholar,openalex,crossref,dblp,pubmed,ieee"
./engineering_validation/metadata_download_task_metadata_only/run_metadata_task.sh
```

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
