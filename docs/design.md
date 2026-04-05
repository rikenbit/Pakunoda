# Pakunoda design document

## Responsibility split

### mwTensor (solver)

- Accepts a single, fully-defined decomposition problem
- Performs the actual coupled/joint matrix-tensor factorization
- Returns factor matrices and diagnostics

### Pakunoda (compiler + workflow)

- Reads heterogeneous data files and a declarative config
- Validates dimensional consistency and relation compatibility
- Builds the relation graph connecting blocks via shared modes
- Enumerates valid decomposition candidates under constraints
- Compiles each candidate into a structured definition that mwTensor can consume
- Executes candidates via R bridge to mwTensor (or mock solver)
- Scores and ranks results by reconstruction error and complexity
- (Future) Generates reports

## Pipeline stages

```
config.yaml + data files
        |
        v
    [ingest]              Read files, detect format, extract metadata
        |
        v
    [canonicalize]        Convert to common internal format (.npy)
        |
        v
    [validate]            Check config consistency, dimension matching
        |
        v
    [graph]               Build relation graph
        |
        v
    [enumerate]           Constrained candidate enumeration
        |
        v
    [compile_candidates]  Compile each candidate into a problem JSON
        |
        v
    [run_candidates]      Execute via mwTensor or mock solver
        |
        v
    [score_candidates]    Score: reconstruction error, runtime, complexity
        |
        v
    [summarize]           Aggregate into ranked summary
        |
        v
    summary.json / summary.tsv
```

## Three-layer architecture: Graph → Candidate → Problem

Pakunoda's core logic is organized in three layers:

### Layer 1: Relation Graph

There are two representations of the relation graph, used at different stages:

- `pakunoda/relation_graph.py` — dict-based. Used by the `graph` Snakemake rule to produce
  `relation_graph.json`. Simple, serializable, used for the legacy `compile` path.
- `pakunoda/graph.py` — typed `RelationGraph` dataclass. Used by `enumerate` and `search`.
  Built from config via `RelationGraph.from_config()` or from the JSON via
  `RelationGraph.from_graph_json()`.

The **RelationGraph** dataclass holds:

- **Blocks**: the data matrices/tensors declared in config
- **ModeNodes**: each (block, mode) pair with its dimension
- **Relations**: exact or nested connections between modes across blocks

The graph provides query methods used by enumeration:
`get_relations_for_blocks()`, `get_shared_block_ids()`, `get_coupled_modes()`.

### Layer 2: Candidate (`pakunoda/candidate.py`)

A **Candidate** is a specific decomposition configuration. It specifies:

- Which **block subset** to include (>= 2 blocks)
- **ModeAssignments**: for each mode in each block, whether to `decompose` or `freeze`,
  and whether the factor is `common` (shared via coupling) or `specific` (block-local)
- **Couplings**: which modes are coupled together (from relations)
- **Rank**: placeholder (null until search fills it in)
- **Solver family**: `CoupledMWCA`

Enumeration generates candidates by:
1. Iterating over block subsets of size 2..max_blocks
2. Finding applicable relations within each subset
3. Checking constraints (shared fraction, partial coupling, nested, frozen)
4. Building mode assignments: coupled modes → common, uncoupled → specific

### Layer 3: Problem JSON (compiled output)

The **compile_candidate** function transforms a Candidate into a
`CoupledMWCAParams`-equivalent JSON structure that mwTensor can consume.

The search pipeline uses `patch_problem_for_trial(problem, params)` to overlay
trial-specific hyperparameters (rank, init_policy) onto the base problem dict
before passing to the solver function.

### Contract between compile_candidate (Python) and run_candidate.R

The problem JSON is the contract between the Python compiler and the R bridge.
Here is how each field maps to `CoupledMWCAParams`:

| Problem JSON field | mwTensor mapping | Notes |
|---|---|---|
| `tensors[].data_file` | `Xs` (named list of arrays) | Loaded via RcppCNPy |
| `tensors[].id` | Names of `Xs` list | e.g. `Xs$expression` |
| `couplings[].members` | `common_model` factor labels | Members of the same coupling group share the same factor label (F0, F1, ...), which means mwTensor forces the same factor matrix across those modes |
| `mode_assignments[].sharing=common` | Factor label from coupling (F0, F1, ...) in `common_model` | Shared across blocks |
| `mode_assignments[].sharing=specific` | Unique factor label (S0, S1, ...) in `common_model` | Per-block; NOT mwTensor's `specific_model` |
| `mode_assignments[].status=decompose` | `common_decomp[[factor]] = TRUE` | Factor is optimized |
| `mode_assignments[].status=freeze` | `common_decomp[[factor]] = FALSE` | Factor is fixed at initial values |
| `rank` | `common_dims[[factor]] = rank` for ALL factors | Uniform rank; future: per-factor rank |
| `solver.init_policy` | `initCoupledMWCA(params, init_policy=...)` | random / svd / nonneg_random |
| `solver.seed` | `initCoupledMWCA(params, seed=...)` | Reproducibility |
| `nested_relations[]` | **Rejected** | R bridge raises error if non-empty |

