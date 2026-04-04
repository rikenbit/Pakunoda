# Pakunoda

**Factorization problem compiler and reproducible workflow for heterogeneous matrix/tensor data.**

Pakunoda takes a collection of heterogeneous matrices and tensors with shared or related modes,
constructs coupled/joint decomposition problems from a declarative configuration,
runs them through [mwTensor](https://github.com/rikenbit/mwTensor), and produces a ranked summary.

## What Pakunoda is

- A **config-first workflow** that turns `config.yaml` + data files into validated, scored decomposition results
- A **problem compiler** that builds the relation graph, enumerates candidates, and generates solver-ready structures
- A **reproducible pipeline** built on Snakemake with container support

## What Pakunoda is NOT

- **Not a solver library.** The actual decomposition is performed by `mwTensor`. Pakunoda constructs the problem; `mwTensor` solves it.
- **Not a visualization tool.** Report generation is planned but not yet implemented.
- **Not a full AutoML system.** Optuna-based MVP search (rank, init policy) is implemented, but advanced features — multi-objective optimization, richer recommendation, and automated model selection — are not yet available.

## Responsibility split

| Concern | Owner |
|---|---|
| Read data, validate config, build relation graph | **Pakunoda** |
| Enumerate decomposition candidates | **Pakunoda** |
| Execute candidates via solver | **Pakunoda** (calls mwTensor) |
| Score and rank results | **Pakunoda** |
| Solve a single defined decomposition problem | **mwTensor** |
| Hyperparameter search (Optuna) | **Pakunoda** |
| Report generation | **Pakunoda** (future) |

## Current scope and limitations (v0.1.0)

**What works:**
- Relations: `exact` and `nested`
- Solver family: `CoupledMWCA` only
- Scoring: reconstruction error, runtime, total model complexity
- Search: Optuna-based imputation search over rank and init policy
- File formats: `.tsv` and `.csv` only

**Mock / stub areas:**
- **Mock solver.** When `search.mock: true` (or R/mwTensor is unavailable), all execution uses a Python SVD-based approximation instead of mwTensor. The mock solver only handles 2D matrices; higher-order tensors are returned as-is. The toy example runs entirely in mock mode.
- **Nested relation mappings.** `nested` relations are accepted in config and enumerated as candidates, but execution is blocked: `run_candidate.R` and `run_candidates.py` raise an explicit error if a candidate contains nested relations. The mapping file path is preserved in the problem JSON but not yet processed.
- **Recommendation heuristics.** `best_by_balanced_score` uses fixed weights (0.7 error, 0.3 complexity) with min-max normalization. This is a simple heuristic, not a principled selection criterion.

**Not yet implemented:**
- Papermill report generation
- MCP / AI agent interface
- Multi-objective Pareto search
- Block-wise or relation-aware masking (only elementwise random)
- Stability metrics (cross-validation, bootstrap)
- `.mat` / `.tns` file format readers
- Additional solver families beyond CoupledMWCA

## Quick start

### Prerequisites

- Python >= 3.7, NumPy, Snakemake, Optuna, PyYAML
- For real solver: R >= 4.1, [mwTensor](https://github.com/rikenbit/mwTensor)
- Or use mock mode (`search.mock: true`) to run without R

### Run the toy example

```bash
snakemake --snakefile Snakefile --configfile examples/toy_heterogeneous/config.yaml --cores 1
```

### With Docker

```bash
docker build -t pakunoda .
docker run -v $(pwd)/examples/toy_heterogeneous:/work pakunoda \
  snakemake --snakefile /app/Snakefile --configfile /work/config.yaml --cores 1
```

## Configuration

Pakunoda is driven entirely by `config.yaml`. See [docs/config-reference.md](docs/config-reference.md) for the full specification.

Minimal example:

```yaml
project:
  id: my_analysis

blocks:
  - id: expression
    file: data/expression.tsv
    kind: matrix
    modes: [samples, genes]
  - id: methylation
    file: data/methylation.tsv
    kind: matrix
    modes: [samples, cpg_sites]

relations:
  - type: exact
    between:
      - { block: expression, mode: samples }
      - { block: methylation, mode: samples }

solver:
  family: CoupledMWCA

search:
  max_rank: 5
  mock: true
  enabled: true
  goal: imputation
  max_trials: 20
  seed: 42
  rank_range: [2, 5]
  init_policies: [random, svd]
  masking:
    scheme: elementwise
    fraction: 0.1
```

## Pipeline stages

| Stage | Rule | Description |
|---|---|---|
| 1 | `ingest` | Detect file formats, read dimensions, produce metadata JSON |
| 2 | `canonicalize` | Convert all inputs to a common internal format (NumPy `.npy`) |
| 3 | `validate` | Check config consistency, dimensional compatibility, relation validity |
| 4 | `graph` | Build the block-mode relation graph |
| 5 | `enumerate` | Constrained enumeration of valid decomposition candidates |
| 6 | `compile_candidates` | Compile each candidate into a mwTensor problem JSON |
| 7 | `run_candidates` | Execute each candidate via mwTensor (or mock solver) |
| 8 | `score_candidates` | Score each result: reconstruction error, runtime, complexity |
| 9 | `summarize` | Aggregate scores into ranked summary JSON and TSV |
| 10 | `prepare_search` | Create masks and search spaces (when `search.enabled: true`) |
| 11 | `run_search` | Run Optuna trials for each candidate |
| 12 | `summarize_search` | Produce trials table, best JSON, summary TSV |
| 13 | `recommend` | Generate recommendation report with best picks and explanations |

## Output structure

```
results/{project_id}/
├── ingest/                     # Per-block metadata
├── canonical/                  # Per-block .npy files
├── validate/report.json        # Validation report
├── graph/relation_graph.json   # Relation graph
├── candidates/
│   ├── candidates.json         # Enumerated candidates
│   ├── compiled_manifest.json  # Compilation manifest
│   └── *.problem.json          # Per-candidate problem definitions
├── runs/
│   ├── run_manifest.json       # Run manifest
│   └── {candidate_id}/
│       └── result.json         # Per-candidate run result
├── scores/
│   ├── score_manifest.json     # Score manifest
│   └── *.score.json            # Per-candidate scores
├── summary.json                # Ranked summary (JSON)
├── summary.tsv                 # Ranked summary (TSV)
└── search/                     # (when search.enabled: true)
    ├── study.sqlite3           # Optuna study storage
    ├── search_manifest.json    # Masks and search space config
    ├── search_results.json     # Full trial results
    ├── trials.tsv              # All trials across all candidates
    ├── best.json               # Best trial per candidate
    ├── summary.tsv             # Best results summary table
    └── recommendation.yaml     # Recommendation with explanations
```

## Project structure

```
Pakunoda/
├── Snakefile                       # Workflow entry point
├── config/schema.yaml              # Config schema reference
├── workflow/rules/                  # Snakemake rule files (13 rules)
├── pakunoda/                        # Python library
│   ├── config.py                    # Config loading and validation
│   ├── io.py                        # File format readers
│   ├── graph.py                     # Typed RelationGraph dataclass
│   ├── relation_graph.py            # Relation graph (dict-based)
│   ├── candidate.py                 # Candidate representation and enumeration
│   ├── compiler.py                  # Problem compiler for mwTensor
│   ├── scorer.py                    # Scoring and summarization
│   └── search/                      # Optuna search layer
│       ├── search_space.py          # Search space from config
│       ├── objective.py             # Trial objective (imputation RMSE)
│       ├── study.py                 # Optuna study management
│       ├── masking.py               # Data masking utilities
│       └── recommend.py             # Recommendation engine
├── scripts/                         # Scripts called by Snakemake rules
│   └── run_candidate.R              # R bridge to mwTensor
├── envs/pakunoda.yaml
├── Dockerfile
├── examples/toy_heterogeneous/
├── tests/
└── docs/
```

## Future directions

- Multi-objective search (accuracy + complexity Pareto front)
- Block-wise and relation-aware masking schemes
- Papermill-based report generation
- Additional relation types (`partial`, `hierarchical`)
- Additional solver families
- Stability and masked benchmark metrics
- MCP / AI agent interface

## License

TBD
