"""Snakemake script: compile each candidate into a mwTensor problem definition.

Includes metadata from aggregated blocks (nested preprocessing) if present.
"""

import json
import os
import sys
import copy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pakunoda.compiler import compile_candidate, problem_to_json

# Load candidates
with open(snakemake.input.candidates) as f:
    candidates_data = json.load(f)

# Load block metadata
block_metadata = {}
for meta_file in snakemake.input.metas:
    with open(meta_file) as f:
        meta = json.load(f)
    block_metadata[meta["block_id"]] = meta

# Add canonical file paths for original blocks
for i, canonical_file in enumerate(snakemake.input.canonicals):
    bid = snakemake.config["blocks"][i]["id"]
    if bid in block_metadata:
        block_metadata[bid]["canonical_file"] = canonical_file

# Load nested manifest and add aggregated block metadata
with open(snakemake.input.nested_manifest) as f:
    nested_manifest = json.load(f)

effective_config = copy.deepcopy(dict(snakemake.config))
for agg_block in nested_manifest.get("aggregated_blocks", []):
    block_metadata[agg_block["id"]] = {
        "block_id": agg_block["id"],
        "shape": agg_block["shape"],
        "canonical_file": agg_block["canonical_file"],
        "row_names": None,
        "col_names": None,
    }
    effective_config["blocks"].append({
        "id": agg_block["id"],
        "kind": agg_block["kind"],
        "modes": agg_block["modes"],
        "file": agg_block["canonical_file"],
    })

# Compile each candidate
outdir = snakemake.params.outdir
compiled_files = []

for candidate in candidates_data["candidates"]:
    problem = compile_candidate(candidate, effective_config, block_metadata)
    outpath = os.path.join(outdir, "{}.problem.json".format(candidate["id"]))
    with open(outpath, "w") as f:
        f.write(problem_to_json(problem))
    compiled_files.append({
        "candidate_id": candidate["id"],
        "problem_file": outpath,
    })

# Write manifest
manifest = {
    "project_id": snakemake.config["project"]["id"],
    "num_compiled": len(compiled_files),
    "problems": compiled_files,
}

with open(snakemake.output.manifest, "w") as f:
    json.dump(manifest, f, indent=2)
