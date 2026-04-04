"""Tests for pakunoda.relation_graph."""

from pakunoda.relation_graph import build_relation_graph, validate_graph


def _sample_config():
    return {
        "blocks": [
            {"id": "A", "modes": ["samples", "genes"]},
            {"id": "B", "modes": ["samples", "cpgs"]},
            {"id": "C", "modes": ["genes", "proteins"]},
        ],
        "relations": [
            {
                "type": "exact",
                "between": [
                    {"block": "A", "mode": "samples"},
                    {"block": "B", "mode": "samples"},
                ],
            },
            {
                "type": "exact",
                "between": [
                    {"block": "A", "mode": "genes"},
                    {"block": "C", "mode": "genes"},
                ],
            },
        ],
    }


def _sample_metadata():
    return {
        "A": {"shape": [5, 4]},
        "B": {"shape": [5, 3]},
        "C": {"shape": [4, 3]},
    }


def test_build_graph_nodes():
    graph = build_relation_graph(_sample_config(), _sample_metadata())
    node_ids = {n["id"] for n in graph["nodes"]}
    assert node_ids == {"A:samples", "A:genes", "B:samples", "B:cpgs", "C:genes", "C:proteins"}


def test_build_graph_edges():
    graph = build_relation_graph(_sample_config(), _sample_metadata())
    assert len(graph["edges"]) == 2
    edge_pairs = {(e["source"], e["target"]) for e in graph["edges"]}
    assert ("A:samples", "B:samples") in edge_pairs
    assert ("A:genes", "C:genes") in edge_pairs


def test_build_graph_dimensions():
    graph = build_relation_graph(_sample_config(), _sample_metadata())
    node_map = {n["id"]: n for n in graph["nodes"]}
    assert node_map["A:samples"]["dimension"] == 5
    assert node_map["A:genes"]["dimension"] == 4
    assert node_map["C:proteins"]["dimension"] == 3


def test_validate_graph_ok():
    graph = build_relation_graph(_sample_config(), _sample_metadata())
    errors = validate_graph(graph)
    assert errors == []


def test_validate_graph_dimension_mismatch():
    meta = _sample_metadata()
    meta["B"]["shape"] = [10, 3]  # samples dimension mismatch
    graph = build_relation_graph(_sample_config(), meta)
    errors = validate_graph(graph)
    assert len(errors) == 1
    assert "dimension mismatch" in errors[0]
