"""Snakemake script: enumerate valid decomposition candidates."""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pakunoda.graph import RelationGraph
from pakunoda.candidate import enumerate_candidates, EnumerationConstraints

# Load graph JSON
with open(snakemake.input.graph) as f:
    graph_dict = json.load(f)

# Build typed graph
graph = RelationGraph.from_graph_json(snakemake.config, graph_dict)

# Build constraints from config
constraints = EnumerationConstraints.from_config(snakemake.config)

# Enumerate
candidates = enumerate_candidates(graph, constraints)

# Serialize
output = {
    "project_id": snakemake.config["project"]["id"],
    "num_candidates": len(candidates),
    "constraints": {
        "max_blocks": constraints.max_blocks,
        "min_shared_fraction": constraints.min_shared_fraction,
        "allow_partial_coupling": constraints.allow_partial_coupling,
        "allow_nested": constraints.allow_nested,
        "allow_frozen_modes": constraints.allow_frozen_modes,
    },
    "candidates": [c.to_dict() for c in candidates],
}

with open(snakemake.output.candidates, "w") as f:
    json.dump(output, f, indent=2)
