#!/bin/bash
# Smoke test for run_candidate.R inside the Docker container.
# Run from repo root:
#   docker run --rm -v $(pwd):/app -w /app pakunoda bash tests/test_r_bridge.sh
set -e

echo "=== R bridge smoke test ==="

# 1. Run the full pipeline in mock mode to generate problem JSONs
snakemake --snakefile /app/Snakefile \
  --configfile /app/examples/toy_heterogeneous/config.yaml \
  --cores 1 -q \
  --until compile_candidates

PROBLEM=/app/examples/toy_heterogeneous/results/toy_heterogeneous/candidates/c0_expression_methylation.problem.json
OUTDIR=/tmp/r_bridge_test

echo "=== Running R bridge on $PROBLEM ==="
Rscript /app/scripts/run_candidate.R "$PROBLEM" "$OUTDIR"

echo "=== Result ==="
cat "$OUTDIR/result.json"

# Check success
python3 -c "
import json, sys
r = json.load(open('$OUTDIR/result.json'))
if not r['success']:
    print('FAIL:', r.get('error_message'))
    sys.exit(1)
print('rank:', r['rank'])
print('reconstruction_error:', r['reconstruction_error'])
print('runtime:', r['runtime_seconds'])
print('PASS')
"

# Cleanup
rm -rf /app/examples/toy_heterogeneous/results /app/.snakemake "$OUTDIR"
echo "=== Done ==="
