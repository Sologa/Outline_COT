#!/usr/bin/env python3
import argparse
import asyncio
import json
import os
import re
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

REFS_DIR = ROOT_DIR / "refs"
RESULTS_DIR = ROOT_DIR / "results"
SYSTEM_PROMPT_PATH = ROOT_DIR / "prompts" / "meow_llm_judge_6d_source_system.txt"
USER_PROMPT_PATH = ROOT_DIR / "prompts" / "meow_llm_judge_6d_source_user.txt"
BLIND_FILENAME = "chatgpt_meow_outline_blind.json"
REFERENCE_FILENAME = "outline.json"
RESULT_FILENAME = "chatgpt_meow_outline_blind.eval.json"
DEBUG_FILENAME = "chatgpt_meow_outline_blind.eval.debug.json"
SUMMARY_FILENAME = "chatgpt_meow_outline_blind.eval.summary.json"
SCORE_KEYS = [
    "结构_信息快速定位",
    "结构_详略得当",
    "内容_章节互斥性",
    "内容_逻辑深度",
    "内容_学术价值",
    "语用_描述性与简洁性",
]


def discover_target_papers(repo_root: Path = ROOT_DIR) -> List[str]:
    papers = set()
    refs_dir = repo_root / "refs"
    results_dir = repo_root / "results"
    papers.update(path.parent.name for path in refs_dir.glob(f"*/{BLIND_FILENAME}"))
    papers.update(path.parent.name for path in results_dir.glob(f"*/{BLIND_FILENAME}"))
    papers.update(path.parent.parent.name for path in results_dir.glob(f"*/*/{BLIND_FILENAME}"))
    return sorted(papers)


