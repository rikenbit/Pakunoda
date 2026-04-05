"""Tests for pakunoda.io."""

import os
import tempfile

import numpy as np
import pytest

from pakunoda.io import detect_format, read_tsv, read_mat, ingest_file


def test_detect_tsv():
    assert detect_format("data.tsv") == "tsv"


def test_detect_csv():
    assert detect_format("data.csv") == "tsv"


def test_detect_mat():
    assert detect_format("data.mat") == "mat"


def test_detect_unsupported():
    with pytest.raises(ValueError, match="Unsupported"):
        detect_format("data.xyz")


def test_read_tsv():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False) as f:
        f.write("\tcol1\tcol2\n")
        f.write("row1\t1.0\t2.0\n")
        f.write("row2\t3.0\t4.0\n")
        f.name
    try:
        result = read_tsv(f.name)
        assert result["shape"] == [2, 2]
        assert result["row_names"] == ["row1", "row2"]
        assert result["col_names"] == ["col1", "col2"]
        np.testing.assert_array_equal(result["data"], [[1.0, 2.0], [3.0, 4.0]])
    finally:
        os.unlink(f.name)


def test_read_mat():
    import scipy.io
    with tempfile.NamedTemporaryFile(suffix=".mat", delete=False) as f:
        path = f.name
    try:
        data = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
        scipy.io.savemat(path, {"X": data})
        result = read_mat(path)
        assert result["shape"] == [3, 2]
        np.testing.assert_array_equal(result["data"], data)
        assert result["variable_name"] == "X"
    finally:
        os.unlink(path)


def test_read_mat_specific_variable():
    import scipy.io
    with tempfile.NamedTemporaryFile(suffix=".mat", delete=False) as f:
        path = f.name
    try:
        scipy.io.savemat(path, {"A": np.ones((2, 3)), "B": np.zeros((4, 5))})
        result = read_mat(path, variable_name="B")
        assert result["shape"] == [4, 5]
        assert result["variable_name"] == "B"
    finally:
        os.unlink(path)


def test_ingest_mat():
    import scipy.io
    with tempfile.NamedTemporaryFile(suffix=".mat", delete=False) as f:
        path = f.name
    try:
        scipy.io.savemat(path, {"M": np.ones((3, 4))})
        meta = ingest_file(path)
        assert meta["format"] == "mat"
        assert meta["shape"] == [3, 4]
    finally:
        os.unlink(path)


def test_ingest_tsv():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False) as f:
        f.write("\ta\tb\n")
        f.write("x\t1\t2\n")
    try:
        meta = ingest_file(f.name)
        assert meta["format"] == "tsv"
        assert meta["shape"] == [1, 2]
    finally:
        os.unlink(f.name)
