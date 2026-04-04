# Rule: enumerate
# Enumerates valid decomposition candidates under search constraints.
# Produces a candidates.json listing all candidates.

rule enumerate:
    input:
        graph=os.path.join(OUTDIR, PROJECT_ID, "graph", "relation_graph.json"),
        metas=expand(
            os.path.join(OUTDIR, PROJECT_ID, "ingest", "{idx}.meta.json"),
            idx=range(len(config["blocks"]))
        )
    output:
        candidates=os.path.join(OUTDIR, PROJECT_ID, "candidates", "candidates.json")
    params:
        configdir=CONFIGDIR
    script:
        "../../scripts/enumerate.py"
