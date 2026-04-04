"""Tests for pakunoda.graph (typed RelationGraph)."""

from pakunoda.graph import RelationGraph, ModeNode, Relation


def _sample_config():
    return {
        "blocks": [
            {"id": "A", "kind": "matrix", "modes": ["samples", "genes"], "file": "a.tsv"},
            {"id": "B", "kind": "matrix", "modes": ["samples", "cpgs"], "file": "b.tsv"},
            {"id": "C", "kind": "matrix", "modes": ["genes", "proteins"], "file": "c.tsv"},
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


def test_from_config():
    g = RelationGraph.from_config(_sample_config(), _sample_metadata())
    assert g.get_block_ids() == ["A", "B", "C"]
    assert len(g.modes) == 6
    assert len(g.relations) == 2


def test_get_modes_for_block():
    g = RelationGraph.from_config(_sample_config(), _sample_metadata())
    modes_a = g.get_modes_for_block("A")
    assert len(modes_a) == 2
    assert {m.mode for m in modes_a} == {"samples", "genes"}


def test_get_relations_for_blocks():
    g = RelationGraph.from_config(_sample_config(), _sample_metadata())
    # A and B share a samples relation
    rels_ab = g.get_relations_for_blocks(["A", "B"])
    assert len(rels_ab) == 1
    assert rels_ab[0].type == "exact"

    # A and C share a genes relation
    rels_ac = g.get_relations_for_blocks(["A", "C"])
    assert len(rels_ac) == 1

    # B and C share no direct relation
    rels_bc = g.get_relations_for_blocks(["B", "C"])
    assert len(rels_bc) == 0

    # All three: both relations apply
    rels_all = g.get_relations_for_blocks(["A", "B", "C"])
    assert len(rels_all) == 2


def test_get_shared_block_ids():
    g = RelationGraph.from_config(_sample_config(), _sample_metadata())
    shared = g.get_shared_block_ids(["A", "B", "C"])
    assert shared == {"A", "B", "C"}

    shared_bc = g.get_shared_block_ids(["B", "C"])
    assert shared_bc == set()


def test_get_coupled_modes():
    g = RelationGraph.from_config(_sample_config(), _sample_metadata())
    groups = g.get_coupled_modes(["A", "B", "C"])
    assert len(groups) == 2
    # Check that A:samples and B:samples are grouped
    found_samples = False
    for group in groups:
        if "A:samples" in group and "B:samples" in group:
            found_samples = True
    assert found_samples


def test_dimensions():
    g = RelationGraph.from_config(_sample_config(), _sample_metadata())
    modes_a = g.get_modes_for_block("A")
    dim_map = {m.mode: m.dimension for m in modes_a}
    assert dim_map["samples"] == 5
    assert dim_map["genes"] == 4


def test_from_graph_json():
    """Test building RelationGraph from the graph rule's JSON output."""
    config = _sample_config()
    graph_dict = {
        "nodes": [
            {"id": "A:samples", "block": "A", "mode": "samples", "dimension": 5},
            {"id": "A:genes", "block": "A", "mode": "genes", "dimension": 4},
            {"id": "B:samples", "block": "B", "mode": "samples", "dimension": 5},
            {"id": "B:cpgs", "block": "B", "mode": "cpgs", "dimension": 3},
            {"id": "C:genes", "block": "C", "mode": "genes", "dimension": 4},
            {"id": "C:proteins", "block": "C", "mode": "proteins", "dimension": 3},
        ],
        "edges": [
            {"source": "A:samples", "target": "B:samples", "type": "exact"},
            {"source": "A:genes", "target": "C:genes", "type": "exact"},
        ],
    }
    g = RelationGraph.from_graph_json(config, graph_dict)
    assert len(g.modes) == 6
    assert len(g.relations) == 2
    assert g.get_block_ids() == ["A", "B", "C"]