def load_json_file(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def ensure_outline_list(data: Any, label: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    debug: Dict[str, Any] = {
        "label": label,
        "input_type": type(data).__name__,
        "warnings": [],
        "items_total": 0,
        "items_kept": 0,
        "items_dropped": 0,
        "malformed_indices": [],
        "missing_keys": [],
    }
    if not isinstance(data, list):
        raise ValueError(f"{label} must be a list, got {type(data).__name__}")

    sanitized: List[Dict[str, Any]] = []
    debug["items_total"] = len(data)
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            debug["items_dropped"] += 1
            debug["malformed_indices"].append(idx)
            debug["warnings"].append(f"{label}[{idx}] is not a dict")
            continue

        missing = [key for key in ("level", "numbering", "title", "ref") if key not in item]
        if missing:
            debug["missing_keys"].append({"index": idx, "keys": missing})

        try:
            level = int(item.get("level", 1))
        except Exception:
            level = 1
            debug["warnings"].append(f"{label}[{idx}] level fallback to 1")

        numbering = str(item.get("numbering", "") or "")
        title = str(item.get("title", "") or "")
        refs = item.get("ref", [])
        if refs is None:
            refs = []
        if not isinstance(refs, list):
            refs = [str(refs)]
            debug["warnings"].append(f"{label}[{idx}] ref coerced to list")

        sanitized.append(
            {
                "level": max(level, 1),
                "numbering": numbering,
                "title": title,
                "ref": refs,
            }
        )

    debug["items_kept"] = len(sanitized)
    debug["items_dropped"] = debug["items_total"] - debug["items_kept"]
    return sanitized, debug


def render_outline_text(outline_items: Sequence[Dict[str, Any]]) -> str:
    if not outline_items:
        return ""

    lines: List[str] = []
    for item in outline_items:
        try:
            level = int(item.get("level", 1))
        except Exception:
            level = 1
        numbering = str(item.get("numbering", "") or "")
        title = str(item.get("title", "") or "")
        indent = "  " * max(level - 1, 0)
        if numbering:
            lines.append(f"{indent}{numbering}. {title}")
        else:
            lines.append(f"{indent}{title}")
    return "\n".join(lines)


def load_prompt_templates(repo_root: Path = ROOT_DIR) -> Tuple[str, str]:
    system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()
    user_prompt = USER_PROMPT_PATH.read_text(encoding="utf-8").strip()
    return system_prompt, user_prompt


def build_judge_messages(repo_root: Path, topic: str, outline_text: str) -> List[Dict[str, str]]:
    system_prompt, user_prompt = load_prompt_templates(repo_root)
    rendered_user = user_prompt.replace("{topic}", topic).replace("{outline}", outline_text)
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": rendered_user},
    ]


def _extract_scores_with_regex(raw_response: str) -> Optional[Dict[str, Any]]:
    cleaned = re.sub(r"[\n\r\t]+", " ", raw_response)
    scores: Dict[str, float] = {}
    for key in SCORE_KEYS:
        match = re.search(rf'"{re.escape(key)}"\s*:\s*([0-9]+(?:\.[0-9]+)?)', cleaned)
        if match:
            scores[key] = float(match.group(1))
    if len(scores) < 4:
        return None
    evaluation_match = re.search(r'"评价"\s*:\s*"((?:[^"\\]|\\.)*)"', cleaned)
    evaluation = evaluation_match.group(1) if evaluation_match else "评价内容提取失败"
    result: Dict[str, Any] = {"评价": evaluation}
    result.update(scores)
    return result


def _extract_scores_from_evaluation_text(evaluation_text: str) -> Dict[str, float]:
    scores: Dict[str, float] = {}
    for index, key in enumerate(SCORE_KEYS):
        start = evaluation_text.find(key)
        if start < 0:
            continue

        end = len(evaluation_text)
        for other_key in SCORE_KEYS[index + 1 :]:
            other_pos = evaluation_text.find(other_key, start + len(key))
            if other_pos >= 0:
                end = min(end, other_pos)
        segment = evaluation_text[start:end]
        matches = re.findall(r"([0-9]+(?:\.[0-9]+)?)\s*分", segment)
        if matches:
            scores[key] = float(matches[-1])
    return scores


def parse_judge_response(raw_response: str) -> Dict[str, Any]:
    candidate = raw_response.strip()
    candidate = re.sub(r"```json\s*", "", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"\s*```", "", candidate)
    if not candidate.startswith("{"):
        candidate = "{" + candidate
    if not candidate.endswith("}"):
        candidate = candidate + "}"

    attempts = [candidate]
    attempts.append(re.sub(r"(?<!\\)\n", "\\n", candidate))
    attempts.append(re.sub(r"[\n\r\t]+", " ", candidate))

    for attempt in attempts:
        try:
            parsed = json.loads(attempt)
            if isinstance(parsed, list):
                if not parsed:
                    raise ValueError("Empty JSON array response")
                parsed = parsed[0]
            if not isinstance(parsed, dict):
                raise ValueError(f"Expected dict response, got {type(parsed).__name__}")
            evaluation_text = str(parsed.get("评价", "无评价"))
            recovered_scores = _extract_scores_from_evaluation_text(evaluation_text)
            result: Dict[str, Any] = {"评价": evaluation_text}
            parsed_scores = 0
            for key in SCORE_KEYS:
                if key in parsed:
                    result[key] = float(parsed[key])
                    parsed_scores += 1
                elif key in recovered_scores:
                    result[key] = float(recovered_scores[key])
            if parsed_scores + len(recovered_scores) < 4:
                raise ValueError("Judge response is missing recoverable numeric scores")
            for key in SCORE_KEYS:
                if key not in result:
                    result[key] = 0.0
            return result
        except Exception:
            continue

    recovered = _extract_scores_with_regex(candidate)
    if recovered is not None:
        result = {"评价": recovered.get("评价", "无评价")}
        for key in SCORE_KEYS:
            result[key] = float(recovered.get(key, 0))
        return result

    raise ValueError("Failed to parse judge response as expected JSON payload")


def compute_structural_distance_debug(
    reference_sections: Sequence[Dict[str, Any]],
    source_sections: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    try:
        from combine_scores import _build_shape_tree_from_sections, compute_shape_and_reward
        from zss import simple_distance
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency for structural distance. Install required packages first, e.g. "
            "`python3 -m pip install openai zss tqdm`."
        ) from exc

    def count_nodes(node: Any) -> int:
        total = 1
        for child in node.children:
            total += count_nodes(child)
        return total

    reference_tree = _build_shape_tree_from_sections(list(reference_sections))
    source_tree = _build_shape_tree_from_sections(list(source_sections))
    raw_edit_operations = float(simple_distance(reference_tree, source_tree))
    shape_distance, _ = compute_shape_and_reward(list(reference_sections), list(source_sections))
    reference_node_count = count_nodes(reference_tree)
    source_node_count = count_nodes(source_tree)
    denominator = max(reference_node_count, source_node_count) if max(reference_node_count, source_node_count) > 0 else 1
    return {
        "shape_distance": float(shape_distance),
        "raw_edit_operations": raw_edit_operations,
        "reference_node_count": reference_node_count,
        "source_node_count": source_node_count,
        "normalization_denominator": denominator,
    }


def write_json(path: Path, payload: Dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def write_artifacts(paper_dir: Path, result: Dict[str, Any], debug: Dict[str, Any]) -> Tuple[Path, Path]:
    result_path = write_json(paper_dir / RESULT_FILENAME, result)
    debug_path = write_json(paper_dir / DEBUG_FILENAME, debug)
    return result_path, debug_path


def build_async_client(api_key: str, timeout: int, base_url: Optional[str]) -> Any:
    try:
        from openai import AsyncOpenAI
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency 'openai'. Install it before running LLM judge evaluation: "
            "`python3 -m pip install openai`."
        ) from exc
    kwargs: Dict[str, Any] = {"api_key": api_key, "timeout": timeout}
    if base_url:
        kwargs["base_url"] = base_url
    return AsyncOpenAI(**kwargs)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_paper_paths(repo_root: Path, paper_id: str) -> Dict[str, Path]:
    paper_dir = repo_root / "refs" / paper_id
    return {
        "paper_dir": paper_dir,
        "source_outline_path": paper_dir / BLIND_FILENAME,
        "reference_outline_path": paper_dir / REFERENCE_FILENAME,
        "result_path": paper_dir / RESULT_FILENAME,
        "debug_path": paper_dir / DEBUG_FILENAME,
    }


def resolve_eval_target(
    *,
    repo_root: Path,
    paper_id: str,
    results_root: Path,
    run_name: Optional[str] = None,
    source_outline: Optional[Path] = None,
    reference_outline: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> Dict[str, Path]:
    refs_paper_dir = repo_root / "refs" / paper_id
    results_paper_dir = results_root / paper_id

    if source_outline is not None:
        source_path = Path(source_outline)
    elif run_name:
        source_path = results_paper_dir / run_name / BLIND_FILENAME
    else:
        flat_results_source = results_paper_dir / BLIND_FILENAME
        refs_source = refs_paper_dir / BLIND_FILENAME
        if flat_results_source.exists():
            source_path = flat_results_source
        elif refs_source.exists():
            source_path = refs_source
        else:
            source_path = flat_results_source

    if reference_outline is not None:
        reference_path = Path(reference_outline)
    else:
        reference_path = refs_paper_dir / REFERENCE_FILENAME

    if output_dir is not None:
        resolved_output_dir = Path(output_dir)
    elif run_name:
        resolved_output_dir = results_paper_dir / run_name
    elif results_root in source_path.parents:
        resolved_output_dir = source_path.parent
    else:
        resolved_output_dir = results_paper_dir / "legacy_eval"

    return {
        "paper_id": paper_id,
        "source_outline_path": source_path,
        "reference_outline_path": reference_path,
        "output_dir": resolved_output_dir,
        "result_path": resolved_output_dir / RESULT_FILENAME,
        "debug_path": resolved_output_dir / DEBUG_FILENAME,
    }


def resolve_summary_path(
    *,
    repo_root: Path,
    results_root: Path,
    paper_ids: Sequence[str],
    output_dirs: Sequence[Path],
    run_name: Optional[str],
    explicit_summary_path: Optional[Path],
) -> Path:
    if explicit_summary_path is not None:
        return Path(explicit_summary_path)
    if run_name:
        return results_root / "_summaries" / run_name / SUMMARY_FILENAME
    unique_output_dirs = {Path(path) for path in output_dirs}
    if len(unique_output_dirs) == 1:
        return next(iter(unique_output_dirs)) / SUMMARY_FILENAME
    if len(paper_ids) == 1:
        return results_root / paper_ids[0] / SUMMARY_FILENAME
    return results_root / "_summaries" / SUMMARY_FILENAME


async def run_judge_with_retries(
    *,
    client: Any,
    model: str,
    messages: List[Dict[str, str]],
    semaphore: asyncio.Semaphore,
    timeout: int,
    max_retries: int,
) -> Dict[str, Any]:
    debug: Dict[str, Any] = {"attempts": []}
    last_error = "Judge did not return a successful response"
    for attempt in range(1, max_retries + 1):
        started = time.perf_counter()
        attempt_debug: Dict[str, Any] = {"attempt": attempt}
        try:
            async with semaphore:
                response = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=model,
                        messages=messages,
                    ),
                    timeout=timeout,
                )
            raw_response = (response.choices[0].message.content or "").strip()
            attempt_debug["latency_seconds"] = round(time.perf_counter() - started, 4)
            attempt_debug["raw_response"] = raw_response
            parsed = parse_judge_response(raw_response)
            attempt_debug["parse_status"] = "success"
            debug["attempts"].append(attempt_debug)
            return {
                "success": True,
                "raw_response": raw_response,
                "parsed": parsed,
                "debug": debug,
            }
        except Exception as exc:
            last_error = str(exc)
            attempt_debug["latency_seconds"] = round(time.perf_counter() - started, 4)
            attempt_debug["parse_status"] = "failure"
            attempt_debug["error"] = str(exc)
            attempt_debug["traceback"] = traceback.format_exc()
            debug["attempts"].append(attempt_debug)
            if attempt >= max_retries:
                break
            await asyncio.sleep(min(8.0, 0.75 * (2 ** (attempt - 1))))

    return {
        "success": False,
        "error": last_error,
        "debug": debug,
    }


