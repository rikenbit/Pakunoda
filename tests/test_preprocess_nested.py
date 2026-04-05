"""Tests for pakunoda.preprocess_nested."""

import os
import tempfile

import numpy as np
import pytest

from pakunoda.preprocess_nested import (
    read_mapping,
    build_aggregation_matrix,
    aggregate_block,
    preprocess_nested_relation,
)


# ---- read_mapping ----

def test_read_mapping():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False) as f:
        f.write("gene1\tpathwayA\n")
        f.write("gene2\tpathwayA\n")
        f.write("gene3\tpathwayB\n")
        path = f.name
    try:
        pairs = read_mapping(path)
        assert pairs == [("gene1", "pathwayA"), ("gene2", "pathwayA"), ("gene3", "pathwayB")]
    finally:
        os.unlink(path)


def test_read_mapping_comments():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False) as f:
        f.write("# comment\n")
        f.write("a\tb\n")
        path = f.name
    try:
        pairs = read_mapping(path)
        assert len(pairs) == 1
    finally:
        os.unlink(path)


def test_read_mapping_empty():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False) as f:
        f.write("")
        path = f.name
    try:
        with pytest.raises(ValueError, match="Empty"):
            read_mapping(path)
    finally:
        os.unlink(path)


def test_read_mapping_malformed():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False) as f:
        f.write("only_one_column\n")
        path = f.name
    try:
        with pytest.raises(ValueError, match="2 columns"):
            read_mapping(path)
    finally:
        os.unlink(path)


# ---- build_aggregation_matrix ----

def test_build_agg_matrix():
    mapping = [("g1", "pA"), ("g2", "pA"), ("g3", "pB")]
    source = ["g1", "g2", "g3"]
    target = ["pA", "pB"]
    agg = build_aggregation_matrix(mapping, source, target)
    assert agg.shape == (2, 3)
    # pA = mean(g1, g2) -> [0.5, 0.5, 0]
    # pB = mean(g3)      -> [0, 0, 1]
    np.testing.assert_array_almost_equal(agg[0], [0.5, 0.5, 0.0])
    np.testing.assert_array_almost_equal(agg[1], [0.0, 0.0, 1.0])


def test_build_agg_matrix_missing_source():
    mapping = [("g1", "pA"), ("gX", "pA")]
    with pytest.raises(ValueError, match="Source 'gX'"):
        build_aggregation_matrix(mapping, ["g1", "g2"], ["pA"])


def test_build_agg_matrix_missing_target():
    mapping = [("g1", "pX")]
    with pytest.raises(ValueError, match="Target 'pX'"):
        build_aggregation_matrix(mapping, ["g1"], ["pA"])


# ---- aggregate_block ----

def test_aggregate_rows():
    data = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])  # 3 genes x 2 samples
    agg = np.array([[0.5, 0.5, 0.0], [0.0, 0.0, 1.0]])  # 2 pathways x 3 genes
    result = aggregate_block(data, agg, mode_axis=0)
    assert result.shape == (2, 2)
    np.testing.assert_array_almost_equal(result[0], [2.0, 3.0])  # mean(g1, g2)
    np.testing.assert_array_almost_equal(result[1], [5.0, 6.0])  # g3


def test_aggregate_cols():
    data = np.array([[1.0, 3.0, 5.0], [2.0, 4.0, 6.0]])  # 2 samples x 3 genes
    agg = np.array([[0.5, 0.5, 0.0], [0.0, 0.0, 1.0]])  # 2 pathways x 3 genes
    result = aggregate_block(data, agg, mode_axis=1)
    assert result.shape == (2, 2)
    np.testing.assert_array_almost_equal(result[0], [2.0, 5.0])
    np.testing.assert_array_almost_equal(result[1], [3.0, 6.0])


def test_aggregate_3d_error():
    data = np.ones((2, 3, 4))
    agg = np.ones((2, 3))
    with pytest.raises(ValueError, match="2D"):
        aggregate_block(data, agg, mode_axis=0)


# ---- preprocess_nested_relation ----

def test_preprocess_nested_full():
    """Full nested preprocessing: 4 samples x 6 genes -> 4 samples x 3 pathways."""
    source_data = np.arange(24, dtype=np.float64).reshape(4, 6)
    source_modes = ["samples", "genes"]
    source_mode_names = {"genes": ["g1", "g2", "g3", "g4", "g5", "g6"]}
    target_modes = ["samples", "pathways"]
    target_mode_names = {"pathways": ["pA", "pB", "pC"]}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False) as f:
        f.write("g1\tpA\n")
        f.write("g2\tpA\n")
        f.write("g3\tpB\n")
        f.write("g4\tpB\n")
        f.write("g5\tpC\n")
        f.write("g6\tpC\n")
        mapping_file = f.name

    try:
        result = preprocess_nested_relation(
            source_data, source_modes, source_mode_names,
            target_modes, target_mode_names,
            nested_source_mode="genes",
            nested_target_mode="pathways",
            mapping_file=mapping_file,
        )
        assert result["shape"] == [4, 3]
        assert result["modes"] == ["samples", "pathways"]
        # Column 0 (pA) = mean(col0, col1) = mean(0,1)=0.5, mean(6,7)=6.5, ...
        np.testing.assert_array_almost_equal(result["data"][:, 0], [0.5, 6.5, 12.5, 18.5])
    finally:
        os.unlink(mapping_file)
