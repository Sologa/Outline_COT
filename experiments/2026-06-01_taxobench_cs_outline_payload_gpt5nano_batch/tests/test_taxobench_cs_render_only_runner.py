import json
import re

import pytest

from conftest import load_experiment_script


runner = load_experiment_script(
    "experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prototype/run_taxobench_cs_outline_batch.py"
)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_staging(tmp_path, *, ready=True):
    paper_id = "2401.00001"
    staging = tmp_path / "staging"
    (staging / "manifests").mkdir(parents=True)
    payload_source = {
        "paper_id": paper_id,
        "arxiv_id": paper_id,
        "title": "A {taxonomy_payload} Survey",
        "ref_meta": [
            {
                "ref_index": "0",
                "paperId": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "title": "Graph {title} Systems",
                "year": 2024,
                "abstract": "Reference abstract.",
                "externalIds": {"ArXiv": "2401.11111"},
            }
        ],
        "taxonomy": {"tree": {}},
    }
    write_json(staging / "payload_sources" / f"{paper_id}.payload_source.json", payload_source)
    for arm in ("flat_concepts", "random_hierarchy", "tree_only_guarded", "tree_with_papers"):
        payload_path = staging / "payloads" / paper_id / f"{arm}.txt"
        payload_path.parent.mkdir(parents=True, exist_ok=True)
        payload_path.write_text(f"Payload for {arm} with literal {{title}}\n", encoding="utf-8")
    row = {
        "paper_id": paper_id,
        "arxiv_id": paper_id,
        "title": payload_source["title"],
        "payload_source_path": f"payload_sources/{paper_id}.payload_source.json",
        "ready_for_generation": ready,
    }
    (staging / "manifests" / "input_manifest.jsonl").write_text(
        json.dumps(row, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return staging


def test_render_only_writes_five_generated_requests_without_human_written(tmp_path):
    staging = make_staging(tmp_path)
    output = tmp_path / "render"

    summary = runner.render_requests(
        staging_root=staging,
        output_root=output,
        limit=1,
        write_batch_input=True,
        force=True,
    )

    rows = [json.loads(line) for line in (output / "batch_input.jsonl").read_text(encoding="utf-8").splitlines()]
    prompt_paths = list((output / "prompts").glob("*/*/prompt.txt"))
    all_prompt_text = "\n".join(path.read_text(encoding="utf-8") for path in prompt_paths)
    baseline_row = next(row for row in rows if row["custom_id"].endswith("__baseline_no_taxonomy"))
    taxonomy_rows = [row for row in rows if not row["custom_id"].endswith("__baseline_no_taxonomy")]

    assert summary["request_count"] == 5
    assert len(rows) == 5
    assert {row["custom_id"].split("__", 1)[1] for row in rows} == set(runner.GENERATED_ARMS)
    assert all("human_written" not in row["custom_id"] for row in rows)
    assert all(row["body"]["max_output_tokens"] == 65536 for row in rows)
    assert "meow_reconstructed_blind.json" not in all_prompt_text
    assert "Hard restrictions" not in all_prompt_text
    assert "Faithful released MEOW" not in all_prompt_text
    assert "Payload comparison user prompt" not in all_prompt_text
    assert "{title}" in all_prompt_text
    assert not re.search(
        r"Target Paper Abstract:|with_abstract|no_abstract|structural_complete_guarded|metadata_|/Users/xjp|TaxoBench-CS",
        all_prompt_text + "\n" + (output / "batch_input.jsonl").read_text(encoding="utf-8"),
    )
    assert len(prompt_paths) == 5
    assert baseline_row["body"]["input"] == runner.build_baseline_prompt(
        title="A {taxonomy_payload} Survey",
        references=runner.sanitize_references(
            [
                {
                    "ref_index": "0",
                    "paperId": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "title": "Graph {title} Systems",
                    "year": 2024,
                    "abstract": "Reference abstract.",
                    "externalIds": {"ArXiv": "2401.11111"},
                }
            ]
        ),
    )
    assert all(row["body"]["input"][0]["content"] == runner.SYSTEM_PROMPT for row in rows)
    assert "In addition to the references above" not in baseline_row["body"]["input"][1]["content"]
    for row in taxonomy_rows:
        user_content = row["body"]["input"][1]["content"]
        assert "Write an outline for a literature review based on the given title and references." in user_content
        assert "References:" in user_content
        assert "In addition to the references above, the following is an auxiliary taxonomy representation" in user_content
        assert "Payload mode:" not in user_content
        assert "taxonomy-derived" not in user_content
        assert "Use the reference metadata and taxonomy" not in user_content
        assert "use it as an additional organizational signal" not in user_content


def test_render_only_rejects_non_ready_manifest_rows(tmp_path):
    staging = make_staging(tmp_path, ready=False)

    with pytest.raises(RuntimeError, match="ready_for_generation"):
        runner.render_requests(
            staging_root=staging,
            output_root=tmp_path / "render",
            limit=1,
            write_batch_input=True,
            force=True,
        )


def batch_output_row(custom_id):
    body = {
        "id": f"resp_{custom_id}",
        "model": runner.MODEL,
        "output_text": json.dumps(
            [
                {
                    "level": 1,
                    "numbering": "1",
                    "title": f"Outline for {custom_id}",
                    "ref": ["0"],
                }
            ],
            ensure_ascii=False,
        ),
        "usage": {
            "input_tokens": 100,
            "output_tokens": 20,
            "total_tokens": 120,
            "output_tokens_details": {"reasoning_tokens": 5},
        },
    }
    return {
        "custom_id": custom_id,
        "response": {"status_code": 200, "request_id": f"req_{custom_id}", "body": body},
        "error": None,
    }


def test_parse_generated_outline_accepts_outline_wrapper():
    parsed = runner.parse_generated_outline(
        json.dumps(
            {
                "outline": [
                    {
                        "level": 1,
                        "numbering": "1",
                        "title": "Wrapped Section",
                        "ref": ["0"],
                    }
                ]
            }
        )
    )

    assert parsed == [{"level": 1, "numbering": "1", "title": "Wrapped Section", "ref": ["0"]}]


def test_parse_generated_outline_recovers_complete_objects_with_bad_ref_token():
    raw_text = """
    [
      {
        "level": 1,
        "numbering": "1",
        "title": "Recovered Section",
        "ref": [
          "S2:abc",
          broken reference token,
          "S2:def"
        ]
      }
    ]
    """

    parsed = runner.parse_generated_outline(raw_text)

    assert parsed == [{"level": 1, "numbering": "1", "title": "Recovered Section", "ref": ["S2:abc", "S2:def"]}]


def test_parse_batch_output_writes_generated_root_layout(tmp_path):
    staging = make_staging(tmp_path)
    output = tmp_path / "render"
    generated_root = tmp_path / "generated"
    runner.render_requests(
        staging_root=staging,
        output_root=output,
        generated_root=generated_root,
        limit=1,
        write_batch_input=True,
        force=True,
    )
    rows = [json.loads(line) for line in (output / "batch_input.jsonl").read_text(encoding="utf-8").splitlines()]
    batch_output = tmp_path / "batch_output.jsonl"
    batch_output.write_text(
        "".join(json.dumps(batch_output_row(row["custom_id"]), ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )

    summary = runner.parse_batch_output(
        output_root=output,
        batch_output_path=batch_output,
        generated_root=generated_root,
        force=True,
    )

    assert summary["parsed_count"] == 5
    assert summary["success_count"] == 5
    assert summary["failure_count"] == 0
    for arm in runner.GENERATED_ARMS:
        outline_path = generated_root / "2401.00001" / arm / "chatgpt_meow_outline_blind.json"
        manifest_path = generated_root / "2401.00001" / arm / "run_manifest.json"
        assert json.loads(outline_path.read_text(encoding="utf-8"))[0]["level"] == 1
        assert json.loads(manifest_path.read_text(encoding="utf-8"))["status"] == "success"


def test_parse_batch_output_rejects_missing_custom_id(tmp_path):
    staging = make_staging(tmp_path)
    output = tmp_path / "render"
    runner.render_requests(
        staging_root=staging,
        output_root=output,
        generated_root=tmp_path / "generated",
        limit=1,
        write_batch_input=True,
        force=True,
    )
    rows = [json.loads(line) for line in (output / "batch_input.jsonl").read_text(encoding="utf-8").splitlines()]
    batch_output = tmp_path / "batch_output.jsonl"
    batch_output.write_text(
        "".join(json.dumps(batch_output_row(row["custom_id"]), ensure_ascii=False) + "\n" for row in rows[:-1]),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing expected custom_id"):
        runner.parse_batch_output(output_root=output, batch_output_path=batch_output, force=True)


def test_parse_batch_output_keeps_incomplete_response_failed(tmp_path):
    staging = make_staging(tmp_path)
    output = tmp_path / "render"
    generated_root = tmp_path / "generated"
    runner.render_requests(
        staging_root=staging,
        output_root=output,
        generated_root=generated_root,
        limit=1,
        write_batch_input=True,
        force=True,
    )
    rows = [json.loads(line) for line in (output / "batch_input.jsonl").read_text(encoding="utf-8").splitlines()]
    output_rows = [batch_output_row(row["custom_id"]) for row in rows]
    output_rows[0]["response"]["body"]["status"] = "incomplete"
    output_rows[0]["response"]["body"]["incomplete_details"] = {"reason": "max_output_tokens"}
    batch_output = tmp_path / "batch_output.jsonl"
    batch_output.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in output_rows),
        encoding="utf-8",
    )

    summary = runner.parse_batch_output(
        output_root=output,
        batch_output_path=batch_output,
        generated_root=generated_root,
        force=True,
    )

    assert summary["success_count"] == 4
    assert summary["failure_count"] == 1
    failed_manifest = json.loads((generated_root / "2401.00001" / rows[0]["custom_id"].split("__", 1)[1] / "run_manifest.json").read_text())
    assert failed_manifest["status"] == "parse_failed"
    assert "Response incomplete" in failed_manifest["error"]


def test_generation_output_root_rejects_results_tree(tmp_path):
    staging = make_staging(tmp_path)

    with pytest.raises(ValueError, match=r"under results/"):
        runner.render_requests(
            staging_root=staging,
            output_root=runner.ROOT_DIR / "results" / "taxobench_cs_generation_test",
            limit=1,
            write_batch_input=True,
            force=True,
        )
