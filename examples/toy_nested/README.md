# Toy nested example

Two matrices with one exact and one nested relation:

```
expression (4x6)  --[samples]--> pathway_scores (4x3)
expression (4x6)  --[genes→pathways]--> pathway_scores (4x3)  (nested, via mapping)
```

## Data

| Block | Shape | Modes |
|---|---|---|
| expression | 4 x 6 | samples, genes |
| pathway_scores | 4 x 3 | samples, pathways |

## Mapping

`data/gene_to_pathway.tsv` maps 6 genes to 3 pathways (2 genes per pathway).

## How nested preprocessing works

Pakunoda aggregates `expression` along the `genes` mode using the mapping file,
producing an aggregated block `expression_agg_pathways` (4 x 3).
The nested relation is then replaced by an exact relation between
`expression_agg_pathways:pathways` and `pathway_scores:pathways`.

## Run (mock mode)

```bash
snakemake --snakefile ../../Snakefile --configfile config.yaml --cores 1
```
