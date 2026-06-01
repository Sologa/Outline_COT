import json
import re

import pytest

from conftest import load_experiment_script


evaluator = load_experiment_script(
    "experiments/2026-06-01_taxobench_cs_outline_payload_gpt5nano_batch/prototype/evaluate_taxobench_cs_outlines_batch.py"
)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def make_outline(title_suffix=""):
    return [
        {"level": 1, "numbering": "1", "title": f"Introduction{title_suffix}", "ref": []},
        {"level": 1, "numbering": "2", "title": f"Methods{title_suffix}", "ref": ["ref-a"]},
        {"level": 2, "numbering": "2.1", "title": f"Taxonomy{title_suffix}", "ref": ["ref-a"]},
    ]


def make_staging(tmp_path):
    paper_id = "2401.00001"
    staging = tmp_path / "staging"
    reference_outline = staging / "reference_outlines" / f"{paper_id}.outline.json"
    write_json(reference_outline, make_outline())
    row = {
        "paper_id": paper_id,
        "arxiv_id": paper_id,
        "title": "A Survey Of Example Systems",
        "human_written_outline_path": f"reference_outlines/{paper_id}.outline.json",
        "payload_source_path": f"payload_sources/{paper_id}.payload_source.json",
        "ready_for_generation": True,
    }
    write_jsonl(staging / "manifests" / "input_manifest.jsonl", [row])
    return staging, paper_id


def test_render_only_writes_human_written_judge_batch_request(tmp_path):
    staging, paper_id = make_staging(tmp_path)
    output = tmp_path / "judge_render"

    summary = evaluator.render_judge_requests(
        staging_root=staging,
        output_root=output,
        arms=["human_written"],
        paper_ids=[paper_id],
        write_batch_input=True,
        force=True,
    )

    rows = [json.loads(line) for line in (output / "batch_input.jsonl").read_text(encoding="utf-8").splitlines()]
    manifest = json.loads((output / "request_manifest.json").read_text(encoding="utf-8"))
    prompt_text = (output / "judge_prompts" / paper_id / "human_written" / "prompt.json").read_text(encoding="utf-8")

    assert summary["request_count"] == 1
    assert rows[0]["custom_id"] == f"{paper_id}__human_written"
    assert rows[0]["method"] == "POST"
    assert rows[0]["url"] == "/v1/responses"
    assert rows[0]["body"]["model"] == evaluator.JUDGE_MODEL
    assert rows[0]["body"]["reasoning"] == {"effort": "high"}
    for score_key in evaluator.load_eval_module().SCORE_KEYS:
        assert score_key in prompt_text
    assert "Introduction" in prompt_text
    assert "A Survey Of Example Systems" in prompt_text
    assert not re.search(r"/Users/xjp|source_ground_path|human_written_outline_path|payload_source_path|metadata_", prompt_text)
    request = manifest["requests"][0]
    assert request["arm"] == "human_written"
    assert request["source_equals_reference"] is True
    assert request["structural_distance"] == 0.0


def test_render_only_maps_generated_arm_to_generated_outline_source(tmp_path):
    staging, paper_id = make_staging(tmp_path)
    output = tmp_path / "judge_render"
    generated_root = tmp_path / "generated"
    generated_outline = generated_root / paper_id / "flat_concepts" / "chatgpt_meow_outline_blind.json"
    write_json(generated_outline, make_outline())

    evaluator.render_judge_requests(
        staging_root=staging,
        output_root=output,
        arms=["flat_concepts"],
        paper_ids=[paper_id],
        generated_root=generated_root,
        write_batch_input=True,
        force=True,
    )

    row = json.loads((output / "batch_input.jsonl").read_text(encoding="utf-8").splitlines()[0])
    manifest = json.loads((output / "request_manifest.json").read_text(encoding="utf-8"))

    assert row["custom_id"] == f"{paper_id}__flat_concepts"
    assert manifest["requests"][0]["source_outline_path"] == str(generated_outline)
    assert manifest["requests"][0]["source_equals_reference"] is False


def test_parse_fixture_batch_output_writes_eval_artifacts(tmp_path):
    staging, paper_id = make_staging(tmp_path)
    output = tmp_path / "judge_render"
    evaluator.render_judge_requests(
        staging_root=staging,
        output_root=output,
        arms=["human_written"],
        paper_ids=[paper_id],
        write_batch_input=True,
        force=True,
    )
    scores = {key: 8.0 for key in evaluator.load_eval_module().SCORE_KEYS}
    raw_response = {"评价": "fixture evaluation", **scores}
    batch_output = output / "fixture_batch_output.jsonl"
    write_jsonl(
        batch_output,
        [
            {
                "custom_id": f"{paper_id}__human_written",
                "response": {
                    "status_code": 200,
                    "request_id": "req_fixture",
                    "body": {
                        "output": [
                            {
                                "type": "message",
                                "content": [
                                    {
                                        "type": "output_text",
                                        "text": json.dumps(raw_response, ensure_ascii=False),
                                    }
                                ],
                            }
                        ]
                    },
                },
                "error": None,
            }
        ],
    )

    summary = evaluator.parse_batch_output(output_root=output, batch_output_path=batch_output, force=True)

    result_path = output / "evaluations" / paper_id / "human_written" / evaluator.RESULT_FILENAME
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert summary["parsed_count"] == 1
    assert result["status"] == "success"
    assert result["arm"] == "human_written"
    assert result["structural_distance"] == 0.0
    assert result["judge_transport"] == "openai_batch_api"
    assert set(result["judge_scores"]) == set(evaluator.load_eval_module().SCORE_KEYS)
    assert all(value == 8.0 for value in result["judge_scores"].values())


def test_parse_batch_output_rejects_missing_and_duplicate_rows(tmp_path):
    staging, paper_id = make_staging(tmp_path)
    output = tmp_path / "judge_render"
    evaluator.render_judge_requests(
        staging_root=staging,
        output_root=output,
        arms=["human_written"],
        paper_ids=[paper_id],
        write_batch_input=True,
        force=True,
    )
    empty_output = output / "empty_batch_output.jsonl"
    empty_output.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="missing expected custom_id"):
        evaluator.parse_batch_output(output_root=output, batch_output_path=empty_output, force=True)

    raw_response = {"评价": "fixture evaluation", **{key: 8.0 for key in evaluator.load_eval_module().SCORE_KEYS}}
    row = {
        "custom_id": f"{paper_id}__human_written",
        "response": {
            "status_code": 200,
            "body": {"output_text": json.dumps(raw_response, ensure_ascii=False)},
        },
        "error": None,
    }
    duplicate_output = output / "duplicate_batch_output.jsonl"
    write_jsonl(duplicate_output, [row, row])

    with pytest.raises(ValueError, match="duplicate custom_id"):
        evaluator.parse_batch_output(output_root=output, batch_output_path=duplicate_output, force=True)


def test_evaluator_refuses_results_output_root(tmp_path):
    staging, paper_id = make_staging(tmp_path)
    output = evaluator.ROOT_DIR / "results" / "experiments" / "should_not_write"

    with pytest.raises(ValueError, match=r"under results/"):
        evaluator.render_judge_requests(
            staging_root=staging,
            output_root=output,
            arms=["human_written"],
            paper_ids=[paper_id],
            write_batch_input=True,
            force=True,
        )
