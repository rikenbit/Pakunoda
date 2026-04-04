"""Recommendation engine for Pakunoda search results.

Analyzes trial results across candidates and produces
ranked recommendations with explanations.
"""

from __future__ import annotations

from typing import Dict, List, Optional


def best_by_error(candidate_results):
    # type: (List[Dict]) -> Optional[Dict]
    """Select the candidate with lowest imputation error.

    Args:
        candidate_results: List of dicts, each with 'candidate_id' and 'best_trial'.

    Returns:
        The best candidate result dict, or None.
    """
    valid = [r for r in candidate_results if r.get("best_trial") and r["best_trial"].get("value") is not None]
    if not valid:
        return None
    return min(valid, key=lambda r: r["best_trial"]["value"])


def best_by_balanced_score(candidate_results, error_weight=0.7, complexity_weight=0.3):
    # type: (List[Dict], float, float) -> Optional[Dict]
    """Select the candidate with best balanced score (error + complexity).

    Normalizes error and complexity to [0, 1] across candidates,
    then computes weighted sum.

    Args:
        candidate_results: List of dicts with 'best_trial' containing 'value' and 'total_params'.
        error_weight: Weight for imputation error.
        complexity_weight: Weight for model complexity.

    Returns:
        The best candidate result dict, or None.
    """
    valid = [
        r for r in candidate_results
        if r.get("best_trial")
        and r["best_trial"].get("value") is not None
        and r["best_trial"].get("total_params") is not None
    ]
    if not valid:
        return None
    if len(valid) == 1:
        return valid[0]

    errors = [r["best_trial"]["value"] for r in valid]
    complexities = [r["best_trial"]["total_params"] for r in valid]

    # Normalize to [0, 1]
    e_min, e_max = min(errors), max(errors)
    c_min, c_max = min(complexities), max(complexities)
    e_range = e_max - e_min if e_max > e_min else 1.0
    c_range = c_max - c_min if c_max > c_min else 1.0

    best = None
    best_score = float("inf")
    for r in valid:
        e_norm = (r["best_trial"]["value"] - e_min) / e_range
        c_norm = (r["best_trial"]["total_params"] - c_min) / c_range
        score = error_weight * e_norm + complexity_weight * c_norm
        if score < best_score:
            best_score = score
            best = r

    return best


def top_n_summary(candidate_results, n=5):
    # type: (List[Dict], int) -> List[Dict]
    """Return top-N candidates sorted by imputation error.

    Args:
        candidate_results: List of candidate result dicts.
        n: Number of top results to return.

    Returns:
        Sorted list of top-N candidate summaries.
    """
    valid = [
        r for r in candidate_results
        if r.get("best_trial") and r["best_trial"].get("value") is not None
    ]
    sorted_results = sorted(valid, key=lambda r: r["best_trial"]["value"])
    summaries = []
    for i, r in enumerate(sorted_results[:n]):
        bt = r["best_trial"]
        summaries.append({
            "position": i + 1,
            "candidate_id": r["candidate_id"],
            "imputation_rmse": bt["value"],
            "rank": bt.get("rank"),
            "init_policy": bt.get("init_policy"),
            "total_params": bt.get("total_params"),
            "runtime_seconds": bt.get("runtime_seconds"),
            "num_trials": r.get("num_trials", 0),
        })
    return summaries


def generate_recommendation(candidate_results, config_snapshot=None):
    # type: (List[Dict], Optional[Dict]) -> Dict
    """Generate a full recommendation report.

    Args:
        candidate_results: List of dicts, each with:
            - candidate_id: str
            - best_trial: dict with value, params, attrs
            - num_trials: int
        config_snapshot: Optional config summary for provenance.

    Returns:
        Recommendation dict with best picks, top-N, and explanations.
    """
    best_err = best_by_error(candidate_results)
    best_bal = best_by_balanced_score(candidate_results)
    top = top_n_summary(candidate_results)

    explanation_parts = []
    if best_err:
        bt = best_err["best_trial"]
        explanation_parts.append(
            "Best imputation accuracy: candidate '{}' with RMSE={:.4f} "
            "(rank={}, init={}).".format(
                best_err["candidate_id"],
                bt["value"],
                bt.get("rank"),
                bt.get("init_policy"),
            )
        )
    if best_bal and best_bal != best_err:
        bt = best_bal["best_trial"]
        explanation_parts.append(
            "Best balanced (accuracy+complexity): candidate '{}' with RMSE={:.4f}, "
            "params={}.".format(
                best_bal["candidate_id"],
                bt["value"],
                bt.get("total_params"),
            )
        )

    total_candidates = len(candidate_results)
    total_trials = sum(r.get("num_trials", 0) for r in candidate_results)
    explanation_parts.append(
        "Searched {} candidates with {} total trials.".format(total_candidates, total_trials)
    )

    rec = {
        "best_by_error": {
            "candidate_id": best_err["candidate_id"] if best_err else None,
            "trial": best_err["best_trial"] if best_err else None,
        },
        "best_by_balanced": {
            "candidate_id": best_bal["candidate_id"] if best_bal else None,
            "trial": best_bal["best_trial"] if best_bal else None,
        },
        "top_n": top,
        "explanation": " ".join(explanation_parts),
        "total_candidates_searched": total_candidates,
        "total_trials": total_trials,
    }

    if config_snapshot:
        rec["config_snapshot"] = config_snapshot

    return rec
