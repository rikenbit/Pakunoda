# Rule: validate
# Checks config consistency, dimensional compatibility, and relation validity.
# Runs once for the entire project (not per block).

rule validate:
    input:
        metas=expand(
            os.path.join(OUTDIR, PROJECT_ID, "ingest", "{idx}.meta.json"),
            idx=range(len(config["blocks"]))
        )
    output:
        report=os.path.join(OUTDIR, PROJECT_ID, "validate", "report.json")
    params:
        configdir=CONFIGDIR
    script:
        "../../scripts/validate.py"
