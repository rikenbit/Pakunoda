#!/bin/bash
# End-to-end Snakemake smoke test using real mwTensor solver.
# Run in Docker: docker run --rm --entrypoint bash pakunoda /app/tests/test_snakemake_e2e.sh
set -e
cd /app

echo "=== Snakemake end-to-end: real solver ==="
snakemake --snakefile Snakefile \
  --configfile examples/toy_heterogeneous/config.yaml \
  --cores 1 -q

OUTDIR=examples/toy_heterogeneous/results/toy_heterogeneous

echo ""
echo "=== Checking outputs ==="
PASS=0
FAIL=0

check_file() {
  if [ -f "$1" ]; then
    echo "  OK: $1"
    PASS=$((PASS+1))
  else
    echo "  MISSING: $1"
    FAIL=$((FAIL+1))
  fi
}

check_file "$OUTDIR/validate/report.json"
check_file "$OUTDIR/graph/relation_graph.json"
check_file "$OUTDIR/candidates/candidates.json"
check_file "$OUTDIR/candidates/compiled_manifest.json"
check_file "$OUTDIR/runs/run_manifest.json"
check_file "$OUTDIR/scores/score_manifest.json"
check_file "$OUTDIR/summary.json"
check_file "$OUTDIR/summary.tsv"

echo ""
echo "=== Summary table ==="
cat "$OUTDIR/summary.tsv"

echo ""
echo "=== Verifying real solver (not mock) ==="
python3 -c "
import json, sys, glob
for f in glob.glob('$OUTDIR/runs/*/result.json'):
    r = json.load(open(f))
    is_mock = r.get('mock', False)
    status = 'PASS' if r['success'] else 'FAIL: ' + str(r.get('error_message',''))
    solver = 'mock' if is_mock else 'REAL'
    print(f'  {r[\"candidate_id\"]}: {status} [{solver}] rec_error={r[\"reconstruction_error\"]}')
    if is_mock:
        print('  WARNING: running in mock mode, expected real solver')
        sys.exit(1)
print('All candidates used real mwTensor solver.')
"

echo ""
echo "========================================="
echo "Results: $PASS checks passed, $FAIL failed"
echo "========================================="

rm -rf examples/toy_heterogeneous/results .snakemake

[ $FAIL -eq 0 ]
