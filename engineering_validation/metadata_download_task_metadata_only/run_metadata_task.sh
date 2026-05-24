#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

RUN_ID="${RUN_ID:-metadata_only_$(date +%Y%m%d_%H%M%S)}"
INPUT_ROOT="${INPUT_ROOT:-/Users/xjp/Desktop/Outline_COT/data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/hf_meow_raw_high261.full.jsonl}"
BASE_OUTPUT_ROOT="${BASE_OUTPUT_ROOT:-$REPO_ROOT/results/engineering_validation}"
RUN_ROOT="${RUN_ROOT:-${BASE_OUTPUT_ROOT}/metadata_download_task_metadata_only/${RUN_ID}}"
OUTPUT_ROOT="${OUTPUT_ROOT:-$RUN_ROOT}"
FILTER_ROOT="${FILTER_ROOT:-${RUN_ROOT}/filtered_input}"
SUMMARY_PATH="${SUMMARY_PATH:-${RUN_ROOT}/metadata_download_filter_summary.json}"
LOG_ROOT="${LOG_ROOT:-${RUN_ROOT}/logs}"
PAPER_NAME="${PAPER_NAME:-}"
LIMIT="${LIMIT-20}"
RUN_COLLECT="${RUN_COLLECT:-false}"
FILTER_MISSING_ONLY="${FILTER_MISSING_ONLY:-true}"
INCLUDE_ARXIV="${INCLUDE_ARXIV:-true}"
SOURCE_ORDER="${SOURCE_ORDER:-openalex,semantic_scholar,crossref,dblp,pubmed}"
RESUME="${RESUME:-true}"
CHECKPOINT_EVERY="${CHECKPOINT_EVERY:-20}"
INCLUDE_FULL_METADATA="${INCLUDE_FULL_METADATA:-true}"
ARXIV_MAX_RESULTS="${ARXIV_MAX_RESULTS:-5}"
SEMANTIC_MAX_RESULTS="${SEMANTIC_MAX_RESULTS:-5}"
DBLP_MAX_RESULTS="${DBLP_MAX_RESULTS:-5}"
OPENALEX_MAX_RESULTS="${OPENALEX_MAX_RESULTS:-5}"
CROSSREF_MAX_RESULTS="${CROSSREF_MAX_RESULTS:-5}"
ALLOW_FUZZY="${ALLOW_FUZZY:-true}"
MIN_SIMILARITY="${MIN_SIMILARITY:-0.9}"
METADATA_ROOT="${METADATA_ROOT:-$REPO_ROOT/refs}"
COLLECT_SCRIPT="${COLLECT_SCRIPT:-/Users/xjp/Desktop/Outline_COT/scripts/download/collect_title_abstracts_priority.py}"
COLLECT_MAX_RESULTS="${COLLECT_MAX_RESULTS:-5}"
COLLECT_REQUEST_DELAY="${COLLECT_REQUEST_DELAY:-1.0}"
COLLECT_PROVIDER_DELAYS="${COLLECT_PROVIDER_DELAYS:-openalex=1.0,semantic_scholar=1.5,crossref=1.0,dblp=1.0,pubmed=0.5,arxiv=3.2,ieee=1.0}"
COLLECT_RATE_LIMIT_BACKOFF="${COLLECT_RATE_LIMIT_BACKOFF:-30.0}"
COLLECT_MAX_WORKERS="${COLLECT_MAX_WORKERS:-2}"

assert_bool() {
  local name="$1"
  local value="$2"
  local value_lower
  value_lower="$(printf '%s' "$value" | tr '[:upper:]' '[:lower:]')"
  case "$value_lower" in
    1|true|yes|y|0|false|no|n)
      return 0
      ;;
    *)
      echo "[error] ${name} must be a boolean, got: ${value}" >&2
      exit 1
      ;;
  esac
}

assert_int_or_empty() {
  local name="$1"
  local value="$2"
  if [[ -z "$value" ]]; then
    return 0
  fi
  if ! [[ "$value" =~ ^[0-9]+$ ]]; then
    echo "[error] ${name} must be empty or non-negative integer, got: ${value}" >&2
    exit 1
  fi
}

