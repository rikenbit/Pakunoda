"""Tests for pakunoda.scorer."""

from pakunoda.scorer import score_result, summarize_scores, scores_to_tsv_rows


def _result_ok():
    return {
        "candidate_id": "c0_A_B",
        "success": True,
        "error_message": None,
        "reconstruction_error": 1.5,
        "runtime_seconds": 0.12,
        "rank": 3,
        "num_tensors": 2,
        "solver_family": "CoupledMWCA",
    }


def _result_fail():
    return {
        "candidate_id": "c1_A_C",
        "success": False,
        "error_message": "Solver diverged",
        "reconstruction_error": None,
        "runtime_seconds": 0.05,
        "rank": 3,
        "num_tensors": 2,
        "solver_family": "CoupledMWCA",
    }


def _problem():
    return {
        "tensors": [
            {"id": "A", "shape": [5, 4]},
            {"id": "B", "shape": [5, 3]},
        ],
        "solver": {"family": "CoupledMWCA"},
    }


def test_score_result_success():
    score = score_result(_result_ok(), _problem())
    assert score["candidate_id"] == "c0_A_B"
    assert score["success"] is True
    assert score["reconstruction_error"] == 1.5
    assert score["total_params"] == (5 + 4 + 5 + 3) * 3  # sum(dims) * rank


def test_score_result_failure():
    score = score_result(_result_fail(), _problem())
    assert score["success"] is False
    assert score["reconstruction_error"] is None
    assert score["error_message"] == "Solver diverged"


def test_summarize_scores():
    scores = [
        score_result(_result_ok(), _problem()),
        score_result(_result_fail(), _problem()),
    ]
    summary = summarize_scores(scores)
    assert summary["total_candidates"] == 2
    assert summary["succeeded"] == 1
    assert summary["failed"] == 1
    assert len(summary["ranking"]) == 1
    assert summary["ranking"][0]["candidate_id"] == "c0_A_B"


def test_summarize_scores_ranking_order():
    r1 = _result_ok()
    r2 = _result_ok()
    r2["candidate_id"] = "c1_A_C"
    r2["reconstruction_error"] = 0.5  # better

    scores = [
        score_result(r1, _problem()),
        score_result(r2, _problem()),
    ]
    summary = summarize_scores(scores)
    assert summary["ranking"][0]["candidate_id"] == "c1_A_C"  # lower error first
    assert summary["ranking"][1]["candidate_id"] == "c0_A_B"


def test_scores_to_tsv():
    scores = [score_result(_result_ok(), _problem())]
    rows = scores_to_tsv_rows(scores)
    assert len(rows) == 2  # header + 1 data row
    assert "candidate_id" in rows[0]
    assert "c0_A_B" in rows[1]
