# Rule: prepare_search
# Loads data, creates masks, builds search space for each candidate.

rule prepare_search:
    input:
        compiled_manifest=os.path.join(OUTDIR, PROJECT_ID, "candidates", "compiled_manifest.json"),
        canonicals=expand(
            os.path.join(OUTDIR, PROJECT_ID, "canonical", "{idx}.npy"),
            idx=range(len(config["blocks"]))
        )
    output:
        search_manifest=os.path.join(OUTDIR, PROJECT_ID, "search", "search_manifest.json")
    params:
        outdir=os.path.join(OUTDIR, PROJECT_ID, "search")
    script:
        "../../scripts/prepare_search.py"
