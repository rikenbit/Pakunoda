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

## Run

```bash
snakemake --snakefile ../../Snakefile --configfile config.yaml --cores 1
```

Output will be in `results/toy_heterogeneous/problem.json`.
