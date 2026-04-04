# Rule: summarize
# Aggregates all candidate scores into a summary JSON and TSV.

rule summarize:
    input:
        score_manifest=os.path.join(OUTDIR, PROJECT_ID, "scores", "score_manifest.json")
    output:
        summary_json=os.path.join(OUTDIR, PROJECT_ID, "summary.json"),
        summary_tsv=os.path.join(OUTDIR, PROJECT_ID, "summary.tsv")
    script:
        "../../scripts/summarize.py"
