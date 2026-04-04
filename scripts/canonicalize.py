"""Snakemake script: convert a block file to canonical NumPy format."""

import json
import sys
import os

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pakunoda.io import read_tsv, detect_format

filepath = snakemake.input.data

fmt = detect_format(filepath)
if fmt == "tsv":
    result = read_tsv(filepath)
    np.save(snakemake.output.npy, result["data"])
else:
    raise NotImplementedError(f"Format '{fmt}' not yet supported in MVP")
