# Rule: compile
# Generates the structured problem definition JSON for mwTensor.
# This is the final output of the MVP pipeline.

rule compile:
    input:
        graph=os.path.join(OUTDIR, PROJECT_ID, "graph", "relation_graph.json"),
        canonicals=expand(
            os.path.join(OUTDIR, PROJECT_ID, "canonical", "{idx}.npy"),
            idx=range(len(config["blocks"]))
        ),
        metas=expand(
            os.path.join(OUTDIR, PROJECT_ID, "ingest", "{idx}.meta.json"),
            idx=range(len(config["blocks"]))
        )
    output:
        problem=os.path.join(OUTDIR, PROJECT_ID, "problem.json")
    params:
        configdir=CONFIGDIR
    script:
        "../../scripts/compile.py"
