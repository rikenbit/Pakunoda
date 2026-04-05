"""File format readers for Pakunoda.

Supported: .tsv, .csv, .mat (MATLAB v5/v7)
Planned: .tns (sparse tensor)
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

    Raises:
        ValueError: If no suitable variable is found.
    """
    try:
        import scipy.io
    except ImportError:
        raise ImportError("scipy is required to read .mat files: pip install scipy")

    mat = scipy.io.loadmat(filepath)

    # Filter out internal keys (start with __)
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


def ingest_file(filepath):
    # type: (str) -> dict
    """Ingest a data file and return metadata.

    Returns:
        Dict with keys: 'format', 'shape', 'row_names', 'col_names'.
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
    else:
        raise NotImplementedError("Format '{}' not yet supported".format(fmt))
