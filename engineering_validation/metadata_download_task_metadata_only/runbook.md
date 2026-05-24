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
export SOURCE_ORDER="openalex,semantic_scholar,crossref"
export RESUME=false
export COLLECT_RATE_LIMIT_BACKOFF=10
./engineering_validation/metadata_download_task_metadata_only/run_metadata_task.sh
```

- 會先過濾掉已有 abstract，取前 20 筆缺 abstract 的 reference（或更少，取決於 `PAPER_NAME`）。
  - 會透過 API 實際下載/補齊 metadata。
  - `COLLECT_MAX_WORKERS=2` 會以 paper 為單位並行，但 provider request 會共用 throttle。
  - 若要進入 OpenAlex/Crossref polite pool，設定 `METADATA_API_MAILTO`。
  - 若有 Semantic Scholar key，設定 `SEMANTIC_SCHOLAR_API_KEY` 或 `S2_API_KEY`。
- 輸出 metadata 位於 `results/engineering_validation/metadata_download_task_metadata_only/.../<paper>/metadata/title_abstracts_metadata.jsonl`

## 2. 擴展到全量（必要時）

```bash
cd /Users/xjp/Desktop/Outline_COT
export LIMIT=
export RUN_COLLECT=true
export COLLECT_SCRIPT=/Users/xjp/Desktop/Outline_COT/scripts/download/collect_title_abstracts_priority.py
export COLLECT_MAX_WORKERS=2
export SOURCE_ORDER="openalex,semantic_scholar,crossref,dblp,pubmed"
export RESUME=true
./engineering_validation/metadata_download_task_metadata_only/run_metadata_task.sh
```

預設 provider delays：

```bash
export COLLECT_PROVIDER_DELAYS="openalex=1.0,semantic_scholar=1.5,crossref=1.0,dblp=1.0,pubmed=0.5,arxiv=3.2,ieee=1.0"
export COLLECT_RATE_LIMIT_BACKOFF=30
```

`arxiv` 與 `ieee` 不在 full-run 預設 order；只在明確需要時加回 `SOURCE_ORDER`。

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
