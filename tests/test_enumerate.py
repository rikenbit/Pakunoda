"""Tests for pakunoda.candidate (enumeration)."""

import pytest

from pakunoda.graph import RelationGraph
from pakunoda.candidate import (
    enumerate_candidates,
    EnumerationConstraints,
    Candidate,
)


# --- Helpers ---

def _chain_config():
    """A -- samples -- B -- (no direct) -- C, A -- genes -- C.
    3 blocks, 2 exact relations forming a chain."""
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


def _chain_metadata():
    return {"A": {"shape": [5, 4]}, "B": {"shape": [5, 3]}, "C": {"shape": [4, 3]}}


def _nested_config():
    """2 blocks with a nested relation."""
    return {
        "blocks": [
            {"id": "X", "kind": "matrix", "modes": ["genes", "samples"], "file": "x.tsv"},
            {"id": "Y", "kind": "matrix", "modes": ["gene_families", "samples"], "file": "y.tsv"},
        ],
        "relations": [
            {
                "type": "nested",
                "between": [
                    {"block": "X", "mode": "genes"},
                    {"block": "Y", "mode": "gene_families"},
                ],
                "mapping": "mapping.tsv",
            },
        ],
    }


def _disconnected_config():
    """2 blocks with no relation."""
    return {
        "blocks": [
            {"id": "P", "kind": "matrix", "modes": ["a", "b"], "file": "p.tsv"},
            {"id": "Q", "kind": "matrix", "modes": ["c", "d"], "file": "q.tsv"},
        ],
        "relations": [],
    }


# --- Tests: simple exact shared ---

def test_enumerate_chain_default():
    """Default constraints: enumerate all valid subsets."""
    g = RelationGraph.from_config(_chain_config(), _chain_metadata())
    c = EnumerationConstraints()
    candidates = enumerate_candidates(g, c)

    # Valid pairs: (A,B) has 1 rel, (A,C) has 1 rel, (B,C) has 0 rels -> skip
    # Valid triple: (A,B,C) has 2 rels
    # So: 3 candidates (A+B, A+C, A+B+C)
    assert len(candidates) == 3
    block_sets = [tuple(sorted(c.blocks)) for c in candidates]
    assert ("A", "B") in block_sets
    assert ("A", "C") in block_sets
    assert ("A", "B", "C") in block_sets


def test_enumerate_chain_max_blocks_2():
    """max_blocks=2 should exclude the triple."""
    g = RelationGraph.from_config(_chain_config(), _chain_metadata())
    c = EnumerationConstraints(max_blocks=2)
    candidates = enumerate_candidates(g, c)
    assert len(candidates) == 2
    for cand in candidates:
        assert len(cand.blocks) == 2


def test_enumerate_mode_assignments():
    """Check that mode assignments are correct for a pair."""
    g = RelationGraph.from_config(_chain_config(), _chain_metadata())
    c = EnumerationConstraints(max_blocks=2)
    candidates = enumerate_candidates(g, c)

    # Find the (A, B) candidate
    ab = next(cand for cand in candidates if set(cand.blocks) == {"A", "B"})
    ma_map = {(ma.block, ma.mode): ma for ma in ab.mode_assignments}

    # A:samples and B:samples are shared -> common
    assert ma_map[("A", "samples")].sharing == "common"
    assert ma_map[("B", "samples")].sharing == "common"

    # A:genes and B:cpgs are not shared -> specific
    assert ma_map[("A", "genes")].sharing == "specific"
    assert ma_map[("B", "cpgs")].sharing == "specific"

    # All decomposed
    for ma in ab.mode_assignments:
        assert ma.status == "decompose"


def test_enumerate_couplings():
    """Check coupling structure."""
    g = RelationGraph.from_config(_chain_config(), _chain_metadata())
    c = EnumerationConstraints(max_blocks=2)
    candidates = enumerate_candidates(g, c)

    ab = next(cand for cand in candidates if set(cand.blocks) == {"A", "B"})
    assert len(ab.couplings) == 1
    assert ab.couplings[0].type == "exact"
    members = {(m["block"], m["mode"]) for m in ab.couplings[0].members}
    assert members == {("A", "samples"), ("B", "samples")}


