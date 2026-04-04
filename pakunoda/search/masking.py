"""Masking utilities for imputation-based evaluation.

Creates artificial masks on data matrices/tensors, splits into
observed and held-out sets, and computes imputation error on held-out elements.

MVP: elementwise random masking only.
Future: block-wise, relation-aware masking.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np


def create_elementwise_mask(shape, fraction, rng):
    # type: (Tuple[int, ...], float, np.random.RandomState) -> np.ndarray
    """Create a boolean mask where True = held out (masked).

    Args:
        shape: Shape of the data array.
        fraction: Fraction of elements to mask (0.0 to 1.0).
        rng: NumPy RandomState for reproducibility.

    Returns:
        Boolean array of same shape. True = masked (held out).
    """
    mask = rng.random_sample(shape) < fraction
    # Ensure at least one element is masked and one is observed
    if mask.all():
        idx = tuple(rng.randint(0, s) for s in shape)
        mask[idx] = False
    if not mask.any():
        idx = tuple(rng.randint(0, s) for s in shape)
        mask[idx] = True
    return mask


def apply_mask(data, mask, fill_value=0.0):
    # type: (np.ndarray, np.ndarray, float) -> np.ndarray
    """Replace masked elements with fill_value.

    Args:
        data: Original data array.
        mask: Boolean mask (True = masked).
        fill_value: Value to fill masked positions.

    Returns:
        Copy of data with masked elements replaced.
    """
    masked_data = data.copy()
    masked_data[mask] = fill_value
    return masked_data


def imputation_error(original, reconstructed, mask):
    # type: (np.ndarray, np.ndarray, np.ndarray) -> float
    """Compute RMSE on held-out (masked) elements.

    Args:
        original: Original data array.
        reconstructed: Reconstructed data array.
        mask: Boolean mask (True = held out).

    Returns:
        RMSE on masked elements. Returns float('inf') if no masked elements.
    """
    n_masked = mask.sum()
    if n_masked == 0:
        return float("inf")
    diff = original[mask] - reconstructed[mask]
    return float(np.sqrt(np.mean(diff ** 2)))


def create_masks_for_tensors(tensors_data, fraction, seed):
    # type: (Dict[str, np.ndarray], float, int) -> Dict[str, np.ndarray]
    """Create masks for a collection of tensors.

    Args:
        tensors_data: Dict mapping tensor_id -> data array.
        fraction: Fraction of elements to mask.
        seed: Random seed.

    Returns:
        Dict mapping tensor_id -> boolean mask.
    """
    rng = np.random.RandomState(seed)
    masks = {}
    for tid, data in tensors_data.items():
        masks[tid] = create_elementwise_mask(data.shape, fraction, rng)
    return masks
