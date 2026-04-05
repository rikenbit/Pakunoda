"""Tests for compile → solver bridge contract.

Verifies that problem JSON from compile_candidate has the correct
structure for run_candidate.R to consume and map onto mwTensor's
CoupledMWCAParams.

These tests do NOT call R. They verify the Python-side contract:
the problem JSON fields that R bridge depends on are present and
correctly structured.
"""

import pytest

from pakunoda.compiler import compile_candidate, patch_problem_for_trial
from pakunoda.graph import RelationGraph
from pakunoda.candidate import enumerate_candidates, EnumerationConstraints


# ---- Fixtures ----

def _two_block_config():
    """2 blocks, 1 exact relation (shared samples mode)."""
    return {
        "project": {"id": "test"},
        "blocks": [
            {"id": "expr", "kind": "matrix", "modes": ["samples", "genes"], "file": "e.tsv"},
            {"id": "meth", "kind": "matrix", "modes": ["samples", "cpgs"], "file": "m.tsv"},
        ],
        "relations": [
            {
                "type": "exact",
                "between": [
                    {"block": "expr", "mode": "samples"},
                    {"block": "meth", "mode": "samples"},
                ],
            },
        ],
        "solver": {"family": "CoupledMWCA"},
        "search": {"max_rank": 3},
    }


def _two_block_meta():
    return {
        "expr": {"shape": [5, 4], "canonical_file": "expr.npy"},
        "meth": {"shape": [5, 3], "canonical_file": "meth.npy"},
    }


def _three_block_config():
    """3 blocks, 2 exact relations (chain: meth--samples--expr--genes--inter)."""
    return {
        "project": {"id": "test"},
        "blocks": [
            {"id": "expr", "kind": "matrix", "modes": ["samples", "genes"], "file": "e.tsv"},
            {"id": "meth", "kind": "matrix", "modes": ["samples", "cpgs"], "file": "m.tsv"},
            {"id": "inter", "kind": "matrix", "modes": ["genes", "proteins"], "file": "i.tsv"},
        ],
        "relations": [
            {
                "type": "exact",
                "between": [
                    {"block": "expr", "mode": "samples"},
                    {"block": "meth", "mode": "samples"},
                ],
            },
            {
                "type": "exact",
                "between": [
                    {"block": "expr", "mode": "genes"},
                    {"block": "inter", "mode": "genes"},
                ],
            },
        ],
        "solver": {"family": "CoupledMWCA"},
        "search": {"max_rank": 2},
    }


def _three_block_meta():
    return {
        "expr": {"shape": [5, 4], "canonical_file": "expr.npy"},
        "meth": {"shape": [5, 3], "canonical_file": "meth.npy"},
        "inter": {"shape": [4, 3], "canonical_file": "inter.npy"},
    }


def _compile_first_candidate(config, meta, **enum_kwargs):
    g = RelationGraph.from_config(config, meta)
    candidates = enumerate_candidates(g, EnumerationConstraints(**enum_kwargs))
    assert len(candidates) > 0
    return compile_candidate(candidates[0].to_dict(), config, meta), candidates[0]


# ---- Tests: common_model factor label structure ----

class TestFactorLabels:
    """Verify that couplings and mode_assignments produce correct factor labels."""

    def test_shared_modes_get_same_factor_label(self):
        """Modes in the same coupling group should produce the same factor label
        when the R bridge processes them."""
        problem, _ = _compile_first_candidate(_two_block_config(), _two_block_meta())

        # couplings should have one group with expr:samples and meth:samples
        assert len(problem["couplings"]) == 1
        coupling = problem["couplings"][0]
        members = coupling["members"]
        blocks_in = {m["block"] for m in members}
        assert blocks_in == {"expr", "meth"}
        modes_in = {m["mode"] for m in members}
        assert modes_in == {"samples"}

    def test_non_shared_modes_are_specific(self):
        """Non-shared modes should have sharing=specific."""
        problem, _ = _compile_first_candidate(_two_block_config(), _two_block_meta())
        ma_map = {(m["block"], m["mode"]): m for m in problem["mode_assignments"]}

        # genes and cpgs are non-shared
        assert ma_map[("expr", "genes")]["sharing"] == "specific"
        assert ma_map[("meth", "cpgs")]["sharing"] == "specific"

    def test_all_modes_have_assignments(self):
        """Every mode of every block in the candidate has a mode_assignment."""
        problem, cand = _compile_first_candidate(_two_block_config(), _two_block_meta())

        expected_modes = set()
        for bid in cand.blocks:
            block = next(b for b in _two_block_config()["blocks"] if b["id"] == bid)
            for mode in block["modes"]:
                expected_modes.add((bid, mode))

        actual_modes = {(m["block"], m["mode"]) for m in problem["mode_assignments"]}
        assert actual_modes == expected_modes


