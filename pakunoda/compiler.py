"""Problem compiler for mwTensor.

Generates a structured JSON problem definition that mwTensor's CoupledMWCA can consume.

Two compilation paths exist for historical reasons:

- compile_problem(config, graph_dict, block_metadata)
    Project-level compile. Takes the full config and the dict-based relation graph
    (output of the ``graph`` rule), and produces a single problem.json covering all
    blocks.  Used by the ``compile`` Snakemake rule.  This is the original MVP path
    and is kept for backward compatibility / single-shot use.

- compile_candidate(candidate_dict, config, block_metadata)
    Candidate-level compile. Takes one serialized Candidate (from the ``enumerate``
    stage) and produces a problem.json scoped to that candidate's block subset,
    couplings, and mode assignments.  Used by the ``compile_candidates`` rule.
    This is the primary path for the search pipeline.

Rank semantics:
    ``rank`` sets the number of components for every factor (both common and
    specific) in CoupledMWCA.  This is a simplification; future versions may
    allow per-factor rank.  The value is sourced from (in priority order):
    1. candidate.rank  (set by search trial)
    2. config search.max_rank  (default 10)
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional

from pakunoda import __version__


def compile_problem(config, graph, block_metadata):
    # type: (dict, dict, dict) -> dict
    """Compile a decomposition problem definition for mwTensor.

    Project-level compile: covers all blocks in config.

    Args:
        config: Validated Pakunoda config.
        graph: Relation graph from build_relation_graph (dict).
        block_metadata: Dict mapping block_id -> ingest metadata.

    Returns:
        Problem definition dict ready for mwTensor.
    """
    solver_config = config.get("solver", {})
    search_config = config.get("search", {})

    tensors = []
    for block in config["blocks"]:
        bid = block["id"]
        meta = block_metadata.get(bid, {})
        tensors.append({
            "id": bid,
            "kind": block["kind"],
            "modes": block["modes"],
            "shape": meta.get("shape", []),
            "data_file": meta.get("canonical_file", block["file"]),
        })

    mode_groups = _build_mode_groups(graph)

    couplings = []
    for group_id, members in enumerate(mode_groups):
        if len(members) > 1:
            couplings.append({
                "group_id": group_id,
                "type": "exact",
                "members": [{"block": m["block"], "mode": m["mode"]} for m in members],
            })

    nested_rels = []
    for edge in graph["edges"]:
        if edge["type"] == "nested":
            nested_rels.append({
                "source": edge["source"],
                "target": edge["target"],
                "mapping": edge.get("mapping"),
            })

    problem = {
        "version": __version__,
        "project_id": config["project"]["id"],
        "solver": {
            "family": solver_config.get("family", "CoupledMWCA"),
            "init_policy": "random",
            "seed": None,
        },
        "tensors": tensors,
        "couplings": couplings,
        "nested_relations": nested_rels,
        "rank": search_config.get("max_rank", 10),
        "search": {
            "max_rank": search_config.get("max_rank", 10),
        },
    }

    return problem


def _build_mode_groups(graph):
    # type: (dict) -> List[List[Dict]]
    """Build equivalence classes of modes connected by exact relations.

    Uses union-find over exact edges to group modes that must share dimensions.
    """
    node_ids = [n["id"] for n in graph["nodes"]]
    parent = {nid: nid for nid in node_ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for edge in graph["edges"]:
        if edge["type"] == "exact":
            union(edge["source"], edge["target"])

    groups = {}
    for nid in node_ids:
        root = find(nid)
        if root not in groups:
            groups[root] = []
        block, mode = nid.split(":", 1)
        groups[root].append({"block": block, "mode": mode})

    return list(groups.values())


def compile_candidate(candidate, config, block_metadata):
    # type: (dict, dict, dict) -> dict
    """Compile a single Candidate (as dict) into a CoupledMWCA problem definition.

    Args:
        candidate: Candidate.to_dict() output.
        config: Validated Pakunoda config.
        block_metadata: Dict mapping block_id -> ingest metadata.

    Returns:
        Problem definition dict for mwTensor.  Key fields consumed by the solver:

        - solver.family       -> selects mwTensor algorithm
        - solver.init_policy  -> passed to initCoupledMWCA (random/svd/nonneg_random)
        - solver.seed         -> reproducibility seed for initCoupledMWCA
        - rank                -> sets dims for all common and specific factors
        - tensors[].data_file -> loaded as Xs
        - couplings[]         -> builds common_model (shared factor labels)
        - mode_assignments[]  -> sharing=common/specific sets factor labels;
                                 status=freeze sets decomp=FALSE for that factor
        - nested_relations[]  -> NOT consumed by solver; raises error at run time
    """
    block_defs = {b["id"]: b for b in config["blocks"]}
    search_config = config.get("search", {})

    # Tensors: only include blocks in this candidate
    tensors = []
    for bid in candidate["blocks"]:
        block = block_defs[bid]
        meta = block_metadata.get(bid, {})
        tensors.append({
            "id": bid,
            "kind": block["kind"],
            "modes": block["modes"],
            "shape": meta.get("shape", []),
            "data_file": meta.get("canonical_file", block["file"]),
        })

    # Couplings: separate exact from nested
    all_couplings = candidate.get("couplings", [])
    exact_couplings = [c for c in all_couplings if c["type"] == "exact"]
    nested_rels = [c for c in all_couplings if c["type"] == "nested"]

    # Mode assignments
    mode_assignments = candidate.get("mode_assignments", [])

    # Rank: candidate-level (from search) > config-level (max_rank)
    rank = candidate.get("rank")
    if rank is None:
        rank = search_config.get("max_rank", 10)

    problem = {
        "version": __version__,
        "candidate_id": candidate["id"],
        "project_id": config["project"]["id"],
        "solver": {
            "family": candidate.get("solver_family", "CoupledMWCA"),
            "init_policy": "random",
            "seed": None,
        },
        "tensors": tensors,
        "couplings": exact_couplings,
        "nested_relations": nested_rels,
        "mode_assignments": mode_assignments,
        "rank": rank,
        "search": {
            "max_rank": search_config.get("max_rank", 10),
        },
    }

    return problem


def patch_problem_for_trial(problem, params):
    # type: (dict, dict) -> dict
    """Create a copy of a problem dict with trial-specific hyperparameters overlaid.

    Used by the search objective to inject Optuna trial params into the problem
    before passing to the solver function.

    Args:
        problem: Base problem dict from compile_candidate.
        params: Trial params from SearchSpace.suggest() — must have 'rank',
                'init_policy'; may have 'weight_scaling'.

    Returns:
        Shallow-copied problem dict with solver/rank overridden.
    """
    patched = dict(problem)
    patched["rank"] = params["rank"]
    patched["solver"] = dict(problem.get("solver", {}))
    patched["solver"]["init_policy"] = params.get("init_policy", "random")
    return patched


def problem_to_json(problem):
    # type: (dict) -> str
    """Serialize problem to JSON."""
    return json.dumps(problem, indent=2)
