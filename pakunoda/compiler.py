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
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional

from pakunoda import __version__


def compile_problem(config: dict, graph: dict, block_metadata: dict) -> dict:
    """Compile a decomposition problem definition for mwTensor.

    Args:
        config: Validated Pakunoda config.
        graph: Relation graph from build_relation_graph.
        block_metadata: Dict mapping block_id -> ingest metadata.

    Returns:
        Problem definition dict ready for mwTensor.
    """
    solver_config = config.get("solver", {})
    search_config = config.get("search", {})

    # Build the tensor list for mwTensor
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

    # Build the coupling structure
    # For CoupledMWCA, we need to express which modes are shared across tensors.
    # Group modes by their equivalence classes (connected components in exact relations).
    mode_groups = _build_mode_groups(graph)

    couplings = []
    for group_id, members in enumerate(mode_groups):
        if len(members) > 1:
            couplings.append({
                "group_id": group_id,
                "type": "exact",
                "members": [{"block": m["block"], "mode": m["mode"]} for m in members],
            })

    # Build nested relations separately
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
        },
        "tensors": tensors,
        "couplings": couplings,
        "nested_relations": nested_rels,
        "search": {
            "max_rank": search_config.get("max_rank", 10),
        },
    }

    return problem


def _build_mode_groups(graph: dict) -> List[List[Dict]]:
    """Build equivalence classes of modes connected by exact relations.

    Uses union-find over exact edges to group modes that must share dimensions.
    """
    # Parse node IDs into (block, mode) pairs
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

    # Union exact-related modes
    for edge in graph["edges"]:
        if edge["type"] == "exact":
            union(edge["source"], edge["target"])

    # Group by root
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
        Problem definition dict for mwTensor.
    """
    # Build block lookup
    block_defs = {b["id"]: b for b in config["blocks"]}

    # Only include blocks in this candidate
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

    # Couplings from candidate
    couplings = candidate.get("couplings", [])

    # Separate nested relations
    nested_rels = [c for c in couplings if c["type"] == "nested"]
    exact_couplings = [c for c in couplings if c["type"] == "exact"]

    # Mode assignments
    mode_assignments = candidate.get("mode_assignments", [])

    search_config = config.get("search", {})

    problem = {
        "version": __version__,
        "candidate_id": candidate["id"],
        "project_id": config["project"]["id"],
        "solver": {
            "family": candidate.get("solver_family", "CoupledMWCA"),
        },
        "tensors": tensors,
        "couplings": exact_couplings,
        "nested_relations": nested_rels,
        "mode_assignments": mode_assignments,
        "rank": candidate.get("rank"),
        "search": {
            "max_rank": search_config.get("max_rank", 10),
        },
    }

    return problem


def problem_to_json(problem: dict) -> str:
    """Serialize problem to JSON."""
    return json.dumps(problem, indent=2)
