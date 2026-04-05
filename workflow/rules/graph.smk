# Rule: graph
# Builds the relation graph connecting blocks via shared/related modes.
# Incorporates aggregated blocks from nested preprocessing if present.

rule graph:
    input:
        validation=os.path.join(OUTDIR, PROJECT_ID, "validate", "report.json"),
        metas=expand(
            os.path.join(OUTDIR, PROJECT_ID, "ingest", "{idx}.meta.json"),
            idx=range(len(config["blocks"]))
        ),
        nested_manifest=os.path.join(OUTDIR, PROJECT_ID, "preprocess", "nested_manifest.json")
    output:
        graph=os.path.join(OUTDIR, PROJECT_ID, "graph", "relation_graph.json")
    params:
        configdir=CONFIGDIR
    script:
        "../../scripts/graph.py"
