# Rule: ingest
# Reads each input file, detects format, extracts shape and mode names.
# Produces a metadata JSON per block.

rule ingest:
    input:
        data=lambda wc: config["blocks"][int(wc.block_idx)]["file"]
    output:
        meta=os.path.join(OUTDIR, PROJECT_ID, "ingest", "{block_idx}.meta.json")
    params:
        block_idx=lambda wc: int(wc.block_idx),
        configdir=CONFIGDIR
    script:
        "../../scripts/ingest.py"
