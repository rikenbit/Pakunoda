"""Snakemake script: validate config consistency and dimensional compatibility."""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pakunoda.config import load_config

configdir = snakemake.params.configdir

# Load all block metadata
block_metadata = {}
for meta_file in snakemake.input.metas:
    with open(meta_file) as f:
        meta = json.load(f)
    block_metadata[meta["block_id"]] = meta

# Validate config (paths already resolved by Snakemake)
errors = []

# Check dimensional consistency for exact relations
for rel in snakemake.config.get("relations", []):
    if rel["type"] == "exact":
        between = rel["between"]
        dims = []
        for endpoint in between:
            bid = endpoint["block"]
            mode = endpoint["mode"]
            meta = block_metadata.get(bid, {})
            block_def = next(b for b in snakemake.config["blocks"] if b["id"] == bid)
            mode_idx = block_def["modes"].index(mode)
            shape = meta.get("shape", [])
            if mode_idx < len(shape):
                dims.append((f"{bid}:{mode}", shape[mode_idx]))

        # All dims in an exact relation must match
        if len(dims) >= 2:
            first_label, first_dim = dims[0]
            for label, dim in dims[1:]:
                if dim != first_dim:
                    errors.append(
                        f"Exact relation dimension mismatch: "
                        f"{first_label}={first_dim} vs {label}={dim}"
                    )

report = {
    "valid": len(errors) == 0,
    "errors": errors,
    "blocks_checked": list(block_metadata.keys()),
    "relations_checked": len(snakemake.config.get("relations", [])),
}

with open(snakemake.output.report, "w") as f:
    json.dump(report, f, indent=2)

if errors:
    raise ValueError("Validation failed:\n  " + "\n  ".join(errors))
