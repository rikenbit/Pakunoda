# Toy heterogeneous example

Three matrices with two exact relations, forming a chain structure:

```
methylation (5x3)  --[samples]-->  expression (5x4)  --[genes]-->  interaction (4x3)
```

## Data

| Block | Shape | Modes |
|---|---|---|
| expression | 5 x 4 | samples, genes |
| methylation | 5 x 3 | samples, cpg_sites |
| interaction | 4 x 3 | genes, proteins |

## Relations

| Type | From | To |
|---|---|---|
| exact | expression:samples | methylation:samples |
| exact | expression:genes | interaction:genes |

## Run with real solver (Docker)

```bash
docker run --rm -v $(pwd):/work ghcr.io/rikenbit/pakunoda:latest \
  --snakefile /app/Snakefile --configfile /work/config.yaml --cores 1
```

## Run with mock solver (no R required)

```bash
snakemake --snakefile ../../Snakefile --configfile config_mock.yaml --cores 1
```

## Output

Results are written to `results/toy_heterogeneous/`.
See `summary.tsv` for the ranked candidate table and `search/recommendation.yaml` for search results (mock mode only by default).
