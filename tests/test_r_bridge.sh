#!/bin/bash
# Smoke test for run_candidate.R inside the Docker container.
# Run: docker run --rm --entrypoint bash pakunoda /app/tests/test_r_bridge.sh
set -e
cd /app

echo "=== Setup: generate problem JSONs ==="
snakemake --snakefile Snakefile --configfile examples/toy_heterogeneous/config.yaml \
  --cores 1 -q --until compile_candidates \
  --config "search={mock: true, max_rank: 2, allow_frozen_modes: true}"

CAND_DIR=examples/toy_heterogeneous/results/toy_heterogeneous/candidates
PASS=0
FAIL=0

run_test() {
  local NAME=$1
  local PROBLEM=$2
  local EXPECT=$3  # "success" or "fail"
  local OUTDIR="/tmp/r_test_$NAME"

  echo ""
  echo "=== Test: $NAME ($PROBLEM) ==="
  Rscript scripts/run_candidate.R "$PROBLEM" "$OUTDIR" 2>&1 || true

  if [ ! -f "$OUTDIR/result.json" ]; then
    if [ "$EXPECT" = "fail" ]; then
      echo "PASS (expected failure, no result.json produced — R stopped before tryCatch)"
      PASS=$((PASS+1))
      return
    fi
    echo "FAIL: no result.json produced"
    FAIL=$((FAIL+1))
    return
  fi

  python3 -c "
import json, sys
r = json.load(open('$OUTDIR/result.json'))
if '$EXPECT' == 'success':
    if not r['success']:
        print('FAIL:', r.get('error_message'))
        sys.exit(1)
    print('  rank:', r['rank'], 'init:', r.get('init_policy'), 'frozen:', r.get('num_frozen_factors', 0))
    print('  rec_error:', r['reconstruction_error'])
    print('PASS')
else:
    if r['success']:
        print('FAIL: expected failure but got success')
        sys.exit(1)
    print('  error:', r.get('error_message','')[:80])
    print('PASS (expected failure)')
"
  if [ $? -eq 0 ]; then
    PASS=$((PASS+1))
  else
    FAIL=$((FAIL+1))
  fi
}

# Test 1: 2-block candidate (find first non-frozen 2-block)
TWOB=$(python3 -c "
import json, glob
for f in sorted(glob.glob('$CAND_DIR/*.problem.json')):
    p = json.load(open(f))
    if len(p['tensors'])==2 and 'frozen' not in p['candidate_id']:
        print(f); break
")
run_test "2block" "$TWOB" "success"

# Test 2: 3-block candidate (find first non-frozen 3-block)
THREEB=$(python3 -c "
import json, glob
for f in sorted(glob.glob('$CAND_DIR/*.problem.json')):
    p = json.load(open(f))
    if len(p['tensors'])==3 and 'frozen' not in p['candidate_id']:
        print(f); break
")
run_test "3block" "$THREEB" "success"

# Test 3: frozen variant
FROZEN=$(python3 -c "
import json, glob
for f in sorted(glob.glob('$CAND_DIR/*.problem.json')):
    p = json.load(open(f))
    if 'frozen' in p['candidate_id']:
        print(f); break
")
run_test "frozen" "$FROZEN" "success"

# Test 4: nested rejection (fake problem)
python3 -c "
import json
p = json.load(open('$TWOB'))
p['nested_relations'] = [{'source': 'a:b', 'target': 'c:d', 'mapping': 'x.tsv'}]
json.dump(p, open('/tmp/nested_problem.json', 'w'))
"
run_test "nested_reject" "/tmp/nested_problem.json" "fail"

# Summary
echo ""
echo "========================================="
echo "Results: $PASS passed, $FAIL failed"
echo "========================================="

rm -rf examples/toy_heterogeneous/results .snakemake /tmp/r_test_* /tmp/nested_problem.json
[ $FAIL -eq 0 ]
