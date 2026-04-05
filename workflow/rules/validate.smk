# Rule: validate
# Checks config consistency, dimensional compatibility, and relation validity.
# Runs after preprocess_nested so that aggregated blocks are available.

rule validate:
    input:
        metas=expand(
            os.path.join(OUTDIR, PROJECT_ID, "ingest", "{idx}.meta.json"),
            idx=range(len(config["blocks"]))
        ),
        nested_manifest=os.path.join(OUTDIR, PROJECT_ID, "preprocess", "nested_manifest.json")
    output:
        report=os.path.join(OUTDIR, PROJECT_ID, "validate", "report.json")
    params:
        configdir=CONFIGDIR
    script:
        "../../scripts/validate.py"