assert_bool FILTER_MISSING_ONLY "$FILTER_MISSING_ONLY"
assert_bool INCLUDE_ARXIV "$INCLUDE_ARXIV"
assert_bool RESUME "$RESUME"
assert_bool RUN_COLLECT "$RUN_COLLECT"
assert_bool INCLUDE_FULL_METADATA "$INCLUDE_FULL_METADATA"
assert_bool ALLOW_FUZZY "$ALLOW_FUZZY"
assert_int_or_empty LIMIT "$LIMIT"
assert_int_or_empty CHECKPOINT_EVERY "$CHECKPOINT_EVERY"
assert_int_or_empty COLLECT_MAX_RESULTS "$COLLECT_MAX_RESULTS"
assert_int_or_empty COLLECT_MAX_WORKERS "$COLLECT_MAX_WORKERS"
if (( COLLECT_MAX_WORKERS < 1 )); then
  echo "[error] COLLECT_MAX_WORKERS must be >= 1, got: ${COLLECT_MAX_WORKERS}" >&2
  exit 1
fi

mkdir -p "$RUN_ROOT"
mkdir -p "$OUTPUT_ROOT"
mkdir -p "$FILTER_ROOT"
mkdir -p "$LOG_ROOT"

LOG_PATH="${LOG_ROOT}/${RUN_ID}.log"

{
  echo "[run] $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "[run] repo_root=$REPO_ROOT"
  echo "[run] run_id=$RUN_ID"
  echo "[run] input_root=$INPUT_ROOT"
  echo "[run] run_root=$RUN_ROOT"
  echo "[run] filter_root=$FILTER_ROOT"
  echo "[run] output_root=$OUTPUT_ROOT"
  echo "[run] summary_path=$SUMMARY_PATH"
  echo "[run] paper_name=${PAPER_NAME:-<all>}"
  echo "[run] limit=${LIMIT:-<all>}"
  echo "[run] filter_missing_only=$FILTER_MISSING_ONLY"
  echo "[run] run_collect=$RUN_COLLECT"
  echo "[run] include_arxiv=$INCLUDE_ARXIV"
echo "[run] source_order=$SOURCE_ORDER"
echo "[run] collect_max_results=$COLLECT_MAX_RESULTS"
echo "[run] collect_request_delay=$COLLECT_REQUEST_DELAY"
echo "[run] collect_provider_delays=$COLLECT_PROVIDER_DELAYS"
echo "[run] collect_rate_limit_backoff=$COLLECT_RATE_LIMIT_BACKOFF"
echo "[run] collect_max_workers=$COLLECT_MAX_WORKERS"
  echo "[run] resume=$RESUME"
  echo "[run] checkpoint_every=$CHECKPOINT_EVERY"
  echo "[run] include_full_metadata=$INCLUDE_FULL_METADATA"
  echo "[run] allow_fuzzy=$ALLOW_FUZZY"
  echo "[run] min_similarity=$MIN_SIMILARITY"
  echo "[run] collector_script=$COLLECT_SCRIPT"
} | tee "$LOG_PATH"

if [[ -d "$INPUT_ROOT" ]]; then
  echo "[warn] Directory mode is legacy input (reference_oracle dirs)." | tee -a "$LOG_PATH"
  if [[ -n "$LIMIT" ]]; then
    echo "[warn] LIMIT is ignored in directory mode." | tee -a "$LOG_PATH"
  fi
  FILTERED_COUNT="$(python3 - "$INPUT_ROOT" "$METADATA_ROOT" "$FILTER_ROOT" "$PAPER_NAME" "$FILTER_MISSING_ONLY" "$SUMMARY_PATH" <<'PY'
import json
from typing import Optional
import sys
from pathlib import Path


def is_bool_true(raw: str) -> bool:
    return str(raw).strip().lower() in {"1", "true", "yes", "y"}


def abstract_present(value: object) -> bool:
    if not isinstance(value, str):
        return False
    return bool(value.strip())


