"""File format readers for Pakunoda.

MVP supports .tsv only. Future: .mat, .tns
"""

import csv
from pathlib import Path

import numpy as np


def detect_format(filepath: str) -> str:
    """Detect file format from extension.

    Returns:
        One of: 'tsv', 'mat', 'tns'

    Raises:
        ValueError: If format is unsupported.
    """
    ext = Path(filepath).suffix.lower()
    format_map = {
        ".tsv": "tsv",
        ".csv": "tsv",  # treat csv as tsv variant
        ".mat": "mat",
        ".tns": "tns",
    }
    fmt = format_map.get(ext)
    if fmt is None:
        raise ValueError(f"Unsupported file format: {ext}")
    return fmt


def read_tsv(filepath: str, has_header: bool = True, has_rownames: bool = True) -> dict:
    """Read a TSV/CSV file into a numpy array with metadata.

    Args:
        filepath: Path to TSV/CSV file.
        has_header: Whether the first row contains column names.
        has_rownames: Whether the first column contains row names.

    Returns:
        Dict with keys: 'data' (np.ndarray), 'row_names', 'col_names', 'shape'.
    """
    ext = Path(filepath).suffix.lower()
    delimiter = "," if ext == ".csv" else "\t"

    with open(filepath, "r") as f:
        reader = csv.reader(f, delimiter=delimiter)
        rows = list(reader)

    if not rows:
        raise ValueError(f"Empty file: {filepath}")

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


def ingest_file(filepath: str) -> dict:
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
    else:
        raise NotImplementedError(f"Format '{fmt}' not yet supported in MVP")
