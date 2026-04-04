# Pakunoda - Factorization problem compiler for heterogeneous matrix/tensor data
#
# Entry point for the Snakemake workflow.
# All configuration is provided via config.yaml (--configfile).

import os

# Resolve paths relative to the config file location
CONFIGDIR = os.path.dirname(os.path.abspath(workflow.configfiles[0])) if workflow.configfiles else os.getcwd()
OUTDIR = os.path.join(CONFIGDIR, config.get("report", {}).get("output_dir", "results"))
PROJECT_ID = config["project"]["id"]

# Resolve block file paths relative to config directory
for _block in config["blocks"]:
    if not os.path.isabs(_block["file"]):
        _block["file"] = os.path.join(CONFIGDIR, _block["file"])

# Determine final targets based on search config
SEARCH_ENABLED = config.get("search", {}).get("enabled", False)

_targets = [
    os.path.join(OUTDIR, PROJECT_ID, "summary.json"),
    os.path.join(OUTDIR, PROJECT_ID, "summary.tsv"),
]
if SEARCH_ENABLED:
    _targets.extend([
        os.path.join(OUTDIR, PROJECT_ID, "search", "recommendation.yaml"),
        os.path.join(OUTDIR, PROJECT_ID, "search", "summary.tsv"),
        os.path.join(OUTDIR, PROJECT_ID, "search", "best.json"),
        os.path.join(OUTDIR, PROJECT_ID, "search", "trials.tsv"),
    ])


rule all:
    input:
        _targets


# Core pipeline
include: "workflow/rules/ingest.smk"
include: "workflow/rules/canonicalize.smk"
include: "workflow/rules/validate.smk"
include: "workflow/rules/graph.smk"
include: "workflow/rules/compile.smk"
include: "workflow/rules/enumerate.smk"
include: "workflow/rules/compile_candidates.smk"
include: "workflow/rules/run_candidates.smk"
include: "workflow/rules/score_candidates.smk"
include: "workflow/rules/summarize.smk"

# Search pipeline (Optuna)
include: "workflow/rules/prepare_search.smk"
include: "workflow/rules/run_search.smk"
include: "workflow/rules/summarize_search.smk"
include: "workflow/rules/recommend.smk"
