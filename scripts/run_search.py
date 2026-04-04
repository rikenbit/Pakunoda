"""Snakemake script: run Optuna search for each candidate."""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pakunoda.search.search_space import build_search_space
from pakunoda.search.objective import Objective, mock_solver
from pakunoda.search.study import create_or_load_study, run_study, list_trials_summary, get_best_trial_summary

# Load search manifest
with open(snakemake.input.search_manifest) as f:
    search_manifest = json.load(f)

search_config = snakemake.config.get("search", {})
max_trials = search_config.get("max_trials", 20)
seed = search_config.get("seed", 42)
storage_path = snakemake.params.storage_path
use_mock = search_config.get("mock", False)

space = build_search_space(search_config)

# Determine solver function
# Future: if not mock, call R/mwTensor bridge
# For now, mock_solver is used when mock=True or R is unavailable
solver_fn = mock_solver

candidate_results = []

for candidate_entry in search_manifest["candidates"]:
    candidate_id = candidate_entry["candidate_id"]
    problem_file = candidate_entry["problem_file"]

    with open(problem_file) as f:
        problem = json.load(f)

    # Load tensor data
    tensors_data = {}
    for tensor in problem.get("tensors", []):
        tid = tensor["id"]
        if os.path.exists(tensor["data_file"]):
            tensors_data[tid] = np.load(tensor["data_file"])

    # Load masks
    masks = {}
    for tid, mask_path in candidate_entry.get("mask_files", {}).items():
        if os.path.exists(mask_path):
            masks[tid] = np.load(mask_path)

    # Create objective
    objective = Objective(
        search_space=space,
        tensors_data=tensors_data,
        masks=masks,
        problem=problem,
        solver_fn=solver_fn,
    )

    # Create/load study for this candidate
    study_name = "{}_{}".format(snakemake.config["project"]["id"], candidate_id)
    study = create_or_load_study(study_name, storage_path)

    # Run
    study = run_study(study, objective, n_trials=max_trials, seed=seed)

    # Extract results
    trials = list_trials_summary(study)
    best = get_best_trial_summary(study)

    candidate_results.append({
        "candidate_id": candidate_id,
        "study_name": study_name,
        "num_trials": len(trials),
        "best_trial": best,
        "trials": trials,
    })

# Write results manifest
results = {
    "project_id": snakemake.config["project"]["id"],
    "total_candidates": len(candidate_results),
    "max_trials_per_candidate": max_trials,
    "storage_path": storage_path,
    "candidates": candidate_results,
}

with open(snakemake.output.search_results, "w") as f:
    json.dump(results, f, indent=2, default=str)
