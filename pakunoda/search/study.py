"""Optuna study management for Pakunoda.

Wraps Optuna study creation, execution, and result extraction
behind Pakunoda's semantic interface.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

import optuna

from pakunoda.search.objective import Objective
from pakunoda.search.search_space import SearchSpace


# Suppress Optuna's verbose logging by default
optuna.logging.set_verbosity(optuna.logging.WARNING)


def create_or_load_study(study_name, storage_path):
    # type: (str, str) -> optuna.Study
    """Create a new study or load an existing one.

    Args:
        study_name: Name for the Optuna study.
        storage_path: Path to SQLite file.

    Returns:
        optuna.Study instance.
    """
    os.makedirs(os.path.dirname(storage_path) or ".", exist_ok=True)
    storage = "sqlite:///{}".format(os.path.abspath(storage_path))
    study = optuna.create_study(
        study_name=study_name,
        storage=storage,
        direction="minimize",
        load_if_exists=True,
    )
    return study


def run_study(study, objective, n_trials, seed=None):
    # type: (optuna.Study, Objective, int, Optional[int]) -> optuna.Study
    """Run optimization trials.

    Args:
        study: Optuna study.
        objective: Pakunoda Objective instance.
        n_trials: Number of trials to run.
        seed: Optional seed for the sampler.

    Returns:
        The study after optimization.
    """
    if seed is not None:
        sampler = optuna.samplers.TPESampler(seed=seed)
        study.sampler = sampler

    study.optimize(objective, n_trials=n_trials)
    return study


def resume_study(study_name, storage_path, objective, n_trials, seed=None):
    # type: (str, str, Objective, int, Optional[int]) -> optuna.Study
    """Resume an existing study with additional trials.

    Args:
        study_name: Name of the study.
        storage_path: Path to SQLite file.
        objective: Pakunoda Objective instance.
        n_trials: Number of additional trials.
        seed: Optional seed.

    Returns:
        The study after additional optimization.
    """
    study = create_or_load_study(study_name, storage_path)
    return run_study(study, objective, n_trials, seed)


def list_trials_summary(study):
    # type: (optuna.Study) -> List[Dict]
    """Extract a summary of all trials.

    Returns:
        List of dicts, one per trial, with params and metrics.
    """
    summaries = []
    for trial in study.trials:
        if trial.state != optuna.trial.TrialState.COMPLETE:
            entry = {
                "trial_number": trial.number,
                "state": trial.state.name,
                "value": None,
            }
            entry.update(trial.params)
            entry.update(trial.user_attrs)
            summaries.append(entry)
            continue

        entry = {
            "trial_number": trial.number,
            "state": trial.state.name,
            "value": trial.value,
        }
        entry.update(trial.params)
        entry.update(trial.user_attrs)
        summaries.append(entry)
    return summaries


def get_best_trial_summary(study):
    # type: (optuna.Study) -> Optional[Dict]
    """Get the best trial as a summary dict.

    Returns:
        Dict with params and metrics, or None if no complete trials.
    """
    try:
        best = study.best_trial
    except ValueError:
        return None
    entry = {
        "trial_number": best.number,
        "value": best.value,
    }
    entry.update(best.params)
    entry.update(best.user_attrs)
    return entry
