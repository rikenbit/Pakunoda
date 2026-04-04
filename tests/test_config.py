"""Tests for pakunoda.config."""

import os
import pytest

from pakunoda.config import load_config


def _minimal_config():
    return {
        "project": {"id": "test"},
        "blocks": [
            {"id": "A", "file": "a.tsv", "kind": "matrix", "modes": ["rows", "cols"]},
        ],
        "relations": [],
        "solver": {"family": "CoupledMWCA"},
    }


def test_minimal_valid():
    cfg = _minimal_config()
    result = load_config(cfg)
    assert result["project"]["id"] == "test"


def test_missing_project_id():
    cfg = _minimal_config()
    cfg["project"] = {}
    with pytest.raises(ValueError, match="project.id is required"):
        load_config(cfg)


def test_no_blocks():
    cfg = _minimal_config()
    cfg["blocks"] = []
    with pytest.raises(ValueError, match="At least one block"):
        load_config(cfg)


def test_duplicate_block_id():
    cfg = _minimal_config()
    cfg["blocks"].append(
        {"id": "A", "file": "b.tsv", "kind": "matrix", "modes": ["x", "y"]}
    )
    with pytest.raises(ValueError, match="Duplicate block id"):
        load_config(cfg)


def test_matrix_must_have_2_modes():
    cfg = _minimal_config()
    cfg["blocks"][0]["modes"] = ["a", "b", "c"]
    with pytest.raises(ValueError, match="matrix must have exactly 2 modes"):
        load_config(cfg)


def test_invalid_kind():
    cfg = _minimal_config()
    cfg["blocks"][0]["kind"] = "vector"
    with pytest.raises(ValueError, match="kind must be one of"):
        load_config(cfg)


def test_invalid_relation_type():
    cfg = _minimal_config()
    cfg["blocks"].append(
        {"id": "B", "file": "b.tsv", "kind": "matrix", "modes": ["rows", "cols2"]}
    )
    cfg["relations"] = [
        {
            "type": "partial",
            "between": [
                {"block": "A", "mode": "rows"},
                {"block": "B", "mode": "rows"},
            ],
        }
    ]
    with pytest.raises(ValueError, match="type must be one of"):
        load_config(cfg)


def test_relation_references_nonexistent_block():
    cfg = _minimal_config()
    cfg["relations"] = [
        {
            "type": "exact",
            "between": [
                {"block": "A", "mode": "rows"},
                {"block": "Z", "mode": "rows"},
            ],
        }
    ]
    with pytest.raises(ValueError, match="not found"):
        load_config(cfg)


def test_relation_references_nonexistent_mode():
    cfg = _minimal_config()
    cfg["blocks"].append(
        {"id": "B", "file": "b.tsv", "kind": "matrix", "modes": ["rows", "cols2"]}
    )
    cfg["relations"] = [
        {
            "type": "exact",
            "between": [
                {"block": "A", "mode": "rows"},
                {"block": "B", "mode": "nonexistent"},
            ],
        }
    ]
    with pytest.raises(ValueError, match="not in block"):
        load_config(cfg)


def test_nested_requires_mapping():
    cfg = _minimal_config()
    cfg["blocks"].append(
        {"id": "B", "file": "b.tsv", "kind": "matrix", "modes": ["rows", "cols2"]}
    )
    cfg["relations"] = [
        {
            "type": "nested",
            "between": [
                {"block": "A", "mode": "rows"},
                {"block": "B", "mode": "rows"},
            ],
        }
    ]
    with pytest.raises(ValueError, match="nested relation requires 'mapping'"):
        load_config(cfg)


def test_invalid_solver_family():
    cfg = _minimal_config()
    cfg["solver"]["family"] = "Unknown"
    with pytest.raises(ValueError, match="solver.family must be one of"):
        load_config(cfg)
