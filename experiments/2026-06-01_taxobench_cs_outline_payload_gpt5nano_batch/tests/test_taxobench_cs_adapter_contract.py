from pathlib import Path

import pytest

from conftest import load_taxobench_script


adapter = load_taxobench_script("prepare_taxobench_cs_inputs")
validator = load_taxobench_script("validate_taxobench_cs_staging")


def make_ground_record():
    return {
        "arxiv_id": "2401.00001",
        "title": "A Survey Of Example Systems",
        "taxo_tree": {
            "Representation": {
                "Graphs": {
                    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa": {}
                }
            }
        },
        "papers": {
            "0": {
                "paperId": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "title": "Graph Representations",
                "year": 2024,
                "abstract": "A reference abstract.",
                "externalIds": {"ArXiv": "2401.11111", "DOI": "10.0000/example"},
            }
        },
        "papers_index": {"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa": "0"},
    }


def test_normalize_ground_record_requires_core_fields():
    record = make_ground_record()
    del record["papers_index"]

    with pytest.raises(adapter.GroundRecordError, match="papers_index"):
        adapter.normalize_ground_record(record, source_path=Path("ground.json"))


def test_iter_taxonomy_memberships_preserves_repeated_paper_leaf():
    paper_id = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    taxo_tree = {
        "Branch A": {"Concept 1": {paper_id: {}}},
        "Branch B": {"Concept 2": {paper_id: {}}},
    }

    rows = list(adapter.iter_taxonomy_memberships(taxo_tree))

    assert len(rows) == 2
    assert rows[0]["paperId"] == paper_id
    assert rows[1]["paperId"] == paper_id
    assert rows[0]["path"] == ["Branch A", "Concept 1"]
    assert rows[1]["path"] == ["Branch B", "Concept 2"]


def test_staging_validator_fails_non_ready_rows(tmp_path):
    staging = tmp_path / "staging"
    (staging / "manifests").mkdir(parents=True)
    (staging / "taxonomies").mkdir()
    (staging / "payload_sources").mkdir()
    (staging / "outline.json").write_text("[]\n", encoding="utf-8")
    (staging / "taxonomies" / "2401.00001.taxonomy_source.json").write_text("{}\n", encoding="utf-8")
    (staging / "taxonomies" / "2401.00001.taxonomy_membership.jsonl").write_text(
        '{"path":["Branch"],"depth":1,"paperId":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","resolved":false,"ref_index":null}\n',
        encoding="utf-8",
    )
    (staging / "payload_sources" / "2401.00001.payload_source.json").write_text(
        '{"paper_id":"2401.00001","title":"Example","ref_meta":[],"taxonomy":{"tree":{}}}\n',
        encoding="utf-8",
    )
    (staging / "manifests" / "input_manifest.jsonl").write_text(
        (
            '{"paper_id":"2401.00001","arxiv_id":"2401.00001","title":"Example",'
            '"human_written_outline_path":"outline.json",'
            '"taxonomy_source_path":"taxonomies/2401.00001.taxonomy_source.json",'
            '"taxonomy_membership_path":"taxonomies/2401.00001.taxonomy_membership.jsonl",'
            '"payload_source_path":"payload_sources/2401.00001.payload_source.json",'
            '"taxonomy_unresolved_leaf_count":1,'
            '"ready_for_generation":false}\n'
        ),
        encoding="utf-8",
    )

    report = validator.validate_staging(staging_root=staging, expect_papers=1, require_payloads=False)

    assert report["status"] == "fail"
    assert report["fatal_error_count"] >= 1
