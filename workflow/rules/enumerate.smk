# Rule: enumerate
# Enumerates valid decomposition candidates under search constraints.
# Uses the relation graph (which already includes aggregated blocks from nested preprocessing).

rule enumerate:
    input:
        graph=os.path.join(OUTDIR, PROJECT_ID, "graph", "relation_graph.json"),
        nested_manifest=os.path.join(OUTDIR, PROJECT_ID, "preprocess", "nested_manifest.json"),
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
