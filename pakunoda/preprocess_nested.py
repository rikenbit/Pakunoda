"""Nested relation preprocessing for Pakunoda.

Handles many-to-one mappings (e.g., genes -> gene_families) by aggregating
the source block's data along the mapped mode, producing a new block whose
dimension matches the target. The nested relation is then replaced by an
exact relation between the aggregated block and the target.

Supported: many-to-one aggregation (group-by mean) on a single mode of a
2D matrix. The aggregated mode must be either the row or column mode.

Not yet supported:
- One-to-many (expansion)
- Weighted aggregation
- Tensor (>2D) aggregation
- Multi-mode nested relations
"""

from __future__ import annotations

import csv
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import numpy as np


def read_mapping(filepath):
    # type: (str) -> List[Tuple[str, str]]
    """Read a mapping TSV file.

    Format: two columns, no header. Each row is ``source_id<TAB>target_id``.

    Returns:
        List of (source_id, target_id) tuples.

    Raises:
        ValueError: If file is empty or malformed.
    """
    pairs = []
    with open(filepath, "r") as f:
        reader = csv.reader(f, delimiter="\t")
        for i, row in enumerate(reader):
            if not row or row[0].startswith("#"):
                continue
            if len(row) < 2:
                raise ValueError(
                    "Mapping file line {}: expected 2 columns, got {}".format(i + 1, len(row))
                )
            pairs.append((row[0].strip(), row[1].strip()))

    if not pairs:
        raise ValueError("Empty mapping file: {}".format(filepath))
    return pairs


def build_aggregation_matrix(mapping, source_names, target_names):
    # type: (List[Tuple[str, str]], List[str], List[str]) -> np.ndarray
    """Build an aggregation matrix from a many-to-one mapping.

    The result is a (n_target x n_source) matrix where each row sums to the
    number of source entities mapped to that target. Dividing by the row sum
    gives group-mean aggregation.

    Args:
        mapping: List of (source_id, target_id) pairs.
        source_names: Ordered list of source entity names (e.g., gene names).
        target_names: Ordered list of target entity names (e.g., family names).

    Returns:
        Aggregation matrix of shape (n_target, n_source), float64.

    Raises:
        ValueError: If a source or target name in the mapping is not found.
    """
    source_idx = {name: i for i, name in enumerate(source_names)}
    target_idx = {name: i for i, name in enumerate(target_names)}

    n_src = len(source_names)
    n_tgt = len(target_names)
    agg = np.zeros((n_tgt, n_src), dtype=np.float64)

    for src, tgt in mapping:
        if src not in source_idx:
            raise ValueError("Source '{}' in mapping not found in source block".format(src))
        if tgt not in target_idx:
            raise ValueError("Target '{}' in mapping not found in target block".format(tgt))
        agg[target_idx[tgt], source_idx[src]] = 1.0

    # Normalize rows to get group-mean
    row_sums = agg.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0  # avoid division by zero
    agg = agg / row_sums

    return agg


def aggregate_block(data, agg_matrix, mode_axis):
    # type: (np.ndarray, np.ndarray, int) -> np.ndarray
    """Aggregate a 2D matrix along one mode using an aggregation matrix.

    Args:
        data: Source data matrix, shape (m, n).
        agg_matrix: Aggregation matrix, shape (k, m) if mode_axis=0,
                     or (k, n) if mode_axis=1.
        mode_axis: Which axis to aggregate. 0 = rows, 1 = columns.

    Returns:
        Aggregated matrix.

    Raises:
        ValueError: If data is not 2D or dimensions don't match.
    """
    if data.ndim != 2:
        raise ValueError("aggregate_block only supports 2D matrices, got {}D".format(data.ndim))

    if mode_axis == 0:
        # Aggregate rows: result = agg_matrix @ data, shape (k, n)
        if agg_matrix.shape[1] != data.shape[0]:
            raise ValueError(
                "Aggregation matrix cols ({}) != data rows ({})".format(
                    agg_matrix.shape[1], data.shape[0]
                )
            )
        return agg_matrix @ data
    elif mode_axis == 1:
        # Aggregate columns: result = data @ agg_matrix.T, shape (m, k)
        if agg_matrix.shape[1] != data.shape[1]:
            raise ValueError(
                "Aggregation matrix cols ({}) != data cols ({})".format(
                    agg_matrix.shape[1], data.shape[1]
                )
            )
        return data @ agg_matrix.T
    else:
        raise ValueError("mode_axis must be 0 or 1, got {}".format(mode_axis))


def preprocess_nested_relation(
    source_data,       # np.ndarray, 2D
    source_modes,      # list of mode names, e.g. ["genes", "samples"]
    source_mode_names, # dict: mode_name -> list of entity names (e.g. gene names)
    target_modes,      # list of mode names for target block
    target_mode_names, # dict: mode_name -> list of entity names (e.g. family names)
    nested_source_mode, # mode name in source block being aggregated
    nested_target_mode, # mode name in target block
    mapping_file,      # path to mapping TSV
):
    # type: (...) -> dict
    """Preprocess a single nested relation by aggregating the source block.

    Returns:
        Dict with:
        - 'data': aggregated numpy array
        - 'shape': list of ints
        - 'modes': new mode list (with nested_source_mode replaced by nested_target_mode)
        - 'aggregated_mode': the mode that was aggregated
    """
    mapping = read_mapping(mapping_file)

    # Determine which axis of source_data corresponds to nested_source_mode
    mode_axis = source_modes.index(nested_source_mode)
    source_names = source_mode_names.get(nested_source_mode)
    target_names = target_mode_names.get(nested_target_mode)

    if source_names is None:
        raise ValueError(
            "No entity names for source mode '{}'. "
            "Entity names are required for nested relation aggregation.".format(nested_source_mode)
        )
    if target_names is None:
        raise ValueError(
            "No entity names for target mode '{}'. "
            "Entity names are required for nested relation aggregation.".format(nested_target_mode)
        )

    agg_matrix = build_aggregation_matrix(mapping, source_names, target_names)
    aggregated = aggregate_block(source_data, agg_matrix, mode_axis)

    # Build new mode list: replace nested_source_mode with nested_target_mode
    new_modes = list(source_modes)
    new_modes[mode_axis] = nested_target_mode

    return {
        "data": aggregated,
        "shape": list(aggregated.shape),
        "modes": new_modes,
        "aggregated_mode": nested_source_mode,
    }
