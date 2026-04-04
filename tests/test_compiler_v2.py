"""Tests for compiler v0.2 features: rank propagation, mode_assignments, freeze, nested error."""

import pytest

from pakunoda.compiler import compile_candidate, patch_problem_for_trial
from pakunoda.graph import RelationGraph
from pakunoda.candidate import enumerate_candidates, EnumerationConstraints


def _config(max_rank=5):
    return {
        "project": {"id": "test"},
        "blocks": [
            {"id": "A", "kind": "matrix", "modes": ["s", "g"], "file": "a.tsv"},
            {"id": "B", "kind": "matrix", "modes": ["s", "c"], "file": "b.tsv"},
        ],
        "relations": [
            {
                "type": "exact",
                "between": [
                    {"block": "A", "mode": "s"},
                    {"block": "B", "mode": "s"},
                ],
            },
        ],
        "solver": {"family": "CoupledMWCA"},
        "search": {"max_rank": max_rank},
    }


def _meta():
    return {
        "A": {"shape": [5, 4], "canonical_file": "A.npy"},
        "B": {"shape": [5, 3], "canonical_file": "B.npy"},
    }


def _enumerate(config, meta, **kwargs):
    g = RelationGraph.from_config(config, meta)
    c = EnumerationConstraints(**kwargs)
    return enumerate_candidates(g, c)


# ---- rank propagation ----

def test_compile_rank_from_config():
    """rank defaults to search.max_rank when candidate.rank is None."""
    config = _config(max_rank=7)
    candidates = _enumerate(config, _meta())
    problem = compile_candidate(candidates[0].to_dict(), config, _meta())
    assert problem["rank"] == 7


def test_compile_rank_from_candidate():
    """candidate.rank takes priority over config max_rank."""
    config = _config(max_rank=7)
    candidates = _enumerate(config, _meta())
    cand_dict = candidates[0].to_dict()
    cand_dict["rank"] = 3
    problem = compile_candidate(cand_dict, config, _meta())
    assert problem["rank"] == 3


def test_compile_solver_init_policy():
    """compile_candidate includes solver.init_policy."""
    config = _config()
    candidates = _enumerate(config, _meta())
    problem = compile_candidate(candidates[0].to_dict(), config, _meta())
    assert problem["solver"]["init_policy"] == "random"
    assert "seed" in problem["solver"]


# ---- patch_problem_for_trial ----

def test_patch_problem_rank():
    """patch_problem_for_trial overrides rank from trial params."""
    config = _config(max_rank=10)
    candidates = _enumerate(config, _meta())
    problem = compile_candidate(candidates[0].to_dict(), config, _meta())
    assert problem["rank"] == 10

    patched = patch_problem_for_trial(problem, {"rank": 3, "init_policy": "svd"})
    assert patched["rank"] == 3
    assert patched["solver"]["init_policy"] == "svd"
    # Original unchanged
    assert problem["rank"] == 10
    assert problem["solver"]["init_policy"] == "random"


# ---- mode_assignments in problem JSON ----

def test_compile_mode_assignments_present():
    """mode_assignments are included in problem JSON."""
    config = _config()
    candidates = _enumerate(config, _meta())
    problem = compile_candidate(candidates[0].to_dict(), config, _meta())
    assert len(problem["mode_assignments"]) == 4  # 2 blocks * 2 modes
    statuses = {ma["status"] for ma in problem["mode_assignments"]}
    assert statuses == {"decompose"}


def test_compile_mode_assignments_sharing():
    """Shared modes are common, non-shared are specific."""
    config = _config()
    candidates = _enumerate(config, _meta())
    problem = compile_candidate(candidates[0].to_dict(), config, _meta())

    ma_map = {(ma["block"], ma["mode"]): ma for ma in problem["mode_assignments"]}
    assert ma_map[("A", "s")]["sharing"] == "common"
    assert ma_map[("B", "s")]["sharing"] == "common"
    assert ma_map[("A", "g")]["sharing"] == "specific"
    assert ma_map[("B", "c")]["sharing"] == "specific"


# ---- frozen mode ----

def test_compile_frozen_mode():
    """Frozen mode candidates have status=freeze in mode_assignments."""
    config = _config()
    candidates = _enumerate(config, _meta(), allow_frozen_modes=True)
    frozen_cands = [c for c in candidates if "frozen" in c.id]
    assert len(frozen_cands) > 0

    problem = compile_candidate(frozen_cands[0].to_dict(), config, _meta())
    freeze_modes = [ma for ma in problem["mode_assignments"] if ma["status"] == "freeze"]
    assert len(freeze_modes) > 0

    # Frozen modes should be specific
    for fm in freeze_modes:
        assert fm["sharing"] == "specific"


# ---- nested relation error ----

def test_compile_nested_creates_nested_relations():
    """Nested couplings end up in nested_relations field."""
    config = {
        "project": {"id": "test"},
        "blocks": [
            {"id": "X", "kind": "matrix", "modes": ["genes", "samples"], "file": "x.tsv"},
            {"id": "Y", "kind": "matrix", "modes": ["families", "samples"], "file": "y.tsv"},
        ],
        "relations": [
            {
                "type": "nested",
                "between": [
                    {"block": "X", "mode": "genes"},
                    {"block": "Y", "mode": "families"},
                ],
                "mapping": "mapping.tsv",
            },
        ],
        "solver": {"family": "CoupledMWCA"},
        "search": {"max_rank": 3},
    }
    meta = {
        "X": {"shape": [4, 5], "canonical_file": "X.npy"},
        "Y": {"shape": [3, 5], "canonical_file": "Y.npy"},
    }

    g = RelationGraph.from_config(config, meta)
    candidates = enumerate_candidates(g, EnumerationConstraints(allow_nested=True))
    assert len(candidates) > 0

    problem = compile_candidate(candidates[0].to_dict(), config, meta)
    assert len(problem["nested_relations"]) > 0
    # Exact couplings should be empty (only nested)
    assert len(problem["couplings"]) == 0
