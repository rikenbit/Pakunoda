"""Snakemake script: score all candidate run results."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pakunoda.scorer import score_result

# Load run manifest
with open(snakemake.input.run_manifest) as f:
    run_manifest = json.load(f)

# Load compiled manifest for problem files
with open(snakemake.input.compiled_manifest) as f:
    compiled_manifest = json.load(f)

# Build problem file lookup
problem_files = {
    p["candidate_id"]: p["problem_file"]
    for p in compiled_manifest["problems"]
}

outdir = snakemake.params.outdir
os.makedirs(outdir, exist_ok=True)

score_entries = []

for run_entry in run_manifest["runs"]:
    candidate_id = run_entry["candidate_id"]
    result_file = run_entry["result_file"]
    problem_file = problem_files.get(candidate_id)

    with open(result_file) as f:
        result = json.load(f)

    with open(problem_file) as f:
        problem = json.load(f)

    score = score_result(result, problem)
    score_file = os.path.join(outdir, "{}.score.json".format(candidate_id))

    with open(score_file, "w") as f:
        json.dump(score, f, indent=2)

    score_entries.append({
        "candidate_id": candidate_id,
        "score_file": score_file,
    })

# Write score manifest
manifest = {
    "project_id": snakemake.config["project"]["id"],
    "num_scores": len(score_entries),
    "scores": score_entries,
}
with open(snakemake.output.score_manifest, "w") as f:
    json.dump(manifest, f, indent=2)
