#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL="gpt-5.4"
EFFORT="medium"
OUTPUT_ROOT="$ROOT_DIR/results"
RUN_NAME=""
MAX_WAIT_SECS=3600
POLL_SECS=5
FORCE=0
DRY_RUN=0

declare -a PAPER_IDS=()

usage() {
  cat <<'EOF'
Usage:
  bash scripts/run_codex_meow_outline_blind.sh [options] --paper PAPER_ID ...
  bash scripts/run_codex_meow_outline_blind.sh [options] PAPER_ID ...

Options:
  --paper PAPER_ID        Add one paper ID explicitly. Repeatable.
  --model MODEL           Codex model name. Default: gpt-5.4
  --effort LEVEL          Codex reasoning effort. Default: medium
                          Allowed: low, medium, high, xhigh
  --force                 Overwrite existing results/<paper_id>/chatgpt_meow_outline_blind.json.
  --dry-run               Print the Codex command for each paper without executing it.
  --output-root DIR       Output root. Default: results
  --run-name NAME         Write outputs to results/<paper_id>/<run-name>/...
  --max-wait SECONDS      Max wait per paper before terminating codex. Default: 3600
  --poll-seconds N        Polling interval while waiting on codex. Default: 5
  -h, --help              Show this help text.
EOF
}

validate_effort() {
  case "$1" in
    low|medium|high|xhigh) ;;
    *)
      echo "Invalid --effort '$1'. Allowed: low, medium, high, xhigh" >&2
      exit 1
      ;;
  esac
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --paper)
      PAPER_IDS+=("$2")
      shift 2
      ;;
    --model)
      MODEL="$2"
      shift 2
      ;;
    --effort)
      EFFORT="$2"
      shift 2
      ;;
    --force)
      FORCE=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --output-root)
      OUTPUT_ROOT="$2"
      shift 2
      ;;
    --run-name)
      RUN_NAME="$2"
      shift 2
      ;;
    --max-wait)
      MAX_WAIT_SECS="$2"
      shift 2
      ;;
    --poll-seconds)
      POLL_SECS="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      PAPER_IDS+=("$1")
      shift
      ;;
  esac
done

validate_effort "$EFFORT"

if [[ ${#PAPER_IDS[@]} -eq 0 ]]; then
  usage >&2
  exit 1
fi

if ! command -v codex >/dev/null 2>&1; then
  echo "codex CLI is required but was not found on PATH." >&2
  exit 1
fi

TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

wait_for_pid() {
  local pid="$1"
  local start_ts now_ts
  start_ts="$(date +%s)"
  while kill -0 "$pid" 2>/dev/null; do
    now_ts="$(date +%s)"
    if (( now_ts - start_ts >= MAX_WAIT_SECS )); then
      kill "$pid" 2>/dev/null || true
      sleep 1
      if kill -0 "$pid" 2>/dev/null; then
        kill -9 "$pid" 2>/dev/null || true
      fi
      wait "$pid" 2>/dev/null || true
      return 124
    fi
    sleep "$POLL_SECS"
  done
  wait "$pid"
}

render_prompt() {
  local payload_path="$1"
  local prompt_path="$2"

  python3 - "$ROOT_DIR" "$payload_path" "$prompt_path" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])
payload_path = Path(sys.argv[2])
prompt_path = Path(sys.argv[3])

sys.path.insert(0, str(root / "scripts"))
from codex_meow_outline_blind_lib import build_prompt, load_blind_payload

payload = load_blind_payload(payload_path)
prompt = build_prompt(
    payload["paper_id"],
    payload["title"],
    payload["reference_metadata"],
)
prompt_path.write_text(prompt, encoding="utf-8")
PY
}

parse_and_write_output() {
  local raw_path="$1"
  local output_path="$2"

  python3 - "$ROOT_DIR" "$raw_path" "$output_path" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])
raw_path = Path(sys.argv[2])
output_path = Path(sys.argv[3])

sys.path.insert(0, str(root / "scripts"))
from codex_meow_outline_blind_lib import write_normalized_outline

write_normalized_outline(raw_path.read_text(encoding="utf-8"), output_path)
PY
}

for paper_id in "${PAPER_IDS[@]}"; do
  paper_dir="$ROOT_DIR/refs/$paper_id"
  payload_path="$paper_dir/meow_reconstructed_blind.json"
  if [[ -n "$RUN_NAME" ]]; then
    output_dir="$OUTPUT_ROOT/$paper_id/$RUN_NAME"
  else
    output_dir="$OUTPUT_ROOT/$paper_id"
  fi
  output_path="$output_dir/chatgpt_meow_outline_blind.json"
  prompt_path="$TMP_DIR/$paper_id.prompt.txt"
  raw_path="$TMP_DIR/$paper_id.raw.txt"
  exec_log="$TMP_DIR/$paper_id.exec.log"

  if [[ ! -d "$paper_dir" ]]; then
    echo "[fail] $paper_id: missing directory $paper_dir" >&2
    exit 1
  fi
  if [[ ! -f "$payload_path" ]]; then
    echo "[fail] $paper_id: missing payload $payload_path" >&2
    exit 1
  fi
  if [[ -f "$output_path" && "$FORCE" -eq 0 ]]; then
    echo "[skip] $paper_id: $output_path already exists (use --force to overwrite)"
    continue
  fi

  render_prompt "$payload_path" "$prompt_path"

  codex_cmd=(
    codex exec
    --ephemeral
    -C "$paper_dir"
    -m "$MODEL"
    -s read-only
    -c "model_reasoning_effort=\"$EFFORT\""
    -o "$raw_path"
    -
  )

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] $paper_id"
    printf '  '
    printf '%q ' "${codex_cmd[@]}"
    printf '< %q\n' "$prompt_path"
    echo "  output: $output_path"
    continue
  fi

  mkdir -p "$output_dir"
  echo "[run] $paper_id"

  set +e
  "${codex_cmd[@]}" <"$prompt_path" >"$exec_log" 2>&1 &
  codex_pid=$!
  wait_for_pid "$codex_pid"
  status=$?
  set -e

  if [[ "$status" -eq 124 ]]; then
    echo "[fail] $paper_id: codex timed out after ${MAX_WAIT_SECS}s" >&2
    if [[ -f "$exec_log" ]]; then
      tail -n 40 "$exec_log" >&2 || true
    fi
    exit 1
  fi
  if [[ "$status" -ne 0 ]]; then
    echo "[fail] $paper_id: codex exited with status $status" >&2
    if [[ -f "$exec_log" ]]; then
      tail -n 40 "$exec_log" >&2 || true
    fi
    exit 1
  fi
  if [[ ! -f "$raw_path" ]]; then
    echo "[fail] $paper_id: codex did not produce a final response" >&2
    exit 1
  fi

  if ! parse_and_write_output "$raw_path" "$output_path"; then
    echo "[fail] $paper_id: could not parse outline response" >&2
    exit 1
  fi

  echo "[ok] $paper_id -> $output_path"
done
