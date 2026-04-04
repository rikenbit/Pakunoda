"""Tests for pakunoda.search.search_space."""

from pakunoda.search.search_space import SearchSpace, build_search_space


def test_build_from_config():
    config = {
        "rank_range": [2, 5],
        "init_policies": ["random", "svd", "nonneg_random"],
    }
    space = build_search_space(config)
    assert space.rank_range == (2, 5)
    assert space.init_policies == ["random", "svd", "nonneg_random"]
    assert space.weight_scaling_range is None


def test_build_defaults():
    space = build_search_space({})
    assert space.rank_range == (2, 10)
    assert space.init_policies == ["random", "svd"]


def test_build_with_weight_scaling():
    config = {
        "rank_range": [2, 3],
        "init_policies": ["random"],
        "weight_scaling_range": [0.5, 2.0],
    }
    space = build_search_space(config)
    assert space.weight_scaling_range == (0.5, 2.0)


def test_to_dict():
    space = SearchSpace(
        rank_range=(2, 5),
        init_policies=["random", "svd"],
    )
    d = space.to_dict()
    assert d["rank_range"] == [2, 5]
    assert d["init_policies"] == ["random", "svd"]


def test_suggest():
    """Test that suggest returns valid parameters via a mock trial."""
    import optuna
    study = optuna.create_study()
    space = SearchSpace(rank_range=(2, 5), init_policies=["random", "svd"])

    # Run one trial to test suggest
    def obj(trial):
        params = space.suggest(trial)
        assert 2 <= params["rank"] <= 5
        assert params["init_policy"] in ["random", "svd"]
        return 0.0

    study.optimize(obj, n_trials=1)
