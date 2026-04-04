# Rule: canonicalize
# Converts each input file to a common internal format (NumPy .npy).

rule canonicalize:
    input:
        data=lambda wc: config["blocks"][int(wc.block_idx)]["file"],
        meta=os.path.join(OUTDIR, PROJECT_ID, "ingest", "{block_idx}.meta.json")
    output:
        npy=os.path.join(OUTDIR, PROJECT_ID, "canonical", "{block_idx}.npy")
    params:
        block_idx=lambda wc: int(wc.block_idx),
        configdir=CONFIGDIR
    script:
        "../../scripts/canonicalize.py"
