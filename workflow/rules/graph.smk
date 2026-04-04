# Rule: graph
# Builds the relation graph connecting blocks via shared/related modes.

rule graph:
    input:
        validation=os.path.join(OUTDIR, PROJECT_ID, "validate", "report.json"),
        metas=expand(
            os.path.join(OUTDIR, PROJECT_ID, "ingest", "{idx}.meta.json"),
            idx=range(len(config["blocks"]))
        )
    output:
        graph=os.path.join(OUTDIR, PROJECT_ID, "graph", "relation_graph.json")
    params:
        configdir=CONFIGDIR
    script:
        "../../scripts/graph.py"
