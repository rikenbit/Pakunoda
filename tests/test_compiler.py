"""Tests for pakunoda.compiler."""

from pakunoda.compiler import compile_problem


def _sample_config():
    return {
        "project": {"id": "test"},
        "blocks": [
            {"id": "A", "file": "a.npy", "kind": "matrix", "modes": ["samples", "genes"]},
            {"id": "B", "file": "b.npy", "kind": "matrix", "modes": ["samples", "cpgs"]},
        ],
        "solver": {"family": "CoupledMWCA"},
        "search": {"max_rank": 5},
    }


def _sample_graph():
    return {
        "nodes": [
            {"id": "A:samples", "block": "A", "mode": "samples", "dimension": 5},
            {"id": "A:genes", "block": "A", "mode": "genes", "dimension": 4},
            {"id": "B:samples", "block": "B", "mode": "samples", "dimension": 5},
            {"id": "B:cpgs", "block": "B", "mode": "cpgs", "dimension": 3},
        ],
        "edges": [
            {"source": "A:samples", "target": "B:samples", "type": "exact"},
        ],
    }


def _sample_metadata():
    return {
        "A": {"shape": [5, 4], "canonical_file": "results/A.npy"},
        "B": {"shape": [5, 3], "canonical_file": "results/B.npy"},
    }


def test_compile_basic():
    problem = compile_problem(_sample_config(), _sample_graph(), _sample_metadata())
    assert problem["project_id"] == "test"
    assert problem["solver"]["family"] == "CoupledMWCA"
    assert len(problem["tensors"]) == 2
    assert problem["search"]["max_rank"] == 5


def test_compile_couplings():
    problem = compile_problem(_sample_config(), _sample_graph(), _sample_metadata())
    # A:samples and B:samples should be in the same coupling group
    coupled_groups = [c for c in problem["couplings"] if len(c["members"]) > 1]
    assert len(coupled_groups) == 1
    members = coupled_groups[0]["members"]
    blocks_in_group = {m["block"] for m in members}
    assert blocks_in_group == {"A", "B"}


def test_compile_version():
    problem = compile_problem(_sample_config(), _sample_graph(), _sample_metadata())
    assert problem["version"] == "0.1.0"
