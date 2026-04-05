# Rule: compile_candidates
# Compiles each enumerated candidate into a mwTensor problem definition.
# Produces one problem JSON per candidate, plus a manifest.

rule compile_candidates:
    input:
        candidates=os.path.join(OUTDIR, PROJECT_ID, "candidates", "candidates.json"),
        nested_manifest=os.path.join(OUTDIR, PROJECT_ID, "preprocess", "nested_manifest.json"),
        canonicals=expand(
            os.path.join(OUTDIR, PROJECT_ID, "canonical", "{idx}.npy"),
            idx=range(len(config["blocks"]))
        ),
        metas=expand(
            os.path.join(OUTDIR, PROJECT_ID, "ingest", "{idx}.meta.json"),
            idx=range(len(config["blocks"]))
        )
    output:
        manifest=os.path.join(OUTDIR, PROJECT_ID, "candidates", "compiled_manifest.json")
    params:
        configdir=CONFIGDIR,
        outdir=os.path.join(OUTDIR, PROJECT_ID, "candidates")
    script:
        "../../scripts/compile_candidates.py"
