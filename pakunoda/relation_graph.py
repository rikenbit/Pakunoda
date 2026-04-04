"""Relation graph construction for Pakunoda.

The relation graph represents how blocks are connected through shared or related modes.
Nodes represent (block_id, mode_name) pairs.
Edges represent relations (exact or nested) between mode pairs.
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import List


def build_relation_graph(config: dict, block_metadata: dict) -> dict:
    """Build a relation graph from config and ingested metadata.

    Args:
        config: Validated Pakunoda config dict.
        block_metadata: Dict mapping block_id -> ingest metadata (shape, names, etc).

    Returns:
        Graph dict with 'nodes', 'edges', and 'adjacency'.
    """
    nodes = []
    node_set = set()

    # Add all (block, mode) pairs as nodes
    for block in config["blocks"]:
        bid = block["id"]
        meta = block_metadata.get(bid, {})
        shape = meta.get("shape", [])

        for i, mode in enumerate(block["modes"]):
            node_id = f"{bid}:{mode}"
            if node_id not in node_set:
                dim = shape[i] if i < len(shape) else None
                nodes.append({
                    "id": node_id,
                    "block": bid,
                    "mode": mode,
                    "dimension": dim,
                })
                node_set.add(node_id)

    # Build edges from relations
    edges = []
    adjacency = defaultdict(list)

    for rel in config.get("relations", []):
        between = rel["between"]
        rtype = rel["type"]

        # For pairwise relations, connect all pairs in 'between'
        for i in range(len(between)):
            for j in range(i + 1, len(between)):
                src = f"{between[i]['block']}:{between[i]['mode']}"
                dst = f"{between[j]['block']}:{between[j]['mode']}"

                edge = {
                    "source": src,
                    "target": dst,
                    "type": rtype,
                }
                if rtype == "nested" and rel.get("mapping"):
                    edge["mapping"] = rel["mapping"]

                edges.append(edge)
                adjacency[src].append(dst)
                adjacency[dst].append(src)

    return {
        "nodes": nodes,
        "edges": edges,
        "adjacency": dict(adjacency),
    }


def validate_graph(graph: dict) -> List[str]:
    """Validate the relation graph for consistency.

    Returns:
        List of error messages. Empty if valid.
    """
    errors = []

    # Check that exact-related modes have the same dimension
    for edge in graph["edges"]:
        if edge["type"] == "exact":
            src_node = next((n for n in graph["nodes"] if n["id"] == edge["source"]), None)
            dst_node = next((n for n in graph["nodes"] if n["id"] == edge["target"]), None)

            if src_node and dst_node:
                src_dim = src_node.get("dimension")
                dst_dim = dst_node.get("dimension")
                if src_dim is not None and dst_dim is not None and src_dim != dst_dim:
                    errors.append(
                        f"Exact relation {edge['source']} <-> {edge['target']}: "
                        f"dimension mismatch ({src_dim} != {dst_dim})"
                    )

    return errors


def graph_to_json(graph: dict) -> str:
    """Serialize graph to JSON."""
    return json.dumps(graph, indent=2)
