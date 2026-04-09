#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
MAX_WORKERS="${MAX_WORKERS:-10}"

JUDGE_API_URL="${JUDGE_API_URL:-}"
JUDGE_API_KEY="${JUDGE_API_KEY:-}"
JUDGE_MODEL="${JUDGE_MODEL:-}"
HUMAN_FILE="${HUMAN_FILE:-}"

usage() {
  cat <<EOF
Usage:
  bash scripts/evaluate_pipeline.sh [options] <input_jsonl>

Options:
  --human-file PATH        Optional human outline JSONL for pair rewards / structural distance.
  --judge-api-url URL      Optional judge API URL. Falls back to JUDGE_API_URL.
  --judge-api-key KEY      Optional judge API key. Falls back to JUDGE_API_KEY.
  --judge-model MODEL      Optional judge model. Falls back to JUDGE_MODEL.
  --max-workers N          Worker count for pair rewards and judge evaluation. Default: ${MAX_WORKERS}
  --python BIN             Python executable. Default: ${PYTHON_BIN}
  -h, --help               Show this help text.

Behavior:
  1. Always preprocess the prediction JSONL into judge input.
  2. Always convert predictions into outline JSONL.
  3. Run pair rewards only when --human-file or HUMAN_FILE is provided.
  4. Run LLM judge only when judge API settings are fully provided.
EOF
}

INPUT_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --human-file)
      HUMAN_FILE="$2"
      shift 2
      ;;
    --judge-api-url)
      JUDGE_API_URL="$2"
      shift 2
      ;;
    --judge-api-key)
      JUDGE_API_KEY="$2"
      shift 2
      ;;
    --judge-model)
      JUDGE_MODEL="$2"
      shift 2
      ;;
    --max-workers)
      MAX_WORKERS="$2"
      shift 2
      ;;
    --python)
      PYTHON_BIN="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
    *)
      if [[ -n "$INPUT_FILE" ]]; then
        echo "Only one input file is allowed." >&2
        usage >&2
        exit 1
      fi
      INPUT_FILE="$1"
      shift
      ;;
  esac
done

if [[ -z "$INPUT_FILE" ]]; then
  usage >&2
  exit 1
fi

if [[ ! -f "$INPUT_FILE" ]]; then
  echo "错误: 输入文件 '$INPUT_FILE' 不存在" >&2
  exit 1
fi

if [[ -n "$HUMAN_FILE" && ! -f "$HUMAN_FILE" ]]; then
  echo "错误: 指定的 human outline 文件 '$HUMAN_FILE' 不存在" >&2
  exit 1
fi

JUDGE_FIELDS_SET=0
for value in "$JUDGE_API_URL" "$JUDGE_API_KEY" "$JUDGE_MODEL"; do
  if [[ -n "$value" ]]; then
    JUDGE_FIELDS_SET=$((JUDGE_FIELDS_SET + 1))
  fi
done

if [[ "$JUDGE_FIELDS_SET" -ne 0 && "$JUDGE_FIELDS_SET" -ne 3 ]]; then
  echo "错误: judge 配置必须同时提供 URL / KEY / MODEL，或者全部留空。" >&2
  exit 1
fi

INPUT_DIR="$(cd "$(dirname "$INPUT_FILE")" && pwd)"
INPUT_BASENAME="$(basename "$INPUT_FILE" .jsonl)"

PROCESSED_FILE="$INPUT_DIR/${INPUT_BASENAME}_processed.jsonl"
OUTLINE_FILE="$INPUT_DIR/${INPUT_BASENAME}_outline.jsonl"
REWARDS_FILE="$INPUT_DIR/${INPUT_BASENAME}_vs_human.rewards.jsonl"
EVALUATION_FILE="$INPUT_DIR/${INPUT_BASENAME}_evaluation_results.jsonl"
LOG_FILE="$INPUT_DIR/evaluation_${INPUT_BASENAME}.log"

echo "=========================================="
echo "开始流水化评测"
echo "输入文件: $INPUT_FILE"
echo "输出目录: $INPUT_DIR"
echo "=========================================="

echo "步骤1: 数据预处理..."
"$PYTHON_BIN" "$ROOT_DIR/scripts/generated_preprocessing_new.py" "$INPUT_FILE" "$PROCESSED_FILE"
echo "✓ 预处理完成: $PROCESSED_FILE"

echo "步骤2: 转换为 outline 格式..."
"$PYTHON_BIN" "$ROOT_DIR/scripts/predict_to_outline.py" --input "$INPUT_FILE" --output "$OUTLINE_FILE"
echo "✓ outline 格式转换完成: $OUTLINE_FILE"

if [[ -n "$HUMAN_FILE" ]]; then
  echo "步骤3: 与人类大纲比较..."
  "$PYTHON_BIN" "$ROOT_DIR/scripts/evaluate_pair_rewards.py" \
    --human_file "$HUMAN_FILE" \
    --model_file "$OUTLINE_FILE" \
    --output "$REWARDS_FILE" \
    --max_workers "$MAX_WORKERS"
  echo "✓ 与人类大纲比较完成: $REWARDS_FILE"
else
  echo "步骤3: 跳过 pair rewards；未提供 --human-file / HUMAN_FILE"
fi

if [[ "$JUDGE_FIELDS_SET" -eq 3 ]]; then
  echo "步骤4: LLM 评测..."
  "$PYTHON_BIN" "$ROOT_DIR/scripts/evaluate_llm.py" \
    --input "$PROCESSED_FILE" \
    --output "$EVALUATION_FILE" \
    --judge_api_url "$JUDGE_API_URL" \
    --judge_api_key "$JUDGE_API_KEY" \
    --judge_model "$JUDGE_MODEL" \
    --max_workers "$MAX_WORKERS" \
    --log_file "$LOG_FILE"
  echo "✓ LLM 评测完成: $EVALUATION_FILE"
else
  echo "步骤4: 跳过 LLM judge；未提供完整 judge 配置"
fi

echo "=========================================="
echo "流水化评测完成"
echo "生成文件："
echo "  - 预处理文件: $PROCESSED_FILE"
echo "  - outline 文件: $OUTLINE_FILE"
if [[ -n "$HUMAN_FILE" ]]; then
  echo "  - 人类比较结果: $REWARDS_FILE"
fi
if [[ "$JUDGE_FIELDS_SET" -eq 3 ]]; then
  echo "  - LLM 评测结果: $EVALUATION_FILE"
  echo "  - 评测日志: $LOG_FILE"
fi
echo "=========================================="
