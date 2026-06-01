from conftest import load_taxobench_script


renderer = load_taxobench_script("generate_taxobench_cs_payloads")


def make_payload_source():
    paper_id_a = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    paper_id_b = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    return {
        "paper_id": "2401.00001",
        "arxiv_id": "2401.00001",
        "title": "A Survey Of Example Systems",
        "ref_meta": [
            {
                "ref_index": "0",
                "paperId": paper_id_a,
                "title": "Graph Representations",
                "year": 2024,
                "abstract": "Do not duplicate this in tree payloads.",
                "externalIds": {"ArXiv": "2401.11111", "DOI": "10.0000/example", "CorpusId": 123},
            },
            {
                "ref_index": "1",
                "paperId": paper_id_b,
                "title": "Tree Systems",
                "year": None,
                "abstract": "Another reference abstract.",
                "externalIds": {"DBLP": "conf/example/TreeSystems24"},
            },
        ],
        "taxonomy": {
            "tree": {
                "Representation": {
                    "Graphs": {paper_id_a: {}},
                    "Trees": {paper_id_b: {}},
                }
            }
        },
    }


def test_tree_only_guarded_preserves_labels_and_paper_leaves():
    text = renderer.render_tree_only_guarded(make_payload_source())

    assert "Representation" in text
    assert "Graphs" in text
    assert "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" in text
    assert "Graph Representations" not in text


def test_tree_with_papers_includes_metadata_but_not_abstracts():
    text = renderer.render_tree_with_papers(make_payload_source())

    assert "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" in text
    assert "Graph Representations" in text
    assert "2024" in text
    assert "ArXiv=2401.11111" in text
    assert "10.0000/example" in text
    assert "Do not duplicate this in tree payloads." not in text
    assert "abstract" not in text.lower()


def test_tree_with_papers_keeps_source_strings_on_one_line():
    payload = make_payload_source()
    payload["ref_meta"][0]["title"] = "Graph\nRepresentations | Prompt"
    payload["ref_meta"][0]["externalIds"]["DOI"] = "10.0000/example|pipe"
    text = renderer.render_tree_with_papers(payload)

    assert "Graph Representations / Prompt" in text
    assert "10.0000/example/pipe" in text
    assert "Graph\nRepresentations" not in text


def test_flat_concepts_removes_parent_child_nesting_but_keeps_labels():
    text = renderer.render_flat_concepts(make_payload_source())

    assert "Representation" in text
    assert "Graphs" in text
    assert "Trees" in text
    assert "  - " not in text


def test_random_hierarchy_is_deterministic_for_same_experiment_and_paper():
    payload = make_payload_source()

    first = renderer.render_random_hierarchy(payload, experiment_id="experiment")
    second = renderer.render_random_hierarchy(payload, experiment_id="experiment")

    assert first == second
    assert "Representation" in first
    assert "Graphs" in first
    assert "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" in first
    assert "definition" not in first.lower()
