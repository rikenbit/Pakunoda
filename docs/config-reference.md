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
  # --- Enumeration constraints ---
  max_rank: <int>                    # Optional. Default: 10.
  max_blocks: <int>                  # Optional. Default: all blocks.
  min_shared_fraction: <float>       # Optional. Default: 0.0. Range: 0.0-1.0.
  allow_partial_coupling: <bool>     # Optional. Default: true.
  allow_nested: <bool>               # Optional. Default: false.
  allow_frozen_modes: <bool>         # Optional. Default: false.
  mock: <bool>                       # Optional. Default: false. Use SVD mock solver.

  # --- Optuna search (when enabled: true) ---
  enabled: <bool>                    # Optional. Default: false.
  goal: imputation                   # Optional. Only 'imputation' supported.
  max_trials: <int>                  # Optional. Default: 20. Trials per candidate.
  seed: <int>                        # Optional. Random seed for reproducibility.
  rank_range: [<int>, <int>]         # Optional. Default: [2, 10].
  init_policies: [<string>, ...]     # Optional. Default: [random, svd].
  weight_scaling_range: [<float>, <float>]  # Optional. Default: null (disabled).
  masking:
    scheme: elementwise              # Optional. Only 'elementwise' supported.
    fraction: <float>                # Optional. Default: 0.1.

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

### mock
If `true`, use the Python SVD-based mock solver instead of R/mwTensor.
The mock solver only handles 2D matrices.
Useful for development and testing without an R environment.

## Optuna search settings

These settings are used when `search.enabled: true`.

### enabled
Set to `true` to run the Optuna search pipeline (prepare_search → run_search → summarize_search → recommend) in addition to the core pipeline.

### goal
Currently only `imputation` is supported. The objective is to minimize RMSE on artificially masked elements.

### max_trials
Number of Optuna trials per candidate. Default: 20.

### rank_range
`[min, max]` range for the rank hyperparameter. Default: `[2, 10]`.

### init_policies
List of initialization policies to search over. Valid values: `random`, `svd`, `nonneg_random`. Default: `[random, svd]`.

### masking.scheme
Masking scheme for imputation evaluation. Currently only `elementwise` (random element-wise masking). Future: `block_wise`, `relation_aware`.

### masking.fraction
Fraction of elements to hold out. Default: 0.1.

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

One mode is a grouping or subset of another (many-to-one).
Requires a mapping file and exactly 2 endpoints.

**Ordering matters**: `between[0]` is the **source** (fine-grained, e.g. genes),
`between[1]` is the **target** (coarse-grained, e.g. pathways).
The mapping file maps source entities to target entities.

```yaml
relations:
  - type: nested
    between:
      - { block: A, mode: genes }          # source (fine-grained)
      - { block: B, mode: gene_families }  # target (coarse-grained)
    mapping: data/gene_to_family.tsv
```

Pakunoda preprocesses nested relations by aggregating the source block along the
source mode (group-mean), producing an aggregated block whose dimension matches
the target. The nested relation is then replaced by an exact relation.

Limitations:
- Only 2D matrices (not tensors)
- Only many-to-one direction (source → target aggregation)
- Only mean aggregation (no weighted or custom functions)
- Source block must have entity names for the mapped mode (from TSV headers)

### Mapping file format

Two columns, tab-separated, no header. Each row is `source_id<TAB>target_id`.
Lines starting with `#` are ignored.

```
gene1	pathwayA
gene2	pathwayA
gene3	pathwayB
```

The source block must have entity names (row_names or col_names from ingest) for
the mapped mode. Only many-to-one mappings are supported (multiple sources per target).

## Supported file formats

| Extension | Format | Status |
|---|---|---|
| `.tsv` | Tab-separated values | Supported |
| `.csv` | Comma-separated values | Supported |
| `.mat` | MATLAB v5/v7 | Supported |
| `.tns` | FROSTT coordinate format | Supported (dense conversion; no out-of-core) |

### `.tns` format

Each line is `i1 i2 ... iN value` (whitespace-separated).
Indices are **1-based**. Lines starting with `#` are skipped.
The tensor is read into a dense numpy array (shape inferred from max indices).

```
1 1 1 5.0
2 1 2 3.0
1 2 1 7.0
```

For large sparse tensors, the dense conversion may be memory-intensive.
An explicit shape can be provided in the block config (future feature).
