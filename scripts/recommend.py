"""Snakemake script: generate recommendation from search results."""

import json
import os
import sys

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pakunoda.search.recommend import generate_recommendation

# Load search results
with open(snakemake.input.search_results) as f:
    results = json.load(f)

# Build candidate_results for the recommender
candidate_results = []
for candidate in results["candidates"]:
    candidate_results.append({
        "candidate_id": candidate["candidate_id"],
        "best_trial": candidate.get("best_trial"),
        "num_trials": candidate.get("num_trials", 0),
    })

config_snapshot = {
    "project_id": snakemake.config["project"]["id"],
    "solver_family": snakemake.config.get("solver", {}).get("family", "CoupledMWCA"),
    "max_trials": snakemake.config.get("search", {}).get("max_trials", 20),
    "masking_scheme": snakemake.config.get("search", {}).get("masking", {}).get("scheme", "elementwise"),
    "masking_fraction": snakemake.config.get("search", {}).get("masking", {}).get("fraction", 0.1),
}

recommendation = generate_recommendation(candidate_results, config_snapshot)

# Write as YAML
with open(snakemake.output.recommendation, "w") as f:
    yaml.dump(recommendation, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
