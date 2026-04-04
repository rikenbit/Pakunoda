"""Config loading and validation for Pakunoda."""

import os
from pathlib import Path

# Allowed values
VALID_KINDS = {"matrix", "tensor"}
VALID_RELATION_TYPES = {"exact", "nested"}
VALID_SOLVER_FAMILIES = {"CoupledMWCA"}


def load_config(config_dict: dict, base_dir: str = ".") -> dict:
    """Normalize and validate a Pakunoda config dict.

    Args:
        config_dict: Raw config dict (from Snakemake config or YAML load).
        base_dir: Base directory for resolving relative file paths.

    Returns:
        Validated config dict with resolved paths.

    Raises:
        ValueError: If config is invalid.
    """
    errors = []

    # --- project ---
    project = config_dict.get("project")
    if not project or not project.get("id"):
        errors.append("project.id is required")

    # --- blocks ---
    blocks = config_dict.get("blocks", [])
    if not blocks:
        errors.append("At least one block is required")

    block_ids = set()
    block_modes = {}  # block_id -> list of mode names
    for i, block in enumerate(blocks):
        bid = block.get("id")
        if not bid:
            errors.append(f"blocks[{i}].id is required")
            continue

        if bid in block_ids:
            errors.append(f"Duplicate block id: {bid}")
        block_ids.add(bid)

        # file path
        fpath = block.get("file")
        if not fpath:
            errors.append(f"blocks[{i}].file is required")
        else:
            resolved = os.path.join(base_dir, fpath)
            block["file"] = resolved

        # kind
        kind = block.get("kind")
        if kind not in VALID_KINDS:
            errors.append(f"blocks[{i}].kind must be one of {VALID_KINDS}, got '{kind}'")

        # modes
        modes = block.get("modes", [])
        if not modes:
            errors.append(f"blocks[{i}].modes must be a non-empty list")
        if kind == "matrix" and len(modes) != 2:
            errors.append(f"blocks[{i}]: matrix must have exactly 2 modes, got {len(modes)}")

        block_modes[bid] = modes

    # --- relations ---
    relations = config_dict.get("relations", [])
    for i, rel in enumerate(relations):
        rtype = rel.get("type")
        if rtype not in VALID_RELATION_TYPES:
            errors.append(
                f"relations[{i}].type must be one of {VALID_RELATION_TYPES}, got '{rtype}'"
            )

        between = rel.get("between", [])
        if len(between) < 2:
            errors.append(f"relations[{i}].between must have at least 2 entries")

        for j, endpoint in enumerate(between):
            blk = endpoint.get("block")
            mode = endpoint.get("mode")
            if blk not in block_ids:
                errors.append(f"relations[{i}].between[{j}].block '{blk}' not found")
            elif mode not in block_modes.get(blk, []):
                errors.append(
                    f"relations[{i}].between[{j}].mode '{mode}' not in block '{blk}' modes"
                )

        # nested requires mapping
        if rtype == "nested" and not rel.get("mapping"):
            errors.append(f"relations[{i}]: nested relation requires 'mapping' field")
        if rtype == "nested" and rel.get("mapping"):
            resolved = os.path.join(base_dir, rel["mapping"])
            rel["mapping"] = resolved

    # --- solver ---
    solver = config_dict.get("solver", {})
    family = solver.get("family")
    if family and family not in VALID_SOLVER_FAMILIES:
        errors.append(f"solver.family must be one of {VALID_SOLVER_FAMILIES}, got '{family}'")

    if errors:
        raise ValueError("Config validation errors:\n  " + "\n  ".join(errors))

    return config_dict
