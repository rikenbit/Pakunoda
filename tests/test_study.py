"""Tests for pakunoda.search.study."""

import os
import tempfile

import numpy as np
import optuna

from pakunoda.search.study import (
    create_or_load_study,
    run_study,
    list_trials_summary,
    get_best_trial_summary,
)
from pakunoda.search.objective import Objective, mock_solver
from pakunoda.search.search_space import SearchSpace
from pakunoda.search.masking import create_masks_for_tensors


def _make_objective():
    data = {"X": np.random.RandomState(42).rand(4, 3)}
    masks = create_masks_for_tensors(data, 0.2, seed=42)
    space = SearchSpace(rank_range=(1, 3), init_policies=["svd"])
    problem = {"tensors": [{"id": "X", "shape": [4, 3]}]}
    return Objective(space, data, masks, problem, mock_solver)


def test_create_study():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.sqlite3")
        study = create_or_load_study("test_study", path)
        assert study.study_name == "test_study"
        assert os.path.exists(path)


def test_load_existing_study():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.sqlite3")
        s1 = create_or_load_study("test_study", path)
        s1.optimize(lambda trial: trial.suggest_int("x", 1, 10), n_trials=3)
        s2 = create_or_load_study("test_study", path)
        assert len(s2.trials) == 3


def test_run_study():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.sqlite3")
        study = create_or_load_study("test_run", path)
        objective = _make_objective()
        study = run_study(study, objective, n_trials=5, seed=42)
        assert len(study.trials) == 5


def test_list_trials_summary():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.sqlite3")
        study = create_or_load_study("test_list", path)
        objective = _make_objective()
        run_study(study, objective, n_trials=3, seed=42)

        summaries = list_trials_summary(study)
        assert len(summaries) == 3
        assert "trial_number" in summaries[0]
        assert "value" in summaries[0]


def test_get_best_trial_summary():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.sqlite3")
        study = create_or_load_study("test_best", path)
        objective = _make_objective()
        run_study(study, objective, n_trials=5, seed=42)

        best = get_best_trial_summary(study)
        assert best is not None
        assert "value" in best
        assert best["value"] <= float("inf")


def test_get_best_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.sqlite3")
        study = create_or_load_study("test_empty", path)
        best = get_best_trial_summary(study)
        assert best is None
