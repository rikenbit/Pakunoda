"""Objective function for Pakunoda search.

Defines how a single trial is evaluated:
1. Suggest hyperparameters (rank, init_policy, etc.)
2. Apply mask to data
3. Run factorization on masked data
4. Compute imputation error on held-out elements
5. Return objective value

The objective is structured so that:
- It is self-contained (one function call per trial)
- It records auxiliary metrics (runtime, complexity) as trial user_attrs
- It is extensible to multi-objective (return tuple) in the future
"""

from __future__ import annotations

import time
from typing import Callable, Dict, List, Optional

import numpy as np

from pakunoda.search.masking import apply_mask, create_masks_for_tensors, imputation_error
from pakunoda.search.search_space import SearchSpace


class Objective:
    """Callable objective for Optuna.

    Wraps a solver function and evaluates imputation quality.

    Args:
        search_space: The SearchSpace to draw parameters from.
        tensors_data: Dict mapping tensor_id -> np.ndarray (original data).
        masks: Dict mapping tensor_id -> boolean mask.
        problem: The compiled problem dict for this candidate.
        solver_fn: Function(masked_tensors_data, params, problem) -> reconstructed_data.
                   Returns Dict[tensor_id -> np.ndarray].
    """

    def __init__(
        self,
        search_space,    # type: SearchSpace
        tensors_data,    # type: Dict[str, np.ndarray]
        masks,           # type: Dict[str, np.ndarray]
        problem,         # type: Dict
        solver_fn,       # type: Callable
    ):
        self.search_space = search_space
        self.tensors_data = tensors_data
        self.masks = masks
        self.problem = problem
        self.solver_fn = solver_fn

    def __call__(self, trial):
        """Evaluate a single trial.

        Returns:
            float: Imputation RMSE (lower is better).
        """
        # Suggest parameters
        params = self.search_space.suggest(trial)

        # Prepare masked data
        masked_data = {}
        for tid, data in self.tensors_data.items():
            mask = self.masks.get(tid)
            if mask is not None:
                masked_data[tid] = apply_mask(data, mask)
            else:
                masked_data[tid] = data.copy()

        # Run solver
        start_time = time.time()
        try:
            reconstructed = self.solver_fn(masked_data, params, self.problem)
        except Exception as e:
            trial.set_user_attr("error", str(e))
            trial.set_user_attr("success", False)
            return float("inf")
        elapsed = time.time() - start_time

        # Compute imputation error (RMSE on masked elements)
        total_sq_error = 0.0
        total_masked = 0
        for tid, data in self.tensors_data.items():
            mask = self.masks.get(tid)
            if mask is not None and mask.any():
                recon = reconstructed.get(tid)
                if recon is not None:
                    diff = data[mask] - recon[mask]
                    total_sq_error += float(np.sum(diff ** 2))
                    total_masked += int(mask.sum())

        if total_masked == 0:
            rmse = float("inf")
        else:
            rmse = float(np.sqrt(total_sq_error / total_masked))

        # Compute model complexity
        rank = params["rank"]
        total_params = 0
        for t in self.problem.get("tensors", []):
            for dim in t.get("shape", []):
                total_params += dim * rank

        # Record auxiliary metrics
        trial.set_user_attr("success", True)
        trial.set_user_attr("runtime_seconds", round(elapsed, 4))
        trial.set_user_attr("total_params", total_params)
        trial.set_user_attr("rank", rank)
        trial.set_user_attr("init_policy", params["init_policy"])
        if "weight_scaling" in params:
            trial.set_user_attr("weight_scaling", params["weight_scaling"])

        return rmse


def mock_solver(masked_data, params, problem):
    # type: (Dict[str, np.ndarray], Dict, Dict) -> Dict[str, np.ndarray]
    """SVD-based mock solver for development and testing.

    For each 2D matrix, computes a rank-k SVD approximation.

    Args:
        masked_data: Dict mapping tensor_id -> masked data array.
        params: Hyperparameters dict with at least 'rank'.
        problem: Problem definition (unused in mock).

    Returns:
        Dict mapping tensor_id -> reconstructed array.
    """
    rank = params["rank"]
    reconstructed = {}
    for tid, data in masked_data.items():
        if data.ndim == 2:
            U, s, Vt = np.linalg.svd(data, full_matrices=False)
            k = min(rank, len(s))
            reconstructed[tid] = U[:, :k] @ np.diag(s[:k]) @ Vt[:k, :]
        else:
            # For higher-order tensors, just return the masked data as-is (stub)
            reconstructed[tid] = data.copy()
    return reconstructed
