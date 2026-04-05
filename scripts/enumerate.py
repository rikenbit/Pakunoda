"""Snakemake script: enumerate valid decomposition candidates.

If nested relations were preprocessed, augments the config with
aggregated blocks before building the typed graph for enumeration.
"""

import json
import sys
import os
import copy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pakunoda.graph import RelationGraph
from pakunoda.candidate import enumerate_candidates, EnumerationConstraints

# Load graph JSON (already includes aggregated blocks/exact replacements)
with open(snakemake.input.graph) as f:
    graph_dict = json.load(f)

# Load nested manifest to augment config for RelationGraph.from_graph_json
with open(snakemake.input.nested_manifest) as f:
    nested_manifest = json.load(f)

effective_config = copy.deepcopy(dict(snakemake.config))
for agg_block in nested_manifest.get("aggregated_blocks", []):
    effective_config["blocks"].append({
        "id": agg_block["id"],
        "kind": agg_block["kind"],
        "modes": agg_block["modes"],
        "file": agg_block["canonical_file"],
    })

# Build typed graph from the augmented graph JSON and effective config
graph = RelationGraph.from_graph_json(effective_config, graph_dict)

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