def derive_status(structural_ok: bool, judge_ok: bool, dry_run: bool) -> str:
    if structural_ok and judge_ok:
        return "success"
    if structural_ok and dry_run:
        return "dry_run_structural_only"
    if structural_ok:
        return "partial_failure"
    return "failure"


async def evaluate_single_paper(
    *,
    repo_root: Path,
    target: Dict[str, Path],
    client: Any,
    model: str,
    semaphore: asyncio.Semaphore,
    timeout: int,
    max_retries: int,
    dry_run: bool,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    paper_id = str(target["paper_id"])
    total_started = time.perf_counter()
    debug: Dict[str, Any] = {
        "paper_id": paper_id,
        "started_at": utc_now_iso(),
        "input_files": {
            "source_outline_path": str(target["source_outline_path"]),
            "reference_outline_path": str(target["reference_outline_path"]),
            "source_exists": target["source_outline_path"].exists(),
            "reference_exists": target["reference_outline_path"].exists(),
        },
        "normalization": {},
        "outline_rendering": {},
        "structural_distance": {},
        "judge": {
            "model": model,
            "dry_run": dry_run,
            "prompt_paths": {
                "system": str(SYSTEM_PROMPT_PATH),
                "user": str(USER_PROMPT_PATH),
            },
        },
        "errors": [],
    }
    result: Dict[str, Any] = {
        "paper_id": paper_id,
        "source_outline_path": str(target["source_outline_path"]),
        "reference_outline_path": str(target["reference_outline_path"]),
        "output_dir": str(target["output_dir"]),
        "judge_model": model,
        "judge_scores": None,
        "judge_evaluation": None,
        "structural_distance": None,
        "status": "failure",
        "timing": {},
    }

    try:
        source_raw = load_json_file(target["source_outline_path"])
        reference_raw = load_json_file(target["reference_outline_path"])
    except Exception as exc:
        debug["errors"].append(f"Failed to read input files: {exc}")
        debug["ended_at"] = utc_now_iso()
        result["timing"]["total_seconds"] = round(time.perf_counter() - total_started, 4)
        return result, debug

    try:
        source_sections, source_debug = ensure_outline_list(source_raw, "source")
        reference_sections, reference_debug = ensure_outline_list(reference_raw, "reference")
        debug["normalization"]["source"] = source_debug
        debug["normalization"]["reference"] = reference_debug
    except Exception as exc:
        debug["errors"].append(f"Outline normalization failed: {exc}")
        debug["ended_at"] = utc_now_iso()
        result["timing"]["total_seconds"] = round(time.perf_counter() - total_started, 4)
        return result, debug

    structural_ok = False
    judge_ok = False

    structural_started = time.perf_counter()
    try:
        structural_debug = compute_structural_distance_debug(reference_sections, source_sections)
        debug["structural_distance"] = structural_debug
        result["structural_distance"] = structural_debug["shape_distance"]
        structural_ok = True
    except Exception as exc:
        debug["errors"].append(f"Structural distance failed: {exc}")
        debug["structural_distance"]["traceback"] = traceback.format_exc()
    result["timing"]["structural_seconds"] = round(time.perf_counter() - structural_started, 4)

    outline_text = render_outline_text(source_sections)
    debug["outline_rendering"] = {
        "line_count": outline_text.count("\n") + 1 if outline_text else 0,
        "character_count": len(outline_text),
        "preview": outline_text[:1000],
    }

    if dry_run:
        debug["judge"]["status"] = "skipped"
    else:
        judge_started = time.perf_counter()
        messages = build_judge_messages(repo_root=repo_root, topic=paper_id, outline_text=outline_text)
        debug["judge"]["messages_preview"] = {
            "system_length": len(messages[0]["content"]),
            "user_length": len(messages[1]["content"]),
            "user_preview": messages[1]["content"][:1000],
        }
        judge_result = await run_judge_with_retries(
            client=client,
            model=model,
            messages=messages,
            semaphore=semaphore,
            timeout=timeout,
            max_retries=max_retries,
        )
        debug["judge"].update(judge_result.get("debug", {}))
        if judge_result["success"]:
            parsed = judge_result["parsed"]
            result["judge_scores"] = {key: float(parsed[key]) for key in SCORE_KEYS}
            result["judge_evaluation"] = parsed.get("评价", "")
            debug["judge"]["raw_response"] = judge_result["raw_response"]
            debug["judge"]["status"] = "success"
            judge_ok = True
        else:
            debug["judge"]["status"] = "failure"
            debug["judge"]["error"] = judge_result.get("error", "Unknown judge error")
            debug["errors"].append(f"Judge failed: {judge_result.get('error', 'Unknown judge error')}")
        result["timing"]["judge_seconds"] = round(time.perf_counter() - judge_started, 4)

    result["status"] = derive_status(structural_ok, judge_ok, dry_run)
    result["timing"]["total_seconds"] = round(time.perf_counter() - total_started, 4)
    debug["ended_at"] = utc_now_iso()
    return result, debug


def compute_summary(results: Sequence[Dict[str, Any]], model: str, dry_run: bool) -> Dict[str, Any]:
    structural_values = [item["structural_distance"] for item in results if isinstance(item.get("structural_distance"), (int, float))]
    judge_successes = [item for item in results if isinstance(item.get("judge_scores"), dict)]

    judge_averages: Dict[str, float] = {}
    if judge_successes:
        for key in SCORE_KEYS:
            judge_averages[key] = round(
                sum(float(item["judge_scores"][key]) for item in judge_successes) / len(judge_successes),
                4,
            )

    return {
        "generated_at": utc_now_iso(),
        "judge_model": model,
        "dry_run": dry_run,
        "papers_total": len(results),
        "status_counts": {
            status: sum(1 for item in results if item.get("status") == status)
            for status in sorted({item.get("status", "unknown") for item in results} | {"success", "partial_failure", "failure"})
        },
        "avg_structural_distance": round(sum(structural_values) / len(structural_values), 6) if structural_values else None,
        "judge_average_scores": judge_averages or None,
        "papers": results,
    }


async def run_batch(args: argparse.Namespace) -> int:
    repo_root = ROOT_DIR
    results_root = Path(args.results_root)
    if args.source_outline and len(args.paper or []) > 1:
        raise SystemExit("--source-outline only supports a single paper at a time.")

    if args.source_outline:
        paper_id = (args.paper[0] if args.paper else Path(args.source_outline).parent.name)
        paper_ids = [paper_id]
    else:
        paper_ids = args.paper or discover_target_papers(repo_root)
    if not paper_ids:
        raise SystemExit("No chatgpt_meow_outline_blind.json files were found under refs/.")

    client = None
    if not args.dry_run:
        client = build_async_client(
            api_key=args.openai_api_key,
            timeout=args.timeout,
            base_url=args.openai_base_url,
        )
    semaphore = asyncio.Semaphore(max(args.concurrency, 1))

    targets = [
        resolve_eval_target(
            repo_root=repo_root,
            paper_id=paper_id,
            results_root=results_root,
            run_name=args.run_name,
            source_outline=Path(args.source_outline) if args.source_outline else None,
            reference_outline=Path(args.reference_outline) if args.reference_outline else None,
            output_dir=Path(args.output_dir) if args.output_dir and len(paper_ids) == 1 else None,
        )
        for paper_id in paper_ids
    ]

    tasks = [
        evaluate_single_paper(
            repo_root=repo_root,
            target=target,
            client=client,
            model=args.model,
            semaphore=semaphore,
            timeout=args.timeout,
            max_retries=args.max_retries,
            dry_run=args.dry_run,
        )
        for target in targets
    ]
    results_with_debug = await asyncio.gather(*tasks)

    ordered_results: List[Dict[str, Any]] = []
    output_dirs: List[Path] = []
    for target, (result, debug) in zip(targets, results_with_debug):
        write_artifacts(target["output_dir"], result, debug)
        ordered_results.append(result)
        output_dirs.append(target["output_dir"])

    summary = compute_summary(ordered_results, model=args.model, dry_run=args.dry_run)
    summary_path = resolve_summary_path(
        repo_root=repo_root,
        results_root=results_root,
        paper_ids=paper_ids,
        output_dirs=output_dirs,
        run_name=args.run_name,
        explicit_summary_path=Path(args.summary_path) if args.summary_path else None,
    )
    write_json(summary_path, summary)

    for item in ordered_results:
        structural = item["structural_distance"]
        if structural is None:
            structural_text = "NA"
        else:
            structural_text = f"{structural:.6f}"
        print(f"{item['paper_id']}\tstatus={item['status']}\tstructural_distance={structural_text}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate blind outlines with structural distance and async LLM judge."
    )
    parser.add_argument("--paper", action="append", help="Paper id to evaluate. Repeatable. Defaults to all discovered blind outputs.")
    parser.add_argument("--source-outline", help="Explicit path to the model outline JSON file. Single-paper mode.")
    parser.add_argument("--reference-outline", help="Explicit path to the reference outline JSON file. Single-paper mode.")
    parser.add_argument("--output-dir", help="Explicit directory for eval/debug outputs. Single-paper mode.")
    parser.add_argument("--summary-path", help="Explicit summary output path.")
    parser.add_argument("--run-name", help="Results namespace under results/<paper_id>/<run_name>/...")
    parser.add_argument("--results-root", default=str(RESULTS_DIR), help="Root directory for experiment outputs. Default: results/")
    parser.add_argument("--model", default="gpt-5-nano", help="Judge model name.")
    parser.add_argument("--concurrency", type=int, default=4, help="Async judge concurrency.")
    parser.add_argument("--max-retries", type=int, default=3, help="Per-paper max judge retries.")
    parser.add_argument("--timeout", type=int, default=120, help="Per-request timeout in seconds.")
    parser.add_argument("--dry-run", action="store_true", help="Skip API calls and only validate inputs plus structural distance.")
    parser.add_argument("--openai-api-key", default=os.environ.get("OPENAI_API_KEY"), help="OpenAI API key; defaults to OPENAI_API_KEY.")
    parser.add_argument("--openai-base-url", default=os.environ.get("OPENAI_BASE_URL"), help="Optional OpenAI-compatible base URL.")
    args = parser.parse_args()
    if args.output_dir and ((args.paper and len(args.paper) > 1) or not (args.paper or args.source_outline)):
        parser.error("--output-dir only supports single-paper mode.")
    if args.reference_outline and not (args.paper or args.source_outline):
        parser.error("--reference-outline requires --paper or --source-outline.")
    if not args.dry_run and not args.openai_api_key:
        parser.error("Missing OPENAI_API_KEY or --openai-api-key for LLM-as-a-Judge evaluation.")
    return args


def main() -> int:
    args = parse_args()
    return asyncio.run(run_batch(args))


if __name__ == "__main__":
    raise SystemExit(main())
