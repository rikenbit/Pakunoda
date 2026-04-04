"""Snakemake script: run all compiled candidates through the solver.

Reads compiled_manifest.json, runs each candidate, writes result JSONs
and a run_manifest.json.

Solver selection:
- If search.mock is true, uses Python SVD-based mock solver.
- Otherwise, tries R/mwTensor via run_candidate.R.
- Falls back to mock if R or mwTensor is unavailable.
"""

import json
import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Load compiled manifest
with open(snakemake.input.manifest) as f:
    compiled_manifest = json.load(f)

outdir = snakemake.params.outdir
os.makedirs(outdir, exist_ok=True)

use_mock = snakemake.config.get("search", {}).get("mock", False)
r_script = os.path.join(os.path.dirname(__file__), "run_candidate.R")

run_entries = []

for entry in compiled_manifest["problems"]:
    candidate_id = entry["candidate_id"]
    problem_file = entry["problem_file"]
    candidate_outdir = os.path.join(outdir, candidate_id)
    result_file = os.path.join(candidate_outdir, "result.json")

    os.makedirs(candidate_outdir, exist_ok=True)

    with open(problem_file) as f:
        problem = json.load(f)

    # Check for unsupported nested relations
    nested = problem.get("nested_relations", [])
    if nested:
        result = {
            "candidate_id": candidate_id,
            "success": False,
            "error_message": "Nested relations are not yet supported by the solver. "
                             "Set allow_nested: false or remove nested relations.",
            "reconstruction_error": None,
            "runtime_seconds": 0.0,
            "rank": problem.get("rank"),
            "num_tensors": len(problem.get("tensors", [])),
            "solver_family": problem.get("solver", {}).get("family"),
        }
        with open(result_file, "w") as f:
            json.dump(result, f, indent=2)
        run_entries.append({"candidate_id": candidate_id, "result_file": result_file})
        continue

    ran_with_mock = use_mock

    if not use_mock:
        # Try R/mwTensor
        try:
            proc = subprocess.run(
                ["Rscript", r_script, problem_file, candidate_outdir],
                capture_output=True, text=True, timeout=600,
            )
            if proc.returncode == 0 and os.path.exists(result_file):
                run_entries.append({"candidate_id": candidate_id, "result_file": result_file})
                continue
            else:
                stderr = proc.stderr
                if "mwTensor" in stderr or "there is no package" in stderr:
                    ran_with_mock = True
                else:
                    result = {
                        "candidate_id": candidate_id,
                        "success": False,
                        "error_message": stderr[:500] if stderr else "R script failed",
                        "reconstruction_error": None,
                        "runtime_seconds": 0.0,
                        "rank": problem.get("rank"),
                        "num_tensors": len(problem.get("tensors", [])),
                        "solver_family": problem.get("solver", {}).get("family"),
                    }
                    with open(result_file, "w") as f:
                        json.dump(result, f, indent=2)
                    run_entries.append({"candidate_id": candidate_id, "result_file": result_file})
                    continue
        except FileNotFoundError:
            ran_with_mock = True
        except subprocess.TimeoutExpired:
            result = {
                "candidate_id": candidate_id,
                "success": False,
                "error_message": "Timeout after 600s",
                "reconstruction_error": None,
                "runtime_seconds": 600.0,
                "rank": problem.get("rank"),
                "num_tensors": len(problem.get("tensors", [])),
                "solver_family": problem.get("solver", {}).get("family"),
            }
            with open(result_file, "w") as f:
                json.dump(result, f, indent=2)
            run_entries.append({"candidate_id": candidate_id, "result_file": result_file})
            continue

    if ran_with_mock:
        # Mock mode: SVD-based reconstruction error using rank from problem JSON
        start_time = time.time()
        rank = problem.get("rank", 3)

        total_error_sq = 0.0
        for tensor_info in problem.get("tensors", []):
            data_file = tensor_info["data_file"]
            if os.path.exists(data_file):
                data = np.load(data_file)
                if data.ndim == 2:
                    U, s, Vt = np.linalg.svd(data, full_matrices=False)
                    k = min(rank, len(s))
                    approx = U[:, :k] @ np.diag(s[:k]) @ Vt[:k, :]
                    total_error_sq += float(np.linalg.norm(data - approx, "fro") ** 2)

        reconstruction_error = float(np.sqrt(total_error_sq))
        elapsed = time.time() - start_time

        result = {
            "candidate_id": candidate_id,
            "success": True,
            "error_message": None,
            "reconstruction_error": round(reconstruction_error, 6),
            "runtime_seconds": round(elapsed, 4),
            "rank": rank,
            "num_tensors": len(problem.get("tensors", [])),
            "solver_family": problem.get("solver", {}).get("family"),
            "mock": True,
        }
        with open(result_file, "w") as f:
            json.dump(result, f, indent=2)

    run_entries.append({"candidate_id": candidate_id, "result_file": result_file})

# Write run manifest
manifest = {
    "project_id": snakemake.config["project"]["id"],
    "num_runs": len(run_entries),
    "runs": run_entries,
}
with open(snakemake.output.run_manifest, "w") as f:
    json.dump(manifest, f, indent=2)
