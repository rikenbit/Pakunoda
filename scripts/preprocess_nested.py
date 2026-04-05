"""Snakemake script: preprocess nested relations by aggregating source blocks.

For each nested relation:
1. Read the mapping file
2. Aggregate the source block along the mapped mode
3. Save the aggregated block as a new .npy file
4. Record a replacement: the nested relation becomes exact

If no nested relations exist, produce a manifest indicating no changes.
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pakunoda.preprocess_nested import preprocess_nested_relation

outdir = snakemake.params.outdir
os.makedirs(outdir, exist_ok=True)

config = snakemake.config
relations = config.get("relations", [])
blocks = config["blocks"]

# Load all block metadata
block_meta = {}
for meta_file in snakemake.input.metas:
    with open(meta_file) as f:
        meta = json.load(f)
    block_meta[meta["block_id"]] = meta

# Load all canonical data
block_data = {}
for i, canonical_file in enumerate(snakemake.input.canonicals):
    bid = blocks[i]["id"]
    block_data[bid] = np.load(canonical_file)

# Process nested relations
aggregated_blocks = []  # new blocks produced by aggregation
replaced_relations = []  # nested relations replaced by exact

for rel in relations:
    if rel.get("type") != "nested":
        continue

    between = rel["between"]
    if len(between) != 2:
        raise ValueError("Nested relation must have exactly 2 endpoints")

    mapping_file = rel.get("mapping")
    if not mapping_file:
        raise ValueError("Nested relation requires 'mapping' field")

    # Identify source and target: source has the fine-grained mode,
    # target has the coarse-grained mode.
    ep0_block = between[0]["block"]
    ep0_mode = between[0]["mode"]
    ep1_block = between[1]["block"]
    ep1_mode = between[1]["mode"]

    # Source is the one whose mode has more entities (fine-grained)
    meta0 = block_meta[ep0_block]
    meta1 = block_meta[ep1_block]
    block0_def = next(b for b in blocks if b["id"] == ep0_block)
    block1_def = next(b for b in blocks if b["id"] == ep1_block)

    mode0_axis = block0_def["modes"].index(ep0_mode)
    mode1_axis = block1_def["modes"].index(ep1_mode)
    dim0 = meta0["shape"][mode0_axis]
    dim1 = meta1["shape"][mode1_axis]

    if dim0 >= dim1:
        source_bid, source_mode = ep0_block, ep0_mode
        target_bid, target_mode = ep1_block, ep1_mode
    else:
        source_bid, source_mode = ep1_block, ep1_mode
        target_bid, target_mode = ep0_block, ep0_mode

    source_def = next(b for b in blocks if b["id"] == source_bid)
    source_meta = block_meta[source_bid]
    target_def = next(b for b in blocks if b["id"] == target_bid)
    target_meta = block_meta[target_bid]

    # Build entity name dicts
    source_mode_axis = source_def["modes"].index(source_mode)
    source_names = {}
    if source_mode_axis == 0 and source_meta.get("row_names"):
        source_names[source_mode] = source_meta["row_names"]
    elif source_mode_axis == 1 and source_meta.get("col_names"):
        source_names[source_mode] = source_meta["col_names"]

    target_mode_axis = target_def["modes"].index(target_mode)
    target_names = {}
    if target_mode_axis == 0 and target_meta.get("row_names"):
        target_names[target_mode] = target_meta["row_names"]
    elif target_mode_axis == 1 and target_meta.get("col_names"):
        target_names[target_mode] = target_meta["col_names"]

    result = preprocess_nested_relation(
        source_data=block_data[source_bid],
        source_modes=source_def["modes"],
        source_mode_names=source_names,
        target_modes=target_def["modes"],
        target_mode_names=target_names,
        nested_source_mode=source_mode,
        nested_target_mode=target_mode,
        mapping_file=mapping_file,
    )

    # Save aggregated data
    agg_id = "{}_agg_{}".format(source_bid, target_mode)
    agg_npy = os.path.join(outdir, "{}.npy".format(agg_id))
    np.save(agg_npy, result["data"])

    aggregated_blocks.append({
        "id": agg_id,
        "original_block": source_bid,
        "kind": source_def["kind"],
        "modes": result["modes"],
        "shape": result["shape"],
        "canonical_file": agg_npy,
        "aggregated_mode": result["aggregated_mode"],
    })

    replaced_relations.append({
        "original_type": "nested",
        "original_between": [
            {"block": source_bid, "mode": source_mode},
            {"block": target_bid, "mode": target_mode},
        ],
        "replacement_type": "exact",
        "replacement_between": [
            {"block": agg_id, "mode": target_mode},
            {"block": target_bid, "mode": target_mode},
        ],
    })

# Write manifest
manifest = {
    "project_id": config["project"]["id"],
    "num_nested_processed": len(aggregated_blocks),
    "aggregated_blocks": aggregated_blocks,
    "replaced_relations": replaced_relations,
}

with open(snakemake.output.manifest, "w") as f:
    json.dump(manifest, f, indent=2)
