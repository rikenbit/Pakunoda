"""Tests for pakunoda.search.objective."""

import numpy as np
import optuna

from pakunoda.search.objective import Objective, mock_solver
from pakunoda.search.search_space import SearchSpace
from pakunoda.search.masking import create_masks_for_tensors


def _make_data():
    return {
        "A": np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]]),
        "B": np.array([[0.5, 1.5], [2.5, 3.5], [4.5, 5.5]]),
    }


def _make_problem():
    return {
        "tensors": [
            {"id": "A", "shape": [3, 3], "data_file": "a.npy"},
            {"id": "B", "shape": [3, 2], "data_file": "b.npy"},
        ],
        "solver": {"family": "CoupledMWCA"},
    }


def test_mock_solver():
    data = {"A": np.array([[1.0, 2.0], [3.0, 4.0]])}
    params = {"rank": 1}
    result = mock_solver(data, params, {})
    assert "A" in result
    assert result["A"].shape == (2, 2)


def test_mock_solver_rank2_exact():
    """Rank-2 SVD of a 2x2 matrix should be exact."""
    data = {"A": np.array([[1.0, 2.0], [3.0, 4.0]])}
    result = mock_solver(data, {"rank": 2}, {})
    np.testing.assert_array_almost_equal(result["A"], data["A"])


def test_objective_runs():
    data = _make_data()
    masks = create_masks_for_tensors(data, fraction=0.2, seed=42)
    space = SearchSpace(rank_range=(1, 3), init_policies=["random", "svd"])
    objective = Objective(space, data, masks, _make_problem(), mock_solver)

    study = optuna.create_study()
    study.optimize(objective, n_trials=3)

    assert len(study.trials) == 3
    assert study.best_value < float("inf")


def test_objective_records_attrs():
    data = _make_data()
    masks = create_masks_for_tensors(data, fraction=0.2, seed=42)
    space = SearchSpace(rank_range=(2, 2), init_policies=["svd"])
    objective = Objective(space, data, masks, _make_problem(), mock_solver)

    study = optuna.create_study()
    study.optimize(objective, n_trials=1)

    trial = study.trials[0]
    assert trial.user_attrs["success"] is True
    assert "runtime_seconds" in trial.user_attrs
    assert "total_params" in trial.user_attrs
    assert trial.user_attrs["rank"] == 2
