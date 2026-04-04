# Config reference

Pakunoda is driven by a single `config.yaml` file.
All paths in the config are relative to the config file's directory.

## Full structure

```yaml
project:
  id: <string>              # Required. Project identifier.
  description: <string>     # Optional.

blocks:                      # Required. At least one block.
  - id: <string>             # Required. Unique within the project.
    file: <path>             # Required. Relative to config.yaml.
    kind: matrix | tensor    # Required.
    modes: [<string>, ...]   # Required. Ordered list.

relations:                   # Optional.
  - type: exact | nested     # Required.
    between:                 # Required. At least 2 entries.
      - block: <string>      # Must reference a block id.
        mode: <string>       # Must reference a mode in that block.
    mapping: <path>          # Required for nested. TSV mapping file.

solver:
  family: CoupledMWCA        # Optional. Default: CoupledMWCA.

search:
  max_rank: <int>                    # Optional. Default: 10.
  max_blocks: <int>                  # Optional. Default: all blocks.
  min_shared_fraction: <float>       # Optional. Default: 0.0. Range: 0.0-1.0.
  allow_partial_coupling: <bool>     # Optional. Default: true.
  allow_nested: <bool>               # Optional. Default: false.
  allow_frozen_modes: <bool>         # Optional. Default: false.

report:
  output_dir: <path>         # Optional. Default: results.
```

## Enumeration constraints

The `search` section controls candidate enumeration:

### max_blocks
Maximum number of blocks in a single candidate. Limits combinatorial explosion.
Default: all blocks (no limit).

### min_shared_fraction
Minimum fraction of blocks in a candidate that must participate in at least one relation.
Range: 0.0 (any subset with at least one relation) to 1.0 (all blocks must be shared).

### allow_partial_coupling
If `true` (default), candidates may include blocks not connected by any relation.
If `false`, every block in a candidate must participate in at least one relation.

### allow_nested
If `false` (default), nested relations are excluded from enumeration.
If `true`, candidates using nested relations are included.

### allow_frozen_modes
If `false` (default), all modes in every candidate are decomposed.
If `true`, an additional frozen-mode variant is generated per candidate,
where all non-shared modes have status `freeze` instead of `decompose`.

## Block kinds

- **matrix**: Must have exactly 2 modes. File shape must be (mode0_size, mode1_size).
- **tensor**: Must have 3+ modes. (Not yet tested in MVP.)

## Relation types

### exact

Two modes represent the same set of entities with the same cardinality.
Pakunoda checks that the dimensions match at validation time.

```yaml
relations:
  - type: exact
    between:
      - { block: A, mode: samples }
      - { block: B, mode: samples }
```

### nested

One mode is a grouping or subset of another. Requires a mapping file (TSV with two columns:
source entity, target entity).

```yaml
relations:
  - type: nested
    between:
      - { block: A, mode: genes }
      - { block: B, mode: gene_families }
    mapping: data/gene_to_family.tsv
```

Note: nested relation processing is defined in the schema but is a stub in the MVP.

## Supported file formats

| Extension | Format | Status |
|---|---|---|
| `.tsv` | Tab-separated values | Supported |
| `.csv` | Comma-separated values | Supported |
| `.mat` | MATLAB format | Planned |
| `.tns` | Tensor format | Planned |
