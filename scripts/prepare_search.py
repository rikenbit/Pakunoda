"""Snakemake script: prepare search — load data, create masks, build search spaces."""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pakunoda.search.masking import create_masks_for_tensors
from pakunoda.search.search_space import build_search_space

# Load compiled manifest
with open(snakemake.input.compiled_manifest) as f:
    compiled_manifest = json.load(f)

search_config = snakemake.config.get("search", {})
masking_config = search_config.get("masking", {})
mask_fraction = masking_config.get("fraction", 0.1)
mask_seed = search_config.get("seed", 42)

# Build search space
space = build_search_space(search_config)

outdir = snakemake.params.outdir
os.makedirs(outdir, exist_ok=True)

# For each candidate, load data and create masks
preparations = []
for entry in compiled_manifest["problems"]:
    candidate_id = entry["candidate_id"]
    problem_file = entry["problem_file"]

    with open(problem_file) as f:
        problem = json.load(f)

    # Load tensor data and create masks
    candidate_dir = os.path.join(outdir, candidate_id)
    os.makedirs(candidate_dir, exist_ok=True)

    tensors_data = {}
    for tensor in problem.get("tensors", []):
        tid = tensor["id"]
        data_file = tensor["data_file"]
        if os.path.exists(data_file):
            tensors_data[tid] = np.load(data_file)

    masks = create_masks_for_tensors(tensors_data, mask_fraction, mask_seed)

    # Save masks as .npy
    mask_files = {}
    for tid, mask in masks.items():
        mask_path = os.path.join(candidate_dir, "{}.mask.npy".format(tid))
        np.save(mask_path, mask)
        mask_files[tid] = mask_path

    preparations.append({
        "candidate_id": candidate_id,
        "problem_file": problem_file,
        "mask_files": mask_files,
    })

# Save preparation manifest
manifest = {
    "project_id": snakemake.config["project"]["id"],
    "search_space": space.to_dict(),
    "masking": {
        "scheme": masking_config.get("scheme", "elementwise"),
        "fraction": mask_fraction,
        "seed": mask_seed,
    },
    "candidates": preparations,
}

with open(snakemake.output.search_manifest, "w") as f:
    json.dump(manifest, f, indent=2)
