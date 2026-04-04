# Rule: run_search
# Runs Optuna-based search for each candidate.

rule run_search:
    input:
        search_manifest=os.path.join(OUTDIR, PROJECT_ID, "search", "search_manifest.json")
    output:
        search_results=os.path.join(OUTDIR, PROJECT_ID, "search", "search_results.json")
    params:
        storage_path=os.path.join(OUTDIR, PROJECT_ID, "search", "study.sqlite3")
    script:
        "../../scripts/run_search.py"
