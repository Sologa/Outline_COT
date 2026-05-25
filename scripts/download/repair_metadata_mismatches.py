#!/usr/bin/env python3
"""Redownload metadata rows whose title-pair adjudication did not match.

The script repairs selected rows in-place only after writing full per-paper
JSONL files to local staging and validating row counts. It preserves row order
and all non-selected rows.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import collect_title_abstracts_priority as collector  # noqa: E402


JsonObject = dict[str, Any]
DEFAULT_DECISIONS = {"different", "uncertain"}
DEFAULT_PROVIDER_DELAYS = "semantic_scholar=1.5,crossref=1.0,dblp=1.0,pubmed=0.5,openalex=90.0,arxiv=3.2,ieee=1.0"


class MetadataRepairError(RuntimeError):
    """Raised when a repair would break row identity or artifact integrity."""


class RepairItem:
    __slots__ = ("paper", "index", "key", "openai_decision", "verification_status")

    def __init__(self, *, paper: str, index: int, key: str, openai_decision: str, verification_status: str) -> None:
        self.paper = paper
        self.index = index
        self.key = key
        self.openai_decision = openai_decision
        self.verification_status = verification_status


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_csv_set(raw: str, *, default: set[str]) -> set[str]:
    if not raw:
        return set(default)
    return {part.strip() for part in raw.replace(";", ",").split(",") if part.strip()}


def load_jsonl(path: Path) -> list[JsonObject]:
    rows: list[JsonObject] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {path}:{line_number}: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"Expected JSON object in {path}:{line_number}")
            rows.append(row)
    return rows


def write_jsonl_atomic(path: Path, rows: list[JsonObject]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    temp_path.replace(path)


def count_jsonl_rows(path: Path) -> int:
    return collector.count_jsonl_rows(path)


def validate_jsonl_row_count(path: Path, expected_rows: int, *, context: str) -> None:
    actual = count_jsonl_rows(path)
    if actual != expected_rows:
        raise MetadataRepairError(f"{context}: expected {expected_rows} rows, found {actual}: {path}")


def load_repair_items(path: Path, *, decisions: set[str] | None = None) -> list[RepairItem]:
    decision_filter = decisions if decisions is not None else set(DEFAULT_DECISIONS)
    items: list[RepairItem] = []
    seen: set[tuple[str, int, str]] = set()
    for row in load_jsonl(path):
        decision = collector.normalize_text(row.get("openai_decision")).lower()
        if decision not in decision_filter:
            continue
        paper = collector.normalize_text(row.get("paper"))
        key = collector.normalize_text(row.get("key"))
        index = int(row.get("index") or 0)
        if not paper or not key or index < 1:
            continue
        item_key = (paper, index, key)
        if item_key in seen:
            continue
        seen.add(item_key)
        items.append(
            RepairItem(
                paper=paper,
                index=index,
                key=key,
                openai_decision=decision,
                verification_status=collector.normalize_text(row.get("verification_status")),
            )
        )
    return items


def load_metadata_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"env file does not exist: {path}")
    allowed = {
        "METADATA_API_MAILTO",
        "SEMANTIC_SCHOLAR_API_KEY",
        "S2_API_KEY",
        "OPENALEX_API_KEY",
        "IEEE_API_KEY",
        "IEEE_XPLORE_API_KEY",
    }
    loaded: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip().rstrip("\r")
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export ") :]
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key not in allowed:
                continue
            value = value.strip()
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            loaded[key] = value
            os.environ[key] = value
    return loaded


def repair_one_row(
    *,
    item: RepairItem,
    ref_row: JsonObject,
    current_row: JsonObject,
    providers: list[str],
    fetch_client: collector.ProviderFetchClient,
    min_title_similarity: float,
) -> tuple[RepairItem, JsonObject, JsonObject]:
    repaired, got = collector.resolve_reference(
        dict(ref_row),
        providers=providers,
        fetch_client=fetch_client,
        min_title_similarity=min_title_similarity,
    )
    repaired["key"] = item.key
    repaired["metadata_request_providers"] = providers
    repair_status = "redownloaded_abstract" if got and collector.normalize_text(repaired.get("abstract")) else "redownload_unresolved"
    repaired["_metadata_mismatch_repair"] = {
        "repaired_at": now_utc(),
        "openai_decision": item.openai_decision,
        "verification_status": item.verification_status,
        "previous_title": collector.normalize_text(current_row.get("title")),
        "previous_provider": collector.normalize_text(current_row.get("provider")),
        "previous_provider_id": collector.normalize_text(current_row.get("provider_id")),
        "previous_had_abstract": bool(collector.normalize_text(current_row.get("abstract"))),
        "repair_status": repair_status,
        "min_title_similarity": min_title_similarity,
    }
    detail = {
        "paper": item.paper,
        "index": item.index,
        "key": item.key,
        "openai_decision": item.openai_decision,
        "verification_status": item.verification_status,
        "previous_title": collector.normalize_text(current_row.get("title")),
        "new_title": collector.normalize_text(repaired.get("title")),
        "previous_provider": collector.normalize_text(current_row.get("provider")),
        "new_provider": collector.normalize_text(repaired.get("provider")),
        "new_provider_id": collector.normalize_text(repaired.get("provider_id")),
        "new_title_similarity": repaired.get("title_similarity"),
        "repair_status": repair_status,
        "new_abstract_present": bool(collector.normalize_text(repaired.get("abstract"))),
    }
    return item, repaired, detail


def clear_one_row(
    *,
    item: RepairItem,
    ref_row: JsonObject,
    current_row: JsonObject,
    providers: list[str],
    min_title_similarity: float,
) -> tuple[RepairItem, JsonObject, JsonObject]:
    repaired = dict(ref_row)
    repaired["key"] = item.key
    repaired["abstract"] = ""
    repaired["metadata_source"] = "unresolved"
    repaired["provider"] = ""
    repaired["provider_id"] = ""
    repaired["provider_url"] = ""
    repaired["title_similarity"] = collector.title_similarity(
        collector.normalize_text(ref_row.get("title")),
        collector.normalize_text(repaired.get("title")),
    )
    repaired["metadata_request_providers"] = providers
    repaired["metadata_downloaded_at"] = now_utc()
    repaired["_metadata_mismatch_repair"] = {
        "repaired_at": now_utc(),
        "openai_decision": item.openai_decision,
        "verification_status": item.verification_status,
        "previous_title": collector.normalize_text(current_row.get("title")),
        "previous_provider": collector.normalize_text(current_row.get("provider")),
        "previous_provider_id": collector.normalize_text(current_row.get("provider_id")),
        "previous_had_abstract": bool(collector.normalize_text(current_row.get("abstract"))),
        "repair_status": "forced_unresolved",
        "min_title_similarity": min_title_similarity,
    }
    detail = {
        "paper": item.paper,
        "index": item.index,
        "key": item.key,
        "openai_decision": item.openai_decision,
        "verification_status": item.verification_status,
        "previous_title": collector.normalize_text(current_row.get("title")),
        "new_title": collector.normalize_text(repaired.get("title")),
        "previous_provider": collector.normalize_text(current_row.get("provider")),
        "new_provider": "",
        "new_provider_id": "",
        "new_title_similarity": repaired.get("title_similarity"),
        "repair_status": "forced_unresolved",
        "new_abstract_present": False,
    }
    return item, repaired, detail


def repair_run(
    *,
    run_root: Path,
    repair_items: list[RepairItem],
    staging_root: Path,
    providers: list[str],
    fetch_client: collector.ProviderFetchClient,
    min_title_similarity: float,
    publish: bool,
    max_workers: int = 1,
    clear_only: bool = False,
) -> JsonObject:
    items_by_paper: dict[str, list[RepairItem]] = defaultdict(list)
    for item in repair_items:
        items_by_paper[item.paper].append(item)

    refs_by_paper: dict[str, list[JsonObject]] = {}
    metadata_by_paper: dict[str, list[JsonObject]] = {}
    work: list[tuple[RepairItem, JsonObject, JsonObject]] = []

    for paper, paper_items in sorted(items_by_paper.items()):
        input_path = run_root / "filtered_input" / paper / "reference_oracle.jsonl"
        metadata_path = run_root / paper / "metadata" / "title_abstracts_metadata.jsonl"
        refs = load_jsonl(input_path)
        metadata = load_jsonl(metadata_path)
        if len(refs) != len(metadata):
            raise MetadataRepairError(f"{paper}: row count mismatch input={len(refs)} metadata={len(metadata)}")
        refs_by_paper[paper] = refs
        metadata_by_paper[paper] = metadata

        for item in paper_items:
            idx = item.index - 1
            if idx < 0 or idx >= len(refs):
                raise MetadataRepairError(f"{paper}:{item.index}: index out of range")
            ref_key = collector.normalize_text(refs[idx].get("key"))
            metadata_key = collector.normalize_text(metadata[idx].get("key"))
            if ref_key != item.key or metadata_key != item.key:
                raise MetadataRepairError(
                    f"{paper}:{item.index}: key mismatch repair={item.key} input={ref_key} metadata={metadata_key}"
                )
            work.append((item, refs[idx], metadata[idx]))

    details: list[JsonObject] = []
    if max_workers <= 1:
        for item, ref_row, current_row in work:
            if clear_only:
                repaired_item, repaired, detail = clear_one_row(
                    item=item,
                    ref_row=ref_row,
                    current_row=current_row,
                    providers=providers,
                    min_title_similarity=min_title_similarity,
                )
            else:
                repaired_item, repaired, detail = repair_one_row(
                    item=item,
                    ref_row=ref_row,
                    current_row=current_row,
                    providers=providers,
                    fetch_client=fetch_client,
                    min_title_similarity=min_title_similarity,
                )
            metadata_by_paper[repaired_item.paper][repaired_item.index - 1] = repaired
            details.append(detail)
            print(f"[repair] {repaired_item.paper}:{repaired_item.index} {detail['repair_status']}", flush=True)
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    clear_one_row if clear_only else repair_one_row,
                    item=item,
                    ref_row=ref_row,
                    current_row=current_row,
                    providers=providers,
                    min_title_similarity=min_title_similarity,
                    **({} if clear_only else {"fetch_client": fetch_client}),
                )
                for item, ref_row, current_row in work
            ]
            for future in as_completed(futures):
                repaired_item, repaired, detail = future.result()
                metadata_by_paper[repaired_item.paper][repaired_item.index - 1] = repaired
                details.append(detail)
                print(f"[repair] {repaired_item.paper}:{repaired_item.index} {detail['repair_status']}", flush=True)

    published = 0
    for paper, metadata_rows in sorted(metadata_by_paper.items()):
        expected_rows = len(refs_by_paper[paper])
        staged_path = staging_root / paper / "metadata" / "title_abstracts_metadata.jsonl"
        write_jsonl_atomic(staged_path, metadata_rows)
        validate_jsonl_row_count(staged_path, expected_rows, context=f"{paper} staged repair")

        if publish:
            final_path = run_root / paper / "metadata" / "title_abstracts_metadata.jsonl"
            write_jsonl_atomic(final_path, metadata_rows)
            validate_jsonl_row_count(final_path, expected_rows, context=f"{paper} final repair")
            published += 1

    status_counts = Counter(detail["repair_status"] for detail in details)
    summary: JsonObject = {
        "generated_at": now_utc(),
        "run_root": str(run_root),
        "staging_root": str(staging_root),
        "selected_rows": len(repair_items),
        "processed_rows": len(details),
        "touched_papers": len(items_by_paper),
        "published_papers": published,
        "providers": providers,
        "min_title_similarity": min_title_similarity,
        "status_counts": dict(sorted(status_counts.items())),
        "details": sorted(details, key=lambda row: (row["paper"], row["index"])),
    }
    return summary


def default_staging_root(run_root: Path) -> Path:
    return Path.cwd() / ".local" / "metadata_mismatch_repair" / f"repair_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", required=True, help="Target metadata run root")
    parser.add_argument("--adjudication-jsonl", default="", help="OpenAI title-pair adjudication JSONL")
    parser.add_argument("--staging-root", default="", help="Local staging root for repaired full per-paper JSONL files")
    parser.add_argument("--summary-json", default="", help="Repair summary JSON path")
    parser.add_argument("--details-jsonl", default="", help="Repair detail rows JSONL path")
    parser.add_argument("--decisions", default="different,uncertain", help="OpenAI decisions to redownload")
    parser.add_argument("--providers", default="semantic_scholar,crossref,dblp,pubmed", help="Provider order")
    parser.add_argument("--max-results", type=int, default=10, help="Provider max results per title")
    parser.add_argument("--request-delay", type=float, default=1.0, help="Default provider request delay")
    parser.add_argument("--provider-delays", default=DEFAULT_PROVIDER_DELAYS, help="Provider-specific delays")
    parser.add_argument("--rate-limit-backoff", type=float, default=30.0, help="429 backoff seconds")
    parser.add_argument("--max-workers", type=int, default=4, help="Row-level worker threads")
    parser.add_argument("--min-title-similarity", type=float, default=0.95, help="Strict title threshold for repaired metadata")
    parser.add_argument("--env-file", default="", help="Optional .env with metadata provider API keys")
    parser.add_argument("--dry-run", action="store_true", help="Only report selected rows; do not call providers or write metadata")
    parser.add_argument("--clear-only", action="store_true", help="Do not redownload; force selected rows to unresolved blank metadata")
    parser.add_argument("--no-publish", action="store_true", help="Write staging files but do not publish final metadata")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_workers < 1:
        raise ValueError("--max-workers must be >= 1")
    if args.max_results < 1:
        raise ValueError("--max-results must be >= 1")
    if args.min_title_similarity < 0 or args.min_title_similarity > 1:
        raise ValueError("--min-title-similarity must be between 0 and 1")
    if args.request_delay < 0 or args.rate_limit_backoff < 0:
        raise ValueError("delays/backoff must be non-negative")

    run_root = Path(args.run_root)
    adjudication_path = Path(args.adjudication_jsonl) if args.adjudication_jsonl else run_root / "_verification" / "metadata_title_pair_openai_adjudication.jsonl"
    staging_root = Path(args.staging_root) if args.staging_root else default_staging_root(run_root)
    summary_path = Path(args.summary_json) if args.summary_json else run_root / "_verification" / "metadata_mismatch_redownload_repair_summary.json"
    details_path = Path(args.details_jsonl) if args.details_jsonl else run_root / "_verification" / "metadata_mismatch_redownload_repair_rows.jsonl"

    if args.env_file:
        load_metadata_env_file(Path(args.env_file))

    decisions = parse_csv_set(args.decisions, default=DEFAULT_DECISIONS)
    repair_items = load_repair_items(adjudication_path, decisions=decisions)
    print(f"[repair] selected_rows={len(repair_items)} decisions={','.join(sorted(decisions))}")
    if args.dry_run:
        by_paper = Counter(item.paper for item in repair_items)
        print(f"[repair] dry_run touched_papers={len(by_paper)}")
        for paper, count in sorted(by_paper.items()):
            print(f"[repair] dry_run {paper}: {count}")
        return 0

    providers = collector.parse_provider_order(args.providers)
    provider_delays = collector.parse_provider_delays(args.provider_delays, default_delay=args.request_delay)
    fetch_client = collector.ProviderFetchClient(
        max_results=args.max_results,
        default_delay=args.request_delay,
        provider_delays=provider_delays,
        rate_limit_backoff_seconds=args.rate_limit_backoff,
    )
    summary = repair_run(
        run_root=run_root,
        repair_items=repair_items,
        staging_root=staging_root,
        providers=providers,
        fetch_client=fetch_client,
        min_title_similarity=args.min_title_similarity,
        publish=not args.no_publish,
        max_workers=args.max_workers,
        clear_only=args.clear_only,
    )
    details = summary.pop("details")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_jsonl_atomic(details_path, details)

    print(
        "[repair] "
        f"processed={summary['processed_rows']} touched_papers={summary['touched_papers']} "
        f"published_papers={summary['published_papers']} status_counts={json.dumps(summary['status_counts'], sort_keys=True)}"
    )
    print(f"[repair] summary_json={summary_path}")
    print(f"[repair] details_jsonl={details_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
