# Rule: summarize_search
# Produces trials table, best JSON, and summary TSV from search results.

rule summarize_search:
    input:
        search_results=os.path.join(OUTDIR, PROJECT_ID, "search", "search_results.json")
    output:
        trials_tsv=os.path.join(OUTDIR, PROJECT_ID, "search", "trials.tsv"),
        best_json=os.path.join(OUTDIR, PROJECT_ID, "search", "best.json"),
        summary_tsv=os.path.join(OUTDIR, PROJECT_ID, "search", "summary.tsv")
    script:
        "../../scripts/summarize_search.py"
