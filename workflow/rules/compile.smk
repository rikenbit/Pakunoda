# Rule: compile
# Project-level compile: generates a single problem.json covering ALL blocks.
# This is the original MVP path, kept for backward compatibility.
# For per-candidate compilation, see compile_candidates.smk.

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
