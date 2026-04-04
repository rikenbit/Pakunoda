# Rule: score_candidates
# Scores each candidate run result.
# Produces a score JSON per candidate and a score manifest.

rule score_candidates:
    input:
        run_manifest=os.path.join(OUTDIR, PROJECT_ID, "runs", "run_manifest.json"),
        compiled_manifest=os.path.join(OUTDIR, PROJECT_ID, "candidates", "compiled_manifest.json")
    output:
        score_manifest=os.path.join(OUTDIR, PROJECT_ID, "scores", "score_manifest.json")
    params:
        outdir=os.path.join(OUTDIR, PROJECT_ID, "scores")
    script:
        "../../scripts/score_candidates.py"
