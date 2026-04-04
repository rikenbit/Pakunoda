"""Snakemake script: aggregate all scores into summary JSON and TSV."""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pakunoda.scorer import summarize_scores, scores_to_tsv_rows

# Load score manifest
with open(snakemake.input.score_manifest) as f:
    score_manifest = json.load(f)

# Load all scores
scores = []
for entry in score_manifest["scores"]:
    with open(entry["score_file"]) as f:
        scores.append(json.load(f))

# Build summary
summary = summarize_scores(scores)

# Add config snapshot
summary["config_snapshot"] = {
    "project_id": snakemake.config["project"]["id"],
    "num_blocks": len(snakemake.config["blocks"]),
    "num_relations": len(snakemake.config.get("relations", [])),
    "solver_family": snakemake.config.get("solver", {}).get("family", "CoupledMWCA"),
    "max_rank": snakemake.config.get("search", {}).get("max_rank", 10),
    "mock": snakemake.config.get("search", {}).get("mock", False),
}

# Write JSON summary
with open(snakemake.output.summary_json, "w") as f:
    json.dump(summary, f, indent=2)

# Write TSV table
tsv_rows = scores_to_tsv_rows(scores)
with open(snakemake.output.summary_tsv, "w") as f:
    f.write("\n".join(tsv_rows) + "\n")
