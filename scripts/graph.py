"""Snakemake script: build the relation graph."""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pakunoda.relation_graph import build_relation_graph, validate_graph, graph_to_json

# Load block metadata
block_metadata = {}
for meta_file in snakemake.input.metas:
    with open(meta_file) as f:
        meta = json.load(f)
    block_metadata[meta["block_id"]] = meta

# Build graph
graph = build_relation_graph(snakemake.config, block_metadata)

# Validate graph consistency
errors = validate_graph(graph)
if errors:
    raise ValueError("Graph validation failed:\n  " + "\n  ".join(errors))

with open(snakemake.output.graph, "w") as f:
    f.write(graph_to_json(graph))