class TestThreeBlockChain:
    """Verify correct structure for a 3-block chain with 2 coupling groups."""

    def test_two_coupling_groups(self):
        config = _three_block_config()
        meta = _three_block_meta()
        g = RelationGraph.from_config(config, meta)
        # Get the 3-block candidate
        candidates = enumerate_candidates(g, EnumerationConstraints())
        three_block = [c for c in candidates if len(c.blocks) == 3]
        assert len(three_block) == 1

        problem = compile_candidate(three_block[0].to_dict(), config, meta)
        assert len(problem["couplings"]) == 2

    def test_chain_mode_assignments(self):
        config = _three_block_config()
        meta = _three_block_meta()
        g = RelationGraph.from_config(config, meta)
        candidates = enumerate_candidates(g, EnumerationConstraints())
        three_block = [c for c in candidates if len(c.blocks) == 3][0]
        problem = compile_candidate(three_block.to_dict(), config, meta)

        ma_map = {(m["block"], m["mode"]): m for m in problem["mode_assignments"]}

        # Shared modes
        assert ma_map[("expr", "samples")]["sharing"] == "common"
        assert ma_map[("meth", "samples")]["sharing"] == "common"
        assert ma_map[("expr", "genes")]["sharing"] == "common"
        assert ma_map[("inter", "genes")]["sharing"] == "common"

        # Non-shared modes
        assert ma_map[("meth", "cpgs")]["sharing"] == "specific"
        assert ma_map[("inter", "proteins")]["sharing"] == "specific"


# ---- Tests: freeze ----

class TestFreeze:
    """Verify freeze semantics in problem JSON."""

    def test_frozen_modes_are_non_shared(self):
        """In the frozen variant, only non-shared modes should be frozen."""
        config = _two_block_config()
        meta = _two_block_meta()
        g = RelationGraph.from_config(config, meta)
        candidates = enumerate_candidates(g, EnumerationConstraints(allow_frozen_modes=True))

        frozen_cands = [c for c in candidates if "frozen" in c.id]
        assert len(frozen_cands) > 0
        problem = compile_candidate(frozen_cands[0].to_dict(), config, meta)

        ma_map = {(m["block"], m["mode"]): m for m in problem["mode_assignments"]}

        # Shared modes should NOT be frozen
        assert ma_map[("expr", "samples")]["status"] == "decompose"
        assert ma_map[("meth", "samples")]["status"] == "decompose"

        # Non-shared modes SHOULD be frozen
        assert ma_map[("expr", "genes")]["status"] == "freeze"
        assert ma_map[("meth", "cpgs")]["status"] == "freeze"

    def test_frozen_modes_are_marked_specific(self):
        """Frozen modes have sharing=specific."""
        config = _two_block_config()
        meta = _two_block_meta()
        g = RelationGraph.from_config(config, meta)
        candidates = enumerate_candidates(g, EnumerationConstraints(allow_frozen_modes=True))

        frozen = [c for c in candidates if "frozen" in c.id][0]
        problem = compile_candidate(frozen.to_dict(), config, meta)

        for ma in problem["mode_assignments"]:
            if ma["status"] == "freeze":
                assert ma["sharing"] == "specific"

    def test_freeze_in_three_block_chain(self):
        """Freeze works correctly with multiple coupling groups."""
        config = _three_block_config()
        meta = _three_block_meta()
        g = RelationGraph.from_config(config, meta)
        candidates = enumerate_candidates(g, EnumerationConstraints(allow_frozen_modes=True))

        frozen = [c for c in candidates if "frozen" in c.id and len(c.blocks) == 3]
        assert len(frozen) > 0

        problem = compile_candidate(frozen[0].to_dict(), config, meta)
        ma_map = {(m["block"], m["mode"]): m for m in problem["mode_assignments"]}

        # Shared should be decompose
        assert ma_map[("expr", "samples")]["status"] == "decompose"
        assert ma_map[("expr", "genes")]["status"] == "decompose"

        # Non-shared should be freeze
        assert ma_map[("meth", "cpgs")]["status"] == "freeze"
        assert ma_map[("inter", "proteins")]["status"] == "freeze"


# ---- Tests: rank and init_policy propagation ----

class TestSolverParams:
    """Verify rank and solver settings reach the problem JSON correctly."""

    def test_rank_in_problem(self):
        problem, _ = _compile_first_candidate(_two_block_config(), _two_block_meta())
        assert problem["rank"] == 3  # from config max_rank

    def test_patch_overrides_rank_and_init(self):
        problem, _ = _compile_first_candidate(_two_block_config(), _two_block_meta())
        patched = patch_problem_for_trial(problem, {"rank": 1, "init_policy": "svd"})
        assert patched["rank"] == 1
        assert patched["solver"]["init_policy"] == "svd"
        # Original unchanged
        assert problem["rank"] == 3

    def test_solver_family(self):
        problem, _ = _compile_first_candidate(_two_block_config(), _two_block_meta())
        assert problem["solver"]["family"] == "CoupledMWCA"


# ---- Tests: nested relation rejection ----

class TestNestedRejection:
    """Nested relations should be in problem JSON but cause R bridge to error."""

    def test_nested_in_problem(self):
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
        problem = compile_candidate(candidates[0].to_dict(), config, meta)

        # nested_relations should be present and non-empty
        assert len(problem["nested_relations"]) > 0
        # R bridge will reject this at run time
