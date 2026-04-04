"""Candidate scoring for Pakunoda.

Computes quality metrics from run results.
MVP metrics: reconstruction_error, runtime, success/failure, total_rank.
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional


def score_result(result, problem):
    # type: (dict, dict) -> dict
    """Score a single candidate run result.

    Args:
        result: The result.json from run_candidate.
        problem: The problem.json for this candidate.

    Returns:
        Score dict with standardized metrics.
    """
    candidate_id = result.get("candidate_id", "unknown")
    success = result.get("success", False)

    rec_error = result.get("reconstruction_error")
    runtime = result.get("runtime_seconds", 0.0)
    rank = result.get("rank")
    num_tensors = result.get("num_tensors", 0)

    # Model complexity: total parameters ~ sum(dim_i * rank) for each mode
    total_params = 0
    if rank and problem.get("tensors"):
        for tensor in problem["tensors"]:
            shape = tensor.get("shape", [])
            for dim in shape:
                total_params += dim * rank

    score = {
        "candidate_id": candidate_id,
        "success": success,
        "error_message": result.get("error_message"),
        "reconstruction_error": rec_error,
        "runtime_seconds": runtime,
        "rank": rank,
        "num_tensors": num_tensors,
        "num_blocks": len(problem.get("tensors", [])),
        "total_params": total_params,
        "solver_family": result.get("solver_family"),
        "mock": result.get("mock", False),
    }

    return score


def summarize_scores(scores):
    # type: (List[dict]) -> dict
    """Summarize scores across all candidates.

    Args:
        scores: List of score dicts from score_result.

    Returns:
        Summary dict with aggregated statistics.
    """
    total = len(scores)
    succeeded = [s for s in scores if s["success"]]
    failed = [s for s in scores if not s["success"]]

    # Sort successful candidates by reconstruction error
    ranked = sorted(
        succeeded,
        key=lambda s: s["reconstruction_error"] if s["reconstruction_error"] is not None else float("inf"),
    )

    return {
        "total_candidates": total,
        "succeeded": len(succeeded),
        "failed": len(failed),
        "ranking": [
            {
                "rank_position": i + 1,
                "candidate_id": s["candidate_id"],
                "reconstruction_error": s["reconstruction_error"],
                "runtime_seconds": s["runtime_seconds"],
                "total_params": s["total_params"],
                "num_blocks": s["num_blocks"],
            }
            for i, s in enumerate(ranked)
        ],
        "failed_candidates": [
            {
                "candidate_id": s["candidate_id"],
                "error_message": s["error_message"],
            }
            for s in failed
        ],
    }


def scores_to_tsv_rows(scores):
    # type: (List[dict]) -> List[str]
    """Convert scores to TSV rows for a summary table.

    Returns:
        List of strings, first element is header.
    """
    header = "\t".join([
        "candidate_id",
        "success",
        "reconstruction_error",
        "runtime_seconds",
        "rank",
        "num_blocks",
        "total_params",
        "solver_family",
        "mock",
    ])
    rows = [header]
    for s in scores:
        rows.append("\t".join([
            str(s.get("candidate_id", "")),
            str(s.get("success", "")),
            str(s.get("reconstruction_error", "")),
            str(s.get("runtime_seconds", "")),
            str(s.get("rank", "")),
            str(s.get("num_blocks", "")),
            str(s.get("total_params", "")),
            str(s.get("solver_family", "")),
            str(s.get("mock", "")),
        ]))
    return rows