def load_entries(path: Path) -> list[dict]:
    entries: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            entries.append(json.loads(line))
    return entries


def metadata_status(metadata_path: Path) -> tuple[dict[str, bool], int]:
    known = 0
    missing_map: dict[str, bool] = {}
    if not metadata_path.exists():
        return missing_map, known

    with metadata_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            key = str(record.get("key", "")).strip()
            if not key:
                continue
            known += 1
            missing_map[key] = not abstract_present(record.get("abstract"))
    return missing_map, known


def main() -> int:
    input_root = Path(sys.argv[1])
    metadata_root = Path(sys.argv[2])
    filter_root = Path(sys.argv[3])
    paper_name = sys.argv[4].strip()
    filter_missing_only = is_bool_true(sys.argv[5])
    summary_path = Path(sys.argv[6])

    source_dirs = sorted(
        path for path in input_root.iterdir() if path.is_dir() and path.name != "__pycache__"
    )
    if paper_name:
        source_dirs = [input_root / paper_name]

    source_rows = 0
    selected_rows = 0
    paper_reports = []

    for paper_dir in source_dirs:
        if paper_name and not paper_dir.exists():
            raise FileNotFoundError(f"reference_oracle folder not found: {paper_dir}")
        if not paper_dir.is_dir():
            continue

        oracle_path = paper_dir / "reference_oracle.jsonl"
        if not oracle_path.exists():
            raise FileNotFoundError(f"reference_oracle not found: {oracle_path}")

        metadata_path = metadata_root / paper_dir.name / "metadata" / "title_abstracts_metadata.jsonl"
        missing_map, known = metadata_status(metadata_path)

        entries = load_entries(oracle_path)
        selected = 0
        missing_only_count = sum(1 for m in missing_map.values() if m) if filter_missing_only else 0

        output_dir = filter_root / paper_dir.name
        output_dir.mkdir(parents=True, exist_ok=True)
        output_oracle = output_dir / "reference_oracle.jsonl"

        with output_oracle.open("w", encoding="utf-8") as handle:
            for entry in entries:
                key = str(entry.get("key", "")).strip()
                if not key:
                    continue

                source_rows += 1
                if not filter_missing_only:
                    need_fill = True
                elif not metadata_path.exists():
                    need_fill = True
                else:
                    need_fill = missing_map.get(key, True)

                if not need_fill:
                    continue

                selected += 1
                selected_rows += 1
                handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

        paper_reports.append(
            {
                "paper": paper_dir.name,
                "source_rows": len(entries),
                "selected_rows": selected,
                "metadata_known_rows": known,
                "metadata_missing_rows": missing_only_count if filter_missing_only else 0,
            }
        )

    summary = {
        "run_mode": "legacy_reference_oracle_dir",
        "input_root": str(input_root),
        "metadata_root": str(metadata_root),
        "filter_root": str(filter_root),
        "filter_missing_only": filter_missing_only,
        "paper_name": paper_name or None,
        "source_rows": source_rows,
        "selected_rows": selected_rows,
        "papers": paper_reports,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(selected_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY
)"
elif [[ -f "$INPUT_ROOT" ]]; then
  echo "[run] input_root is a jsonl file (hf raw mode)" | tee -a "$LOG_PATH"
  FILTERED_COUNT="$(python3 - "$INPUT_ROOT" "$FILTER_ROOT" "$PAPER_NAME" "$FILTER_MISSING_ONLY" "$LIMIT" "$INCLUDE_FULL_METADATA" "$METADATA_ROOT" "$SUMMARY_PATH" <<'PY'
import json
from typing import Optional
import sys
from pathlib import Path


def is_bool_true(raw: str) -> bool:
    return str(raw).strip().lower() in {"1", "true", "yes", "y"}


def abstract_present(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def parse_limit(raw: str) -> Optional[int]:
    raw = raw.strip()
    if not raw:
        return None
    value = int(raw)
    if value < 0:
        raise ValueError("limit must be non-negative")
    return value


def infer_paper_id(record: dict) -> str:
    for key in ("paper_id", "arxiv_id", "slug", "id", "paper"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def load_metadata_status(metadata_path: Path) -> dict[str, bool]:
    missing: dict[str, bool] = {}
    if not metadata_path.exists():
        return missing

    with metadata_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            key = str(rec.get("key", "")).strip()
            if not key:
                continue
            missing[key] = not abstract_present(rec.get("abstract"))
    return missing


def main() -> int:
    input_root = Path(sys.argv[1])
    filter_root = Path(sys.argv[2])
    paper_name = sys.argv[3].strip()
    filter_missing_only = is_bool_true(sys.argv[4])
    limit = parse_limit(sys.argv[5])
    include_full_metadata = is_bool_true(sys.argv[6])
    metadata_root = Path(sys.argv[7])
    summary_path = Path(sys.argv[8])

    source_rows = 0
    selected_rows = 0
    # LIMIT counts selected refs that need collection after missing/abstract filtering.
    processed_refs = 0
    paper_reports: list[dict[str, int]] = []

    with input_root.open("r", encoding="utf-8") as handle:
        reached_limit = False
        for line in handle:
            if reached_limit:
                break

            line = line.strip()
            if not line:
                continue

            record = json.loads(line)
            paper_id = infer_paper_id(record)
            if not paper_id:
                continue

            if paper_name and paper_id != paper_name:
                continue

            refs = record.get("raw", {}).get("ref_meta")
            if not isinstance(refs, list):
                refs = record.get("ref_meta")
            if not isinstance(refs, list):
                refs = []

            if not refs:
                continue

            metadata_missing = {}
            if include_full_metadata:
                metadata_file = metadata_root / paper_id / "metadata" / "title_abstracts_metadata.jsonl"
                metadata_missing = load_metadata_status(metadata_file)

            selected_refs = []
            paper_source_rows = 0
            paper_selected_rows = 0
            for ref in refs:
                key = str(ref.get("key", "")).strip()
                if not key:
                    continue

                source_rows += 1
                paper_source_rows += 1

                if not filter_missing_only:
                    need_fill = True
                elif metadata_missing:
                    need_fill = metadata_missing.get(key, True)
                    if need_fill is None:
                        need_fill = True
                else:
                    need_fill = not abstract_present(ref.get("abstract"))

                if not need_fill:
                    continue

                if limit is not None and processed_refs >= limit:
                    reached_limit = True
                    break

                processed_refs += 1
                selected_refs.append(ref)
                paper_selected_rows += 1
                selected_rows += 1

            output_dir = filter_root / paper_id
            output_dir.mkdir(parents=True, exist_ok=True)
            output_oracle = output_dir / "reference_oracle.jsonl"
            with output_oracle.open("w", encoding="utf-8") as out:
                for entry in selected_refs:
                    out.write(json.dumps(entry, ensure_ascii=False) + "\n")

            paper_reports.append(
                {
                    "paper": paper_id,
                    "source_rows": paper_source_rows,
                    "selected_rows": paper_selected_rows,
                    "metadata_known_rows": len(metadata_missing),
                    "metadata_missing_rows": sum(1 for value in metadata_missing.values() if value),
                }
            )

            if reached_limit:
                break

    summary = {
        "run_mode": "hf_raw_full_jsonl",
        "input_root": str(input_root),
        "input_type": "hf_meow_raw_taxonomy_high261_full_jsonl",
        "filter_root": str(filter_root),
        "filter_missing_only": filter_missing_only,
        "include_full_metadata": include_full_metadata,
        "paper_name": paper_name or None,
        "limit": limit,
        "source_rows": source_rows,
        "selected_rows": selected_rows,
        "papers": paper_reports,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(selected_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY
)"
else
  echo "[error] INPUT_ROOT must be a file (hf jsonl) or dir (legacy mode): $INPUT_ROOT" | tee -a "$LOG_PATH"
  exit 1
fi

echo "[filter] summary_path=$SUMMARY_PATH" | tee -a "$LOG_PATH"
if [[ -f "$SUMMARY_PATH" ]]; then
  python3 - "$SUMMARY_PATH" <<'PY' | tee -a "$LOG_PATH"
import json
from pathlib import Path
import sys

summary_path = Path(sys.argv[1])
summary = json.loads(summary_path.read_text(encoding="utf-8"))
print(
    f"[filter] papers={len(summary.get('papers', []))} "
    f"source_rows={summary.get('source_rows', 0)} selected_rows={summary.get('selected_rows', 0)}"
)
for item in summary.get("papers", []):
    print(
        f"[filter] {item['paper']}: source={item['source_rows']} "
        f"selected={item['selected_rows']} metadata_known={item.get('metadata_known_rows', 0)} "
        f"metadata_missing={item.get('metadata_missing_rows', 0)}"
    )
PY
fi

if ! [[ "$FILTERED_COUNT" =~ ^[0-9]+$ ]]; then
  echo "[error] cannot parse filtered count, got: $FILTERED_COUNT" | tee -a "$LOG_PATH"
  exit 1
fi

if [[ "$FILTERED_COUNT" -eq 0 ]]; then
  echo "[done] no rows need metadata filling, collector skipped" | tee -a "$LOG_PATH"
  echo "[done] output_root=$OUTPUT_ROOT" | tee -a "$LOG_PATH"
  exit 0
fi

RUN_COLLECT_LOWER="$(printf '%s' "$RUN_COLLECT" | tr '[:upper:]' '[:lower:]')"
if [[ "$RUN_COLLECT_LOWER" != "true" && "$RUN_COLLECT_LOWER" != "1" && "$RUN_COLLECT_LOWER" != "yes" && "$RUN_COLLECT_LOWER" != "y" ]]; then
  echo "[done] filter phase complete. set RUN_COLLECT=true to launch collector." | tee -a "$LOG_PATH"
  echo "[done] output_root=$OUTPUT_ROOT" | tee -a "$LOG_PATH"
  echo "[done] filtered_count=$FILTERED_COUNT" | tee -a "$LOG_PATH"
  exit 0
fi

if [[ ! -f "$COLLECT_SCRIPT" ]]; then
  echo "[error] collector script not found: $COLLECT_SCRIPT" | tee -a "$LOG_PATH"
  exit 2
fi

COLLECT_ARGS=(
  --input-root "$FILTER_ROOT"
  --output-root "$OUTPUT_ROOT"
)

if [[ -n "$PAPER_NAME" ]]; then
  COLLECT_ARGS+=(--paper-name "$PAPER_NAME")
fi

if [[ "${INCLUDE_FULL_METADATA}" == "true" || "${INCLUDE_FULL_METADATA}" == "1" || "${INCLUDE_FULL_METADATA}" == "yes" || "${INCLUDE_FULL_METADATA}" == "y" ]]; then
  COLLECT_ARGS+=(--metadata-root "$METADATA_ROOT")
fi
COLLECT_ARGS+=(
  --providers "$SOURCE_ORDER"
  --max-results "$COLLECT_MAX_RESULTS"
  --request-delay "$COLLECT_REQUEST_DELAY"
  --provider-delays "$COLLECT_PROVIDER_DELAYS"
  --rate-limit-backoff "$COLLECT_RATE_LIMIT_BACKOFF"
  --max-workers "$COLLECT_MAX_WORKERS"
)

RESUME_LOWER="$(printf '%s' "$RESUME" | tr '[:upper:]' '[:lower:]')"
if [[ "$RESUME_LOWER" == "true" || "$RESUME_LOWER" == "1" || "$RESUME_LOWER" == "yes" || "$RESUME_LOWER" == "y" ]]; then
  COLLECT_ARGS+=(--resume)
fi

python3 "$COLLECT_SCRIPT" "${COLLECT_ARGS[@]}" | tee -a "$LOG_PATH"

echo "[done] run complete" | tee -a "$LOG_PATH"
echo "[done] output_root=$OUTPUT_ROOT" | tee -a "$LOG_PATH"
