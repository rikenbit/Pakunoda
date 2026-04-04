"""Snakemake script: compile the problem definition for mwTensor."""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pakunoda.compiler import compile_problem, problem_to_json

# Load graph
with open(snakemake.input.graph) as f:
    graph = json.load(f)

# Load block metadata
block_metadata = {}
for meta_file in snakemake.input.metas:
    with open(meta_file) as f:
        meta = json.load(f)
    block_metadata[meta["block_id"]] = meta

# Add canonical file paths to metadata
for i, canonical_file in enumerate(snakemake.input.canonicals):
    bid = snakemake.config["blocks"][i]["id"]
    if bid in block_metadata:
        block_metadata[bid]["canonical_file"] = canonical_file

# Compile
problem = compile_problem(snakemake.config, graph, block_metadata)

with open(snakemake.output.problem, "w") as f:
    f.write(problem_to_json(problem))
