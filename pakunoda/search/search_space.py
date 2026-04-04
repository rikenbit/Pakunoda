"""Search space construction for Pakunoda.

Builds an Optuna-compatible parameter space from a candidate and search config.
The search space is defined in Pakunoda's semantic terms (rank, init_policy, etc.),
not in raw Optuna terms.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple


class SearchSpace:
    """Defines the hyperparameter search space for a candidate.

    Attributes:
        rank_range: (min_rank, max_rank) inclusive.
        init_policies: List of initialization policies to try.
        weight_scaling_range: Optional (min, max) for weight scaling factor.
    """

    def __init__(
        self,
        rank_range,          # type: Tuple[int, int]
        init_policies,       # type: List[str]
        weight_scaling_range=None,  # type: Optional[Tuple[float, float]]
    ):
        self.rank_range = rank_range
        self.init_policies = init_policies
        self.weight_scaling_range = weight_scaling_range

    def suggest(self, trial):
        """Suggest hyperparameters from an Optuna trial.

        Args:
            trial: optuna.Trial object.

        Returns:
            Dict of suggested hyperparameters.
        """
        params = {}
        params["rank"] = trial.suggest_int("rank", self.rank_range[0], self.rank_range[1])
        params["init_policy"] = trial.suggest_categorical("init_policy", self.init_policies)
        if self.weight_scaling_range is not None:
            params["weight_scaling"] = trial.suggest_float(
                "weight_scaling",
                self.weight_scaling_range[0],
                self.weight_scaling_range[1],
            )
        return params

    def to_dict(self):
        # type: () -> Dict
        d = {
            "rank_range": list(self.rank_range),
            "init_policies": self.init_policies,
        }
        if self.weight_scaling_range is not None:
            d["weight_scaling_range"] = list(self.weight_scaling_range)
        return d


def build_search_space(search_config):
    # type: (Dict) -> SearchSpace
    """Build a SearchSpace from the search section of config.yaml.

    Args:
        search_config: The 'search' section of the Pakunoda config.

    Returns:
        SearchSpace instance.
    """
    rank_range = tuple(search_config.get("rank_range", [2, 10]))
    init_policies = search_config.get("init_policies", ["random", "svd"])
    weight_scaling_range = None
    ws = search_config.get("weight_scaling_range")
    if ws is not None:
        weight_scaling_range = tuple(ws)

    return SearchSpace(
        rank_range=rank_range,
        init_policies=init_policies,
        weight_scaling_range=weight_scaling_range,
    )
