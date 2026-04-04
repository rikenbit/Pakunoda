"""End-to-end smoke test for the Pakunoda pipeline.

Runs the full pipeline programmatically (without Snakemake)
on the toy example data to verify all layers integrate correctly.
"""

import json
import os
import tempfile

import numpy as np
import pytest

from pakunoda.config import load_config
from pakunoda.io import read_tsv
from pakunoda.relation_graph import build_relation_graph, validate_graph
from pakunoda.graph import RelationGraph
from pakunoda.candidate import enumerate_candidates, EnumerationConstraints
from pakunoda.compiler import compile_candidate
from pakunoda.scorer import score_result, summarize_scores
from pakunoda.search.search_space import build_search_space
from pakunoda.search.masking import create_masks_for_tensors
from pakunoda.search.objective import Objective, mock_solver
from pakunoda.search.study import create_or_load_study, run_study, get_best_trial_summary
from pakunoda.search.recommend import generate_recommendation


EXAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "examples", "toy_heterogeneous")


@pytest.fixture
def toy_config():
    """Load and validate the toy example config."""
    import yaml
    config_path = os.path.join(EXAMPLE_DIR, "config.yaml")
    with open(config_path) as f:
        raw = yaml.safe_load(f)
    return load_config(raw, base_dir=EXAMPLE_DIR)


@pytest.fixture
def toy_data(toy_config):
    """Ingest and canonicalize the toy example data."""
    block_metadata = {}
    tensors_data = {}
    for block in toy_config["blocks"]:
        result = read_tsv(block["file"])
        block_metadata[block["id"]] = {
            "shape": result["shape"],
            "row_names": result["row_names"],
            "col_names": result["col_names"],
        }
        tensors_data[block["id"]] = result["data"]
    return block_metadata, tensors_data


def test_full_pipeline(toy_config, toy_data):
    """Verify that config → graph → enumerate → compile → score flows correctly."""
    block_metadata, tensors_data = toy_data

    # Graph
    graph_dict = build_relation_graph(toy_config, block_metadata)
    errors = validate_graph(graph_dict)
    assert errors == [], errors

    # Typed graph for enumeration
    graph = RelationGraph.from_config(toy_config, block_metadata)
    assert len(graph.get_block_ids()) == 3

    # Enumerate
    constraints = EnumerationConstraints.from_config(toy_config)
    candidates = enumerate_candidates(graph, constraints)
    assert len(candidates) >= 2  # at least (A,B) and (A,C)

    # Compile each candidate
    for cand in candidates:
        problem = compile_candidate(cand.to_dict(), toy_config, block_metadata)
        assert problem["project_id"] == "toy_heterogeneous"
        assert len(problem["tensors"]) == len(cand.blocks)
        assert len(problem["couplings"]) == len(cand.couplings)


def test_search_pipeline(toy_config, toy_data):
    """Verify that mask → search → recommend flows correctly."""
    block_metadata, tensors_data = toy_data

    graph = RelationGraph.from_config(toy_config, block_metadata)
    constraints = EnumerationConstraints.from_config(toy_config)
    candidates = enumerate_candidates(graph, constraints)

    search_config = toy_config.get("search", {})
    space = build_search_space(search_config)

    # Pick just the first candidate to keep the test fast
    cand = candidates[0]
    problem = compile_candidate(cand.to_dict(), toy_config, block_metadata)

    # Build data dict for this candidate's blocks
    cand_data = {bid: tensors_data[bid] for bid in cand.blocks}
    masks = create_masks_for_tensors(cand_data, fraction=0.1, seed=42)

    # Run a tiny search
    objective = Objective(space, cand_data, masks, problem, mock_solver)

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "test.sqlite3")
        study = create_or_load_study("test", storage_path)
        study = run_study(study, objective, n_trials=3, seed=42)

        best = get_best_trial_summary(study)
        assert best is not None
        assert best["value"] < float("inf")

        # Recommendation
        candidate_results = [{
            "candidate_id": cand.id,
            "best_trial": best,
            "num_trials": 3,
        }]
        rec = generate_recommendation(candidate_results)
        assert rec["best_by_error"]["candidate_id"] == cand.id
        assert "explanation" in rec
