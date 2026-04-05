"""Snakemake script: build the relation graph.

If nested relations were preprocessed, this script augments the config
with aggregated blocks and replaces nested relations with exact ones
before building the graph.
"""

import json
import sys
import os
import copy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pakunoda.relation_graph import build_relation_graph, validate_graph, graph_to_json

# Load block metadata
block_metadata = {}
for meta_file in snakemake.input.metas:
    with open(meta_file) as f:
        meta = json.load(f)
    block_metadata[meta["block_id"]] = meta

# Load nested preprocessing manifest
with open(snakemake.input.nested_manifest) as f:
    nested_manifest = json.load(f)

# Augment config with aggregated blocks and replaced relations
effective_config = copy.deepcopy(dict(snakemake.config))

for agg_block in nested_manifest.get("aggregated_blocks", []):
    # Add aggregated block to blocks list
    effective_config["blocks"].append({
        "id": agg_block["id"],
        "kind": agg_block["kind"],
        "modes": agg_block["modes"],
        "file": agg_block["canonical_file"],
    })
    # Add metadata for the aggregated block
    block_metadata[agg_block["id"]] = {
        "block_id": agg_block["id"],
        "shape": agg_block["shape"],
        "row_names": agg_block.get("row_names"),
        "col_names": agg_block.get("col_names"),
    }

# Replace nested relations with exact ones
for replacement in nested_manifest.get("replaced_relations", []):
    # Remove the original nested relation
    orig = replacement["original_between"]
    effective_config["relations"] = [
        r for r in effective_config["relations"]
        if not (
            r.get("type") == "nested"
            and any(
                ep.get("block") == orig[0]["block"] and ep.get("mode") == orig[0]["mode"]
                for ep in r.get("between", [])
            )
        )
    ]
    # Add the replacement exact relation
    effective_config["relations"].append({
        "type": "exact",
        "between": replacement["replacement_between"],
    })

# Build graph with effective config
graph = build_relation_graph(effective_config, block_metadata)

# Validate graph consistency
errors = validate_graph(graph)
if errors:
    raise ValueError("Graph validation failed:\n  " + "\n  ".join(errors))

with open(snakemake.output.graph, "w") as f:
    f.write(graph_to_json(graph))
