#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROMPT_FILE="$ROOT_DIR/prompts/outline_induction_ir_user.txt"
LOG_DIR="$ROOT_DIR/logs/outline_induction_ir"

MODEL="${MODEL:-gpt-5.4}"
EFFORT="${EFFORT:-xhigh}"
SERVICE_TIER="${SERVICE_TIER:-}"
MAX_WAIT_SECS="${MAX_WAIT_SECS:-3600}"
STABLE_SECS="${STABLE_SECS:-45}"
POLL_SECS="${POLL_SECS:-5}"
FORCE=0
DRY_RUN=0

declare -a PAPER_IDS=()
declare -a PROCESSED=()
declare -a SKIPPED=()
declare -a FAILED=()

usage() {
  cat <<'EOF'
Usage:
  bash scripts/run_outline_induction_ir_loop.sh [options] [paper_id ...]

Options:
  --paper PAPER_ID        Add one paper ID explicitly. Repeatable.
  --force                 Overwrite existing refs/<paper_id>/outline_induction_ir.yaml files.
  --dry-run               Print the Codex command for each paper without executing it.
  --model MODEL           Codex model to use. Default: gpt-5.4
  --effort LEVEL          Codex reasoning effort. Default: xhigh
  --service-tier TIER     Optional Codex service tier override. Codex config on this machine accepts `fast` or `flex`.
  --max-wait SECONDS      Max wait per paper before treating Codex as hung. Default: 3600
  --stable-seconds N      Consider output complete after YAML stays unchanged for N seconds. Default: 45
  --poll-seconds N        Polling interval while waiting on Codex. Default: 5
  -h, --help              Show this help text.

Examples:
  bash scripts/run_outline_induction_ir_loop.sh --force 2601.19926
  bash scripts/run_outline_induction_ir_loop.sh --force --paper 2601.19926 --paper 2409.13738
  bash scripts/run_outline_induction_ir_loop.sh --dry-run
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --paper)
      PAPER_IDS+=("$2")
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
    --model)
      MODEL="$2"
      shift 2
      ;;
    --effort)
      EFFORT="$2"
      shift 2
      ;;
    --service-tier)
      SERVICE_TIER="$2"
      shift 2
      ;;
    --max-wait)
      MAX_WAIT_SECS="$2"
      shift 2
      ;;
    --stable-seconds)
      STABLE_SECS="$2"
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

if ! command -v codex >/dev/null 2>&1; then
  echo "codex CLI is required but was not found on PATH." >&2
  exit 1
fi

if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "Prompt file not found: $PROMPT_FILE" >&2
  exit 1
fi

