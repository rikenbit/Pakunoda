"""File format readers for Pakunoda.

Supported: .tsv, .csv, .mat (MATLAB v5/v7), .tns (FROSTT coordinate format)
"""

import csv
from pathlib import Path

import numpy as np


def detect_format(filepath):
    # type: (str) -> str
    """Detect file format from extension.

    Returns:
        One of: 'tsv', 'mat', 'tns'

    Raises:
        ValueError: If format is unsupported.
    """
    ext = Path(filepath).suffix.lower()
    format_map = {
        ".tsv": "tsv",
        ".csv": "tsv",
        ".mat": "mat",
        ".tns": "tns",
    }
    fmt = format_map.get(ext)
    if fmt is None:
        raise ValueError("Unsupported file format: {}".format(ext))
    return fmt


def read_tsv(filepath, has_header=True, has_rownames=True):
    # type: (str, bool, bool) -> dict
    """Read a TSV/CSV file into a numpy array with metadata.

    Returns:
        Dict with keys: 'data' (np.ndarray), 'row_names', 'col_names', 'shape'.
    """
    ext = Path(filepath).suffix.lower()
    delimiter = "," if ext == ".csv" else "\t"

    with open(filepath, "r") as f:
        reader = csv.reader(f, delimiter=delimiter)
        rows = list(reader)

    if not rows:
        raise ValueError("Empty file: {}".format(filepath))

    col_names = None
    row_names = None
    data_start_row = 0
    data_start_col = 0

    if has_header:
        header = rows[0]
        data_start_row = 1
        if has_rownames:
            col_names = header[1:]
            data_start_col = 1
        else:
            col_names = header
            data_start_col = 0

    if has_rownames:
        row_names = [rows[i][0] for i in range(data_start_row, len(rows))]
        data_start_col = 1

    data_rows = rows[data_start_row:]
    data = np.array(
        [[float(x) for x in row[data_start_col:]] for row in data_rows],
        dtype=np.float64,
    )

    return {
        "data": data,
        "row_names": row_names,
        "col_names": col_names,
        "shape": list(data.shape),
    }


def read_mat(filepath, variable_name=None):
    # type: (str, str) -> dict
    """Read a MATLAB .mat file (v5/v7) into a numpy array with metadata.

    If ``variable_name`` is given, that variable is loaded.
    Otherwise, the first non-internal variable is used.

    Returns:
        Dict with keys: 'data' (np.ndarray), 'row_names', 'col_names', 'shape',
                         'variable_name'.
    """
    try:
        import scipy.io
    except ImportError:
        raise ImportError("scipy is required to read .mat files: pip install scipy")

    mat = scipy.io.loadmat(filepath)

    var_names = [k for k in mat.keys() if not k.startswith("__")]
    if not var_names:
        raise ValueError("No variables found in .mat file: {}".format(filepath))

    if variable_name is not None:
        if variable_name not in mat:
            raise ValueError(
                "Variable '{}' not found in {}. Available: {}".format(
                    variable_name, filepath, var_names
                )
            )
        data = np.asarray(mat[variable_name], dtype=np.float64)
        chosen = variable_name
    else:
        chosen = var_names[0]
        data = np.asarray(mat[chosen], dtype=np.float64)

    return {
        "data": data,
        "row_names": None,
        "col_names": None,
        "shape": list(data.shape),
        "variable_name": chosen,
    }


def read_tns(filepath, shape=None):
    # type: (str, list) -> dict
    """Read a .tns file in FROSTT coordinate format.

    Format: each line is ``i1 i2 ... iN value`` (whitespace-separated).
    Indices are 1-based. Lines starting with '#' are skipped.

    The data is converted to a dense numpy array. For large sparse tensors
    this may be memory-intensive; that is acceptable for the current MVP.

    Args:
        filepath: Path to .tns file.
        shape: Optional explicit shape. If None, inferred from max indices.

    Returns:
        Dict with keys: 'data' (np.ndarray), 'shape', 'nnz'.

    Raises:
        ValueError: If file is empty or malformed.
    """
    indices = []
    values = []

    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                raise ValueError(
                    "Malformed .tns line (need at least 1 index + 1 value): '{}'".format(line)
                )
            # Last element is the value; everything before is indices (1-based)
            idx = tuple(int(x) - 1 for x in parts[:-1])  # convert to 0-based
            val = float(parts[-1])
            indices.append(idx)
            values.append(val)

    if not indices:
        raise ValueError("Empty .tns file: {}".format(filepath))

    order = len(indices[0])
    for i, idx in enumerate(indices):
        if len(idx) != order:
            raise ValueError(
                "Inconsistent order at line {}: expected {} indices, got {}".format(
                    i + 1, order, len(idx)
                )
            )

    # Infer shape from max indices (0-based, so max+1)
    if shape is None:
        shape = [max(idx[d] for idx in indices) + 1 for d in range(order)]
    else:
        shape = list(shape)
        if len(shape) != order:
            raise ValueError(
                "Explicit shape has {} dims but data has {} index columns".format(
                    len(shape), order
                )
            )

    # Build dense array
    data = np.zeros(shape, dtype=np.float64)
    for idx, val in zip(indices, values):
        data[idx] = val

    return {
        "data": data,
        "shape": list(data.shape),
        "nnz": len(values),
    }


def ingest_file(filepath):
    # type: (str) -> dict
    """Ingest a data file and return metadata.

    Returns:
        Dict with keys: 'format', 'shape', and format-specific fields.
    """
    fmt = detect_format(filepath)

    if fmt == "tsv":
        result = read_tsv(filepath)
        return {
            "format": fmt,
            "shape": result["shape"],
            "row_names": result["row_names"],
            "col_names": result["col_names"],
        }
    elif fmt == "mat":
        result = read_mat(filepath)
        return {
            "format": fmt,
            "shape": result["shape"],
            "row_names": result["row_names"],
            "col_names": result["col_names"],
        }
    elif fmt == "tns":
        result = read_tns(filepath)
        return {
            "format": fmt,
            "shape": result["shape"],
            "row_names": None,
            "col_names": None,
        }
    else:
        raise NotImplementedError("Format '{}' not yet supported".format(fmt))