# --- Tests: nested ---

def test_enumerate_nested_blocked_by_default():
    """Nested relations are excluded by default."""
    g = RelationGraph.from_config(_nested_config())
    c = EnumerationConstraints()
    candidates = enumerate_candidates(g, c)
    assert len(candidates) == 0


def test_enumerate_nested_allowed():
    """With allow_nested=True, nested relation candidates are included."""
    g = RelationGraph.from_config(_nested_config())
    c = EnumerationConstraints(allow_nested=True)
    candidates = enumerate_candidates(g, c)
    assert len(candidates) == 1
    assert candidates[0].couplings[0].type == "nested"


# --- Tests: disconnected / zero candidates ---

def test_enumerate_disconnected():
    """Blocks with no relations produce zero candidates."""
    g = RelationGraph.from_config(_disconnected_config())
    c = EnumerationConstraints()
    candidates = enumerate_candidates(g, c)
    assert len(candidates) == 0


# --- Tests: constraints ---

def test_enumerate_min_shared_fraction():
    """min_shared_fraction=1.0 requires all blocks to be shared."""
    g = RelationGraph.from_config(_chain_config(), _chain_metadata())
    c = EnumerationConstraints(min_shared_fraction=1.0)
    candidates = enumerate_candidates(g, c)

    # (A,B): 2/2=1.0 ok, (A,C): 2/2=1.0 ok, (A,B,C): 3/3=1.0 ok
    assert len(candidates) == 3


def test_enumerate_no_partial_coupling():
    """allow_partial_coupling=False requires every block to participate in a relation."""
    g = RelationGraph.from_config(_chain_config(), _chain_metadata())
    c = EnumerationConstraints(allow_partial_coupling=False)
    candidates = enumerate_candidates(g, c)

    # (A,B): both shared, ok. (A,C): both shared, ok.
    # (A,B,C): all shared (A connects to both B and C), ok.
    block_sets = [tuple(sorted(cand.blocks)) for cand in candidates]
    assert ("A", "B") in block_sets
    assert ("A", "C") in block_sets
    assert ("A", "B", "C") in block_sets


def test_enumerate_frozen_modes():
    """allow_frozen_modes adds a frozen variant per candidate."""
    g = RelationGraph.from_config(_chain_config(), _chain_metadata())
    c = EnumerationConstraints(max_blocks=2, allow_frozen_modes=True)
    candidates = enumerate_candidates(g, c)

    # 2 standard + 2 frozen = 4
    assert len(candidates) == 4

    frozen = [cand for cand in candidates if "frozen" in cand.id]
    assert len(frozen) == 2

    # Check frozen candidate has freeze status on non-shared modes
    ab_frozen = next(cand for cand in frozen if set(cand.blocks) == {"A", "B"})
    ma_map = {(ma.block, ma.mode): ma for ma in ab_frozen.mode_assignments}
    assert ma_map[("A", "samples")].status == "decompose"
    assert ma_map[("A", "genes")].status == "freeze"
    assert ma_map[("B", "cpgs")].status == "freeze"


# --- Tests: candidate serialization ---

def test_candidate_to_dict():
    g = RelationGraph.from_config(_chain_config(), _chain_metadata())
    c = EnumerationConstraints(max_blocks=2)
    candidates = enumerate_candidates(g, c)

    d = candidates[0].to_dict()
    assert "id" in d
    assert "blocks" in d
    assert "mode_assignments" in d
    assert "couplings" in d
    assert "solver_family" in d
    assert d["solver_family"] == "CoupledMWCA"


def test_candidate_to_dict_roundtrip():
    """to_dict produces serializable dicts."""
    import json
    g = RelationGraph.from_config(_chain_config(), _chain_metadata())
    c = EnumerationConstraints()
    candidates = enumerate_candidates(g, c)

    for cand in candidates:
        s = json.dumps(cand.to_dict())
        loaded = json.loads(s)
        assert loaded["id"] == cand.id
