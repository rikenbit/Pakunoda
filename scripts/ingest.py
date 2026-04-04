"""Snakemake script: ingest a single block file and produce metadata JSON."""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pakunoda.io import ingest_file

block_idx = snakemake.params.block_idx
block = snakemake.config["blocks"][block_idx]

filepath = snakemake.input.data
metadata = ingest_file(filepath)
metadata["block_id"] = block["id"]
metadata["block_idx"] = block_idx
metadata["kind"] = block["kind"]
metadata["modes"] = block["modes"]
metadata["source_file"] = filepath

with open(snakemake.output.meta, "w") as f:
    json.dump(metadata, f, indent=2)
