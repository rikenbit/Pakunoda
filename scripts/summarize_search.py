"""Snakemake script: summarize search results into trials table and best JSON."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Load search results
with open(snakemake.input.search_results) as f:
    results = json.load(f)

# --- Trials TSV ---
tsv_header = [
    "candidate_id", "trial_number", "state", "imputation_rmse",
    "rank", "init_policy", "runtime_seconds", "total_params", "success",
]
tsv_rows = ["\t".join(tsv_header)]

for candidate in results["candidates"]:
    cid = candidate["candidate_id"]
    for trial in candidate.get("trials", []):
        row = [
            cid,
            str(trial.get("trial_number", "")),
            str(trial.get("state", "")),
            str(trial.get("value", "")),
            str(trial.get("rank", "")),
            str(trial.get("init_policy", "")),
            str(trial.get("runtime_seconds", "")),
            str(trial.get("total_params", "")),
            str(trial.get("success", "")),
        ]
        tsv_rows.append("\t".join(row))

with open(snakemake.output.trials_tsv, "w") as f:
    f.write("\n".join(tsv_rows) + "\n")

# --- Best JSON ---
best_per_candidate = []
for candidate in results["candidates"]:
    if candidate.get("best_trial"):
        best_per_candidate.append({
            "candidate_id": candidate["candidate_id"],
            "best_trial": candidate["best_trial"],
            "num_trials": candidate["num_trials"],
        })

# Sort by imputation error
best_per_candidate.sort(
    key=lambda x: x["best_trial"].get("value", float("inf"))
    if x["best_trial"].get("value") is not None
    else float("inf")
)

best = {
    "project_id": results["project_id"],
    "overall_best": best_per_candidate[0] if best_per_candidate else None,
    "by_candidate": best_per_candidate,
}

with open(snakemake.output.best_json, "w") as f:
    json.dump(best, f, indent=2, default=str)

# --- Summary TSV ---
summary_header = [
    "candidate_id", "best_rmse", "best_rank", "best_init_policy",
    "best_total_params", "num_trials",
]
summary_rows = ["\t".join(summary_header)]

for entry in best_per_candidate:
    bt = entry["best_trial"]
    row = [
        entry["candidate_id"],
        str(bt.get("value", "")),
        str(bt.get("rank", "")),
        str(bt.get("init_policy", "")),
        str(bt.get("total_params", "")),
        str(entry["num_trials"]),
    ]
    summary_rows.append("\t".join(row))

with open(snakemake.output.summary_tsv, "w") as f:
    f.write("\n".join(summary_rows) + "\n")
