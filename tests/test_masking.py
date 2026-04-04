"""Tests for pakunoda.search.masking."""

import numpy as np
import pytest

from pakunoda.search.masking import (
    create_elementwise_mask,
    apply_mask,
    imputation_error,
    create_masks_for_tensors,
)


def test_mask_shape():
    rng = np.random.RandomState(42)
    mask = create_elementwise_mask((5, 4), 0.2, rng)
    assert mask.shape == (5, 4)
    assert mask.dtype == bool


def test_mask_fraction():
    rng = np.random.RandomState(42)
    mask = create_elementwise_mask((100, 100), 0.3, rng)
    actual = mask.sum() / mask.size
    assert 0.2 < actual < 0.4  # rough check


def test_mask_never_all_true():
    rng = np.random.RandomState(42)
    mask = create_elementwise_mask((2, 2), 0.99, rng)
    assert not mask.all()


def test_mask_never_all_false():
    rng = np.random.RandomState(42)
    mask = create_elementwise_mask((2, 2), 0.01, rng)
    assert mask.any()


def test_apply_mask():
    data = np.array([[1.0, 2.0], [3.0, 4.0]])
    mask = np.array([[True, False], [False, True]])
    result = apply_mask(data, mask, fill_value=0.0)
    np.testing.assert_array_equal(result, [[0.0, 2.0], [3.0, 0.0]])
    # Original unchanged
    assert data[0, 0] == 1.0


def test_imputation_error_exact():
    orig = np.array([[1.0, 2.0], [3.0, 4.0]])
    recon = np.array([[1.0, 2.0], [3.0, 4.0]])
    mask = np.array([[True, False], [False, True]])
    assert imputation_error(orig, recon, mask) == 0.0


def test_imputation_error_known():
    orig = np.array([[1.0, 2.0], [3.0, 4.0]])
    recon = np.array([[2.0, 2.0], [3.0, 6.0]])
    mask = np.array([[True, False], [False, True]])
    # errors: |1-2|=1, |4-6|=2 → RMSE = sqrt((1+4)/2) = sqrt(2.5)
    expected = np.sqrt(2.5)
    assert abs(imputation_error(orig, recon, mask) - expected) < 1e-10


def test_imputation_error_no_mask():
    orig = np.ones((3, 3))
    recon = np.zeros((3, 3))
    mask = np.zeros((3, 3), dtype=bool)
    assert imputation_error(orig, recon, mask) == float("inf")


def test_create_masks_for_tensors():
    data = {
        "A": np.ones((5, 4)),
        "B": np.ones((5, 3)),
    }
    masks = create_masks_for_tensors(data, fraction=0.2, seed=42)
    assert "A" in masks
    assert "B" in masks
    assert masks["A"].shape == (5, 4)
    assert masks["B"].shape == (5, 3)
