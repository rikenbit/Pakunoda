"""Tests for .tns reader."""

import os
import tempfile

import numpy as np
import pytest

from pakunoda.io import read_tns, detect_format, ingest_file


def test_detect_tns():
    assert detect_format("data.tns") == "tns"


def test_read_tns_matrix():
    """2D coordinate list (matrix)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".tns", delete=False) as f:
        # 1-based indices: 3x2 matrix
        f.write("1 1 1.0\n")
        f.write("1 2 2.0\n")
        f.write("2 1 3.0\n")
        f.write("3 2 4.0\n")
        path = f.name
    try:
        result = read_tns(path)
        assert result["shape"] == [3, 2]
        assert result["nnz"] == 4
        expected = np.array([[1.0, 2.0], [3.0, 0.0], [0.0, 4.0]])
        np.testing.assert_array_equal(result["data"], expected)
    finally:
        os.unlink(path)


def test_read_tns_3d():
    """3D tensor in coordinate format."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".tns", delete=False) as f:
        f.write("1 1 1 5.0\n")
        f.write("2 1 2 3.0\n")
        f.write("1 2 1 7.0\n")
        path = f.name
    try:
        result = read_tns(path)
        assert result["shape"] == [2, 2, 2]
        assert result["nnz"] == 3
        assert result["data"][0, 0, 0] == 5.0
        assert result["data"][1, 0, 1] == 3.0
        assert result["data"][0, 1, 0] == 7.0
    finally:
        os.unlink(path)


def test_read_tns_comments():
    """Lines starting with # are skipped."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".tns", delete=False) as f:
        f.write("# This is a comment\n")
        f.write("1 1 1.0\n")
        f.write("# another comment\n")
        f.write("2 2 2.0\n")
        path = f.name
    try:
        result = read_tns(path)
        assert result["nnz"] == 2
    finally:
        os.unlink(path)


def test_read_tns_explicit_shape():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".tns", delete=False) as f:
        f.write("1 1 1.0\n")
        path = f.name
    try:
        result = read_tns(path, shape=[5, 5])
        assert result["shape"] == [5, 5]
        assert result["data"].shape == (5, 5)
    finally:
        os.unlink(path)


def test_read_tns_empty():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".tns", delete=False) as f:
        f.write("# only comments\n")
        path = f.name
    try:
        with pytest.raises(ValueError, match="Empty"):
            read_tns(path)
    finally:
        os.unlink(path)


def test_read_tns_inconsistent_order():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".tns", delete=False) as f:
        f.write("1 1 1.0\n")
        f.write("1 1 1 2.0\n")  # 3 indices vs 2
        path = f.name
    try:
        with pytest.raises(ValueError, match="Inconsistent"):
            read_tns(path)
    finally:
        os.unlink(path)


def test_ingest_tns():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".tns", delete=False) as f:
        f.write("1 1 1.0\n")
        f.write("2 3 2.0\n")
        path = f.name
    try:
        meta = ingest_file(path)
        assert meta["format"] == "tns"
        assert meta["shape"] == [2, 3]
    finally:
        os.unlink(path)
