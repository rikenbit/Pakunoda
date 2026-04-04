"""Tests for pakunoda.search.recommend."""

from pakunoda.search.recommend import (
    best_by_error,
    best_by_balanced_score,
    top_n_summary,
    generate_recommendation,
)


def _results():
    return [
        {
            "candidate_id": "c0",
            "best_trial": {"value": 0.5, "rank": 3, "init_policy": "svd", "total_params": 50, "runtime_seconds": 0.1},
            "num_trials": 10,
        },
        {
            "candidate_id": "c1",
            "best_trial": {"value": 0.3, "rank": 2, "init_policy": "random", "total_params": 30, "runtime_seconds": 0.05},
            "num_trials": 10,
        },
        {
            "candidate_id": "c2",
            "best_trial": {"value": 0.4, "rank": 5, "init_policy": "svd", "total_params": 80, "runtime_seconds": 0.2},
            "num_trials": 10,
        },
    ]


def test_best_by_error():
    result = best_by_error(_results())
    assert result["candidate_id"] == "c1"  # lowest error 0.3


def test_best_by_error_empty():
    assert best_by_error([]) is None


def test_best_by_balanced():
    result = best_by_balanced_score(_results())
    # c1 has lowest error AND lowest complexity, so should win balanced too
    assert result["candidate_id"] == "c1"


def test_top_n():
    top = top_n_summary(_results(), n=2)
    assert len(top) == 2
    assert top[0]["candidate_id"] == "c1"
    assert top[1]["candidate_id"] == "c2"


def test_generate_recommendation():
    rec = generate_recommendation(_results())
    assert rec["best_by_error"]["candidate_id"] == "c1"
    assert rec["total_candidates_searched"] == 3
    assert rec["total_trials"] == 30
    assert len(rec["top_n"]) == 3
    assert "explanation" in rec
    assert len(rec["explanation"]) > 0