if [[ ${#PAPER_IDS[@]} -eq 0 ]]; then
  mapfile -t PAPER_IDS < <(find "$ROOT_DIR/refs" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort)
fi

mkdir -p "$LOG_DIR"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

render_prompt() {
  local paper_id="$1"
  local prompt_path="$2"
  local inputs_path="$3"

  python3 - "$ROOT_DIR" "$paper_id" "$PROMPT_FILE" "$prompt_path" "$inputs_path" <<'PY'
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
paper_id = sys.argv[2]
prompt_template_path = Path(sys.argv[3])
prompt_path = Path(sys.argv[4])
inputs_path = Path(sys.argv[5])

paper_dir = root / "refs" / paper_id
tex_link = paper_dir / "tex_src"

def unique_paths(items):
    seen = set()
    out = []
    for item in items:
        key = str(item)
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out

def clean_text(text):
    text = text.replace("\n", " ")
    text = re.sub(r"\\url\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\href\{[^}]*\}\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\textit\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\textbf\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\emph\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\[A-Za-z@]+(?:\[[^\]]*\])?", " ", text)
    text = text.replace("{", " ").replace("}", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text

def parse_title_from_tex(tex_path):
    text = tex_path.read_text(errors="ignore")
    m = re.search(r"\\title\{(.+?)\}", text, flags=re.S)
    if not m:
        return None
    return clean_text(m.group(1))

def parse_bbl_sections(bbl_path):
    text = bbl_path.read_text(errors="ignore")
    sections = {}
    order = []
    pattern = re.compile(
        r"\\bibitem(?:\[[^\]]*\])?%\s*\{([^}]+)\}(.*?)(?=(?:\\bibitem(?:\[[^\]]*\])?%\s*\{)|(?:\\end\{thebibliography\}))",
        re.S,
    )
    for key, body in pattern.findall(text):
        key = key.strip()
        order.append(key)
        sections[key] = clean_text(body)
    return order, sections

def parse_bib_entries(bib_path):
    text = bib_path.read_text(errors="ignore")
    entries = {}
    i = 0
    while True:
        m = re.search(r'@([A-Za-z]+)\s*\{\s*([^,\s]+)\s*,', text[i:])
        if not m:
            break
        entry_type = m.group(1).lower()
        key = m.group(2).strip()
        start = i + m.end()
        depth = 1
        j = start
        in_quote = False
        while j < len(text):
            c = text[j]
            prev = text[j - 1] if j > 0 else ""
            if c == '"' and prev != "\\":
                in_quote = not in_quote
            elif not in_quote:
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        break
            j += 1
        body = text[start:j]
        i = j + 1
        fields = {}
        k = 0
        while k < len(body):
            while k < len(body) and body[k] in " \t\r\n,":
                k += 1
            if k >= len(body):
                break
            m2 = re.match(r"([A-Za-z0-9_:-]+)\s*=\s*", body[k:])
            if not m2:
                break
            fname = m2.group(1).lower()
            k += m2.end()
            if k >= len(body):
                break
            if body[k] == "{":
                depth2 = 1
                k += 1
                startv = k
                while k < len(body):
                    if body[k] == "{":
                        depth2 += 1
                    elif body[k] == "}":
                        depth2 -= 1
                        if depth2 == 0:
                            break
                    k += 1
                val = body[startv:k]
                k += 1
            elif body[k] == '"':
                k += 1
                startv = k
                while k < len(body):
                    if body[k] == '"' and body[k - 1] != "\\":
                        break
                    k += 1
                val = body[startv:k]
                k += 1
            else:
                startv = k
                while k < len(body) and body[k] not in ",\n\r":
                    k += 1
                val = body[startv:k]
            fields[fname] = clean_text(val)
        entries[key] = {"type": entry_type, **fields}
    return entries

def load_metadata_jsonl(path):
    data = {}
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            key = obj.get("key")
            if not key:
                continue
            source_metadata = obj.get("source_metadata") or {}
            record = {
                "key": key,
                "title": obj.get("title") or source_metadata.get("title"),
                "abstract": obj.get("abstract") or source_metadata.get("abstract"),
                "year": obj.get("year") or source_metadata.get("year"),
                "venue": source_metadata.get("venue") or source_metadata.get("journal") or source_metadata.get("booktitle"),
                "authors": source_metadata.get("authors") or obj.get("authors"),
            }
            data[key] = {k: clean_text(str(v)) for k, v in record.items() if v not in (None, "")}
    return data

candidate_roots = [paper_dir]
tex_roots = []
if tex_link.exists():
    tex_roots.append(tex_link)
    try:
        tex_roots.append(tex_link.resolve())
        candidate_roots.append(tex_link.resolve().parent)
    except FileNotFoundError:
        pass

candidate_roots = unique_paths(candidate_roots)
tex_roots = [p for p in unique_paths(tex_roots) if p.exists()]

title = None
for root_dir in candidate_roots:
    metadata_json = root_dir / "metadata.json"
    if metadata_json.exists():
        obj = json.loads(metadata_json.read_text())
        title = obj.get("title") or obj.get("meta", {}).get("title")
        if title:
            title = clean_text(title)
            break

if not title:
    tex_candidates = []
    for tex_root in tex_roots:
        tex_candidates.extend(sorted(tex_root.glob("*.tex")))
    for tex_path in unique_paths(tex_candidates):
        title = parse_title_from_tex(tex_path)
        if title:
            break

bbl_candidates = []
bib_candidates = []
for tex_root in tex_roots:
    bbl_candidates.extend(sorted(tex_root.glob("*.bbl")))
    bib_candidates.extend(sorted(tex_root.glob("*.bib")))

bbl_candidates = unique_paths(bbl_candidates)
bib_candidates = unique_paths(bib_candidates)

bbl_keys = []
bbl_sections = {}
for bbl_path in bbl_candidates:
    keys, sections = parse_bbl_sections(bbl_path)
    if keys:
        bbl_keys = keys
        bbl_sections = sections
        break

bib_map = {}
for bib_path in bib_candidates:
    bib_map.update(parse_bib_entries(bib_path))

metadata_map = {}
for root_dir in candidate_roots:
    for name in [
        "metadata/title_abstracts_full_metadata.jsonl",
        "metadata/title_abstracts_metadata-annotated.jsonl",
        "metadata/title_abstracts_metadata.jsonl",
    ]:
        path = root_dir / name
        if path.exists():
            metadata_map.update(load_metadata_jsonl(path))

ref_keys = bbl_keys if bbl_keys else sorted(metadata_map.keys() or bib_map.keys())
references = []
for key in ref_keys:
    record = {"key": key}
    if key in metadata_map:
        record.update(metadata_map[key])
    if key in bib_map:
        fields = bib_map[key]
        field_map = {
            "title": fields.get("title"),
            "abstract": fields.get("abstract"),
            "year": fields.get("year"),
            "venue": fields.get("journal") or fields.get("booktitle") or fields.get("publisher") or fields.get("howpublished"),
            "authors": fields.get("author"),
            "entry_type": fields.get("type"),
        }
        for k, v in field_map.items():
            if v and k not in record:
                record[k] = v
    raw_bbl = bbl_sections.get(key)
    if raw_bbl and "raw_bbl" not in record:
        record["raw_bbl"] = raw_bbl
    references.append(record)

if not title:
    raise SystemExit(f"Could not recover title for {paper_id}")
if not references:
    raise SystemExit(f"Could not recover references for {paper_id}")

prompt_template = prompt_template_path.read_text()
reference_metadata = json.dumps(references, ensure_ascii=False, indent=2)
prompt = (
    prompt_template
    .replace("{paper_id}", paper_id)
    .replace("{title}", title)
    .replace("{reference_metadata}", reference_metadata)
)
prompt_path.write_text(prompt)

inputs = {
    "paper_id": paper_id,
    "title": title,
    "reference_count": len(references),
    "has_bbl": bool(bbl_keys),
    "has_metadata_jsonl": bool(metadata_map),
    "has_bib": bool(bib_map),
}
inputs_path.write_text(json.dumps(inputs, ensure_ascii=False, indent=2))
print(json.dumps(inputs, ensure_ascii=False))
PY
}

summarize_output() {
  local output_file="$1"
  python3 - "$output_file" <<'PY'
import json
import sys
import yaml

path = sys.argv[1]
with open(path) as f:
    data = yaml.safe_load(f)

node_ids = {node["node_id"] for node in data.get("nodes", [])}
ref_map = {}
for node in data.get("nodes", []):
    for ref in node.get("refs_complete", []):
        ref_map.setdefault(ref, []).append(node["node_id"])

ledger = {entry["ref_key"]: entry.get("assigned_to", []) for entry in data.get("ref_assignment_ledger", [])}
mismatch = []
for key, assigned_to in ledger.items():
    if sorted(ref_map.get(key, [])) != sorted(assigned_to):
        mismatch.append(key)
missing = sorted(set(ref_map) - set(ledger))

summary = {
    "top_level_nodes": sum(1 for node in data.get("nodes", []) if node.get("parent") is None),
    "ledger_count": len(data.get("ref_assignment_ledger", [])),
    "unassigned_count": len(data.get("unassigned_refs", [])),
    "missing_in_ledger": len(missing),
    "mismatch_count": len(mismatch),
    "output_keys": sorted(data.keys()),
}
print(json.dumps(summary, ensure_ascii=False))
PY
}

wait_for_output_or_exit() {
  local pid="$1"
  local output_file="$2"
  local log_prefix="$3"
  local start_ts
  local now_ts
  local mtime=0
  local last_mtime=0
  local summary_json=""

  start_ts="$(date +%s)"

  while kill -0 "$pid" 2>/dev/null; do
    now_ts="$(date +%s)"
    if [[ -f "$output_file" ]]; then
      mtime="$(stat -f '%m' "$output_file" 2>/dev/null || echo 0)"
      if [[ "$mtime" -gt "$last_mtime" ]]; then
        last_mtime="$mtime"
      fi
      if summary_json="$(summarize_output "$output_file" 2>"$log_prefix.validate.tmp.err")"; then
        if (( now_ts - last_mtime >= STABLE_SECS )); then
          echo "  output stabilized; stopping lingering codex pid $pid"
          kill "$pid" 2>/dev/null || true
          sleep 1
          if kill -0 "$pid" 2>/dev/null; then
            kill -9 "$pid" 2>/dev/null || true
          fi
          wait "$pid" 2>/dev/null || true
          printf '%s' "$summary_json"
          return 0
        fi
      fi
    fi

    if (( now_ts - start_ts >= MAX_WAIT_SECS )); then
      echo "  timed out after ${MAX_WAIT_SECS}s; terminating codex pid $pid" >&2
      kill "$pid" 2>/dev/null || true
      sleep 1
      if kill -0 "$pid" 2>/dev/null; then
        kill -9 "$pid" 2>/dev/null || true
      fi
      wait "$pid" 2>/dev/null || true
      return 1
    fi

    sleep "$POLL_SECS"
  done

  wait "$pid"
  return $?
}

run_one() {
  local paper_id="$1"
  local paper_dir="$ROOT_DIR/refs/$paper_id"
  local output_file="$paper_dir/outline_induction_ir.yaml"
  local prompt_path="$TMP_DIR/${paper_id}.prompt.txt"
  local inputs_path="$LOG_DIR/${paper_id}.inputs.json"
  local log_prefix="$LOG_DIR/${paper_id}"
  local -a codex_cmd=()
  local codex_pid
  local status
  local inputs_json
  local summary_json

  if [[ ! -d "$paper_dir" ]]; then
    echo "[skip] $paper_id: missing directory $paper_dir"
    SKIPPED+=("$paper_id (missing dir)")
    return 0
  fi

  if [[ -f "$output_file" && "$FORCE" -eq 0 ]]; then
    echo "[skip] $paper_id: $output_file already exists (use --force to overwrite)"
    SKIPPED+=("$paper_id (existing output)")
    return 0
  fi

  echo "[prepare] $paper_id"
  if ! inputs_json="$(render_prompt "$paper_id" "$prompt_path" "$inputs_path" 2>"$log_prefix.prepare.err")"; then
    echo "[fail] $paper_id: could not prepare prompt"
    FAILED+=("$paper_id (prepare)")
    return 0
  fi
  echo "  inputs: $inputs_json"

  codex_cmd=(
    codex exec
    --dangerously-bypass-approvals-and-sandbox
    --ephemeral
    -C "$ROOT_DIR"
    -m "$MODEL"
    -c "model_reasoning_effort=\"$EFFORT\""
    -o "$output_file"
    -
  )
  if [[ -n "$SERVICE_TIER" ]]; then
    codex_cmd+=(-c "service_tier=\"$SERVICE_TIER\"")
  fi

  echo "[run] $paper_id"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '  '
    printf '%q ' "${codex_cmd[@]}"
    printf '< %q\n' "$prompt_path"
    PROCESSED+=("$paper_id (dry-run)")
    return 0
  fi

  set +e
  "${codex_cmd[@]}" <"$prompt_path" >"$log_prefix.exec.log" 2>&1 &
  codex_pid=$!
  if summary_json="$(wait_for_output_or_exit "$codex_pid" "$output_file" "$log_prefix")"; then
    status=0
  else
    status=$?
  fi
  set -e

  if [[ "$status" -ne 0 ]]; then
    echo "[fail] $paper_id"
    FAILED+=("$paper_id")
    return 0
  fi

  if ! summary_json="$(summarize_output "$output_file" 2>"$log_prefix.validate.err")"; then
    echo "[fail] $paper_id: invalid YAML output"
    FAILED+=("$paper_id (yaml)")
    return 0
  fi

  echo "  summary: $summary_json"
  PROCESSED+=("$paper_id")
  return 0
}

for paper_id in "${PAPER_IDS[@]}"; do
  run_one "$paper_id"
done

echo
echo "Processed: ${#PROCESSED[@]}"
if [[ ${#PROCESSED[@]} -gt 0 ]]; then
  for item in "${PROCESSED[@]}"; do
    echo "  - $item"
  done
fi

echo "Skipped: ${#SKIPPED[@]}"
if [[ ${#SKIPPED[@]} -gt 0 ]]; then
  for item in "${SKIPPED[@]}"; do
    echo "  - $item"
  done
fi

echo "Failed: ${#FAILED[@]}"
if [[ ${#FAILED[@]} -gt 0 ]]; then
  for item in "${FAILED[@]}"; do
    echo "  - $item"
  done
fi
