# Rule: recommend
# Generates a recommendation report from search results.

rule recommend:
    input:
        search_results=os.path.join(OUTDIR, PROJECT_ID, "search", "search_results.json")
    output:
        recommendation=os.path.join(OUTDIR, PROJECT_ID, "search", "recommendation.yaml")
    script:
        "../../scripts/recommend.py"