**Important**: Pakunoda v0.2 places ALL factors (shared and non-shared) in
mwTensor's `common_model`.  mwTensor's `specific_model` layer (`params@specific`)
is left at `FALSE`.  This means `specific_dims` and `specific_decomp` are unused.
Pakunoda's "specific" refers to a non-shared factor *within* `common_model`,
not mwTensor's `specific_model`.

**Mode labels**: Each mode gets a globally unique I-label (I1, I2, I3, ...).
Modes in the same coupling group share the same I-label because they represent
the same set of entities with identical dimensions.  mwTensor validates this
dimension match internally.

## Enumeration constraints

The `search` section of config.yaml controls enumeration:

| Constraint | Default | Effect |
|---|---|---|
| `max_blocks` | all | Maximum blocks per candidate |
| `min_shared_fraction` | 0.0 | Minimum fraction of blocks in at least one relation |
| `allow_partial_coupling` | true | If false, every block must participate in a relation |
| `allow_nested` | false | Include nested relations in enumeration |
| `allow_frozen_modes` | false | Generate frozen-mode variants |

When `allow_frozen_modes` is true, each candidate gets an additional variant where
all non-shared modes are frozen. This doubles the candidate count at most.

## Config-first design

All behavior is driven by `config.yaml`. There are no CLI flags that change semantics.
The config declares:

1. What data exists (blocks)
2. How data relates (relations)
3. What solver to use
4. Search bounds and enumeration constraints

## Relation types

- **exact**: Two modes represent the same entities in the same order and count.
  Dimensions must match exactly.
- **nested**: One mode's entities are a subset or grouping of another's
  (e.g., genes → gene families).  Requires a mapping file.
  **Not yet executable**: mwTensor's `CoupledMWCA` requires exact dimension
  matching across shared factors, so nested relations cannot be directly passed
  to the solver.  A future implementation would pre-aggregate data using the
  mapping matrix before coupling.  Currently, candidates with nested relations
  are enumerated but rejected at run time with an explicit error.

## Key design decisions

1. **Snakemake for workflow**: Provides dependency tracking, parallelism, and container support.
2. **Python for logic**: Config validation, graph construction, enumeration, and compilation are pure Python.
3. **JSON for intermediate artifacts**: All pipeline stages communicate via JSON metadata files.
4. **NumPy for canonical format**: All data is converted to .npy for uniform access.
5. **Constrained enumeration**: Block subset enumeration with explicit constraints, not exhaustive search.
6. **R bridge with mock fallback**: mwTensor is called via Rscript. When R/mwTensor is unavailable, a mock solver (SVD-based) allows the pipeline to run end-to-end for development and testing.

## Execution and scoring

### Execution (`run_candidates`)

Each compiled candidate is executed by calling `scripts/run_candidate.R` via `Rscript`.
The R script:
1. Reads the problem JSON
2. Loads .npy data files
3. Builds `Xs` (data list) and `common_model` (coupling structure)
4. Calls `defaultCoupledMWCAParams()` and `CoupledMWCA()`
5. Saves `result.json` with reconstruction error and timing
6. On failure, writes a structured error result

If R or mwTensor is unavailable and `search.mock: true`, a Python mock solver computes
SVD-based reconstruction error per matrix (truncated to `max_rank` singular values).

### Scoring (`score_candidates`)

Each result is scored with:
- **reconstruction_error**: from the solver or mock
- **runtime_seconds**: wall clock time
- **total_params**: sum of (dimension * rank) across all modes and blocks
- **success/failure**: boolean with error message on failure

### Summarization (`summarize`)

All scores are aggregated into:
- `summary.json`: ranked list of candidates sorted by reconstruction error, plus config snapshot
- `summary.tsv`: tabular format for quick inspection

## Search and recommendation

### Optuna search (`run_search`)

Each candidate gets its own Optuna study (stored in a shared SQLite file).
The objective is **imputation RMSE**: elements are masked at random, the solver
runs on the masked data, and error is measured on the held-out elements.

Search parameters (per trial):
- **rank** — integer in `rank_range`
- **init_policy** — categorical from `init_policies`
- **weight_scaling** — optional float range

The mock solver (SVD-based) is used when `search.mock: true` or R/mwTensor
is unavailable. The mock only handles 2D matrices; higher-order tensors are
returned unchanged.

### Recommendation (`recommend`)

`recommendation.yaml` is produced by `pakunoda/search/recommend.py` and contains:

- **best_by_error** — candidate + trial with lowest imputation RMSE
- **best_by_balanced** — candidate + trial with lowest weighted score
  (0.7 * normalized error + 0.3 * normalized complexity).
  These weights are **fixed heuristics**, not learned.
- **top_n** — top candidates ranked by error
- **explanation** — one-line natural-language summary

The balanced score uses min-max normalization across candidates, so it is only
meaningful when there are at least 2 successful candidates.
