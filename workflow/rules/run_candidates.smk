# Rule: run_candidates
# Runs each compiled candidate through the solver (mwTensor or mock).
# Produces a result JSON per candidate and a run manifest.

rule run_candidates:
    input:
        manifest=os.path.join(OUTDIR, PROJECT_ID, "candidates", "compiled_manifest.json"),
        canonicals=expand(
            os.path.join(OUTDIR, PROJECT_ID, "canonical", "{idx}.npy"),
            idx=range(len(config["blocks"]))
        )
    output:
        run_manifest=os.path.join(OUTDIR, PROJECT_ID, "runs", "run_manifest.json")
    params:
        outdir=os.path.join(OUTDIR, PROJECT_ID, "runs"),
        configdir=CONFIGDIR
    script:
        "../../scripts/run_candidates.py"
