"""Tests for compile_candidate in pakunoda.compiler."""

from pakunoda.graph import RelationGraph
from pakunoda.candidate import enumerate_candidates, EnumerationConstraints
from pakunoda.compiler import compile_candidate


def _config():
    return {
        "project": {"id": "test"},
        "blocks": [
            {"id": "A", "kind": "matrix", "modes": ["samples", "genes"], "file": "a.tsv"},
            {"id": "B", "kind": "matrix", "modes": ["samples", "cpgs"], "file": "b.tsv"},
        ],
        "relations": [
            {
                "type": "exact",
                "between": [
                    {"block": "A", "mode": "samples"},
                    {"block": "B", "mode": "samples"},
                ],
            },
        ],
        "solver": {"family": "CoupledMWCA"},
        "search": {"max_rank": 5},
    }


def _metadata():
    return {
        "A": {"shape": [5, 4], "canonical_file": "results/A.npy"},
        "B": {"shape": [5, 3], "canonical_file": "results/B.npy"},
    }


def test_compile_candidate_basic():
    config = _config()
    g = RelationGraph.from_config(config, _metadata())
    constraints = EnumerationConstraints()
    candidates = enumerate_candidates(g, constraints)
    assert len(candidates) == 1

    problem = compile_candidate(candidates[0].to_dict(), config, _metadata())
    assert problem["project_id"] == "test"
    assert problem["candidate_id"] == candidates[0].id
    assert problem["solver"]["family"] == "CoupledMWCA"
    assert len(problem["tensors"]) == 2
    assert problem["search"]["max_rank"] == 5


def test_compile_candidate_has_couplings():
    config = _config()
    g = RelationGraph.from_config(config, _metadata())
    constraints = EnumerationConstraints()
    candidates = enumerate_candidates(g, constraints)

    problem = compile_candidate(candidates[0].to_dict(), config, _metadata())
    assert len(problem["couplings"]) == 1
    members = problem["couplings"][0]["members"]
    blocks_in = {m["block"] for m in members}
    assert blocks_in == {"A", "B"}


def test_compile_candidate_has_mode_assignments():
    config = _config()
    g = RelationGraph.from_config(config, _metadata())
    constraints = EnumerationConstraints()
    candidates = enumerate_candidates(g, constraints)

    problem = compile_candidate(candidates[0].to_dict(), config, _metadata())
    assert len(problem["mode_assignments"]) == 4  # 2 modes per block x 2 blocks


def test_compile_candidate_subset():
    """Compile a candidate that uses only a subset of blocks."""
    config = {
        "project": {"id": "test"},
        "blocks": [
            {"id": "A", "kind": "matrix", "modes": ["s", "g"], "file": "a.tsv"},
            {"id": "B", "kind": "matrix", "modes": ["s", "c"], "file": "b.tsv"},
            {"id": "C", "kind": "matrix", "modes": ["g", "p"], "file": "c.tsv"},
        ],
        "relations": [
            {
                "type": "exact",
                "between": [
                    {"block": "A", "mode": "s"},
                    {"block": "B", "mode": "s"},
                ],
            },
            {
                "type": "exact",
                "between": [
                    {"block": "A", "mode": "g"},
                    {"block": "C", "mode": "g"},
                ],
            },
        ],
        "solver": {"family": "CoupledMWCA"},
        "search": {"max_rank": 3},
    }
    meta = {
        "A": {"shape": [5, 4], "canonical_file": "A.npy"},
        "B": {"shape": [5, 3], "canonical_file": "B.npy"},
        "C": {"shape": [4, 3], "canonical_file": "C.npy"},
    }

    g = RelationGraph.from_config(config, meta)
    constraints = EnumerationConstraints(max_blocks=2)
    candidates = enumerate_candidates(g, constraints)

    # Pick the (A, B) candidate
    ab = next(c for c in candidates if set(c.blocks) == {"A", "B"})
    problem = compile_candidate(ab.to_dict(), config, meta)
    assert len(problem["tensors"]) == 2
    tensor_ids = {t["id"] for t in problem["tensors"]}
    assert tensor_ids == {"A", "B"}
