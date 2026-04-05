"""Snakemake script: convert a block file to canonical NumPy format."""

import sys
import os

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pakunoda.io import read_tsv, read_mat, read_tns, detect_format

filepath = snakemake.input.data

fmt = detect_format(filepath)
if fmt == "tsv":
    result = read_tsv(filepath)
elif fmt == "mat":
    result = read_mat(filepath)
elif fmt == "tns":
    result = read_tns(filepath)
else:
    raise NotImplementedError("Format '{}' not yet supported".format(fmt))

np.save(snakemake.output.npy, result["data"])
