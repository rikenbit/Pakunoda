# Rule: preprocess_nested
# If nested relations exist, aggregates source blocks to match target dimensions.
# Replaces nested relations with exact relations in an updated config manifest.
# If no nested relations, passes through unchanged.

rule preprocess_nested:
    input:
        metas=expand(
            os.path.join(OUTDIR, PROJECT_ID, "ingest", "{idx}.meta.json"),
            idx=range(len(config["blocks"]))
        ),
        canonicals=expand(
            os.path.join(OUTDIR, PROJECT_ID, "canonical", "{idx}.npy"),
            idx=range(len(config["blocks"]))
        )
    output:
        manifest=os.path.join(OUTDIR, PROJECT_ID, "preprocess", "nested_manifest.json")
    params:
        outdir=os.path.join(OUTDIR, PROJECT_ID, "preprocess"),
        configdir=CONFIGDIR
    script:
        "../../scripts/preprocess_nested.py"
