"""Tests for pakunoda.io."""

import os
import tempfile

import numpy as np
import pytest

from pakunoda.io import detect_format, read_tsv, ingest_file


def test_detect_tsv():
    assert detect_format("data.tsv") == "tsv"


def test_detect_csv():
    assert detect_format("data.csv") == "tsv"


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
