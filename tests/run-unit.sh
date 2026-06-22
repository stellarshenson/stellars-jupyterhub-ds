#!/usr/bin/env bash
# Unit-test runner with a standardised results table (mirrors tests/functional/run.sh).
# Runs each python unit suite as a "part", capturing result + atomic test count (pytest
# passed+failed+errors) + wall-clock duration, then renders a box table with a TOTAL row.
#
# Usage: run-unit.sh            run every suite, print the table, non-zero if any failed
#        PYTEST_ARGS=... run-unit.sh   pass extra args through to pytest (e.g. -k name)

set -uo pipefail
cd "$(dirname "$0")/.."   # repo root - suite dirs are relative to it

# label:dir - one pytest invocation per entry (the "parts" of the unit suite)
SUITES=(
  "duoptimum-hub-services:services/jupyterhub/duoptimum-hub-services"
  "duoptimum-docker-proxy:services/jupyterhub/duoptimum-docker-proxy"
)

_rep() { local n=$1 c=$2 s=''; while [ "$n" -gt 0 ]; do s="$s$c"; n=$((n-1)); done; printf '%s' "$s"; }

_count_tests() {  # sum passed+failed+errors from the pytest summary in file $1
  local f=$1 p fa er
  p=$(grep -oE '[0-9]+ passed' "$f" | tail -1 | grep -oE '^[0-9]+'); p=${p:-0}
  fa=$(grep -oE '[0-9]+ failed' "$f" | tail -1 | grep -oE '^[0-9]+'); fa=${fa:-0}
  er=$(grep -oE '[0-9]+ error'  "$f" | tail -1 | grep -oE '^[0-9]+'); er=${er:-0}
  echo $((p + fa + er))
}

# render a box table from TSV records (label<TAB>result<TAB>tests<TAB>secs) in $1
_render_results_table() {
  local file=$1
  [ -s "$file" ] || return 0
  local label result tests secs
  local w_label=5 w_res=6 w_tests=5 w_dur=8 tot_tests=0 tot_secs=0 overall=PASS
  while IFS=$'\t' read -r label result tests secs; do
    [ "${#label}" -gt "$w_label" ] && w_label=${#label}
    tot_tests=$((tot_tests + tests)); tot_secs=$((tot_secs + secs))
    [ "$result" = PASS ] || overall=FAIL
  done < "$file"
  local s_tests="$tot_tests" s_dur="${tot_secs}s"
  [ "${#s_tests}" -gt "$w_tests" ] && w_tests=${#s_tests}
  [ "${#s_dur}"   -gt "$w_dur"   ] && w_dur=${#s_dur}
  local L R T D
  L=$(_rep $((w_label+2)) ─); R=$(_rep $((w_res+2)) ─); T=$(_rep $((w_tests+2)) ─); D=$(_rep $((w_dur+2)) ─)
  echo
  printf '┌%s┬%s┬%s┬%s┐\n' "$L" "$R" "$T" "$D"
  printf '│ %-*s │ %-*s │ %*s │ %*s │\n' "$w_label" Suite "$w_res" Result "$w_tests" Tests "$w_dur" Duration
  printf '├%s┼%s┼%s┼%s┤\n' "$L" "$R" "$T" "$D"
  while IFS=$'\t' read -r label result tests secs; do
    printf '│ %-*s │ %-*s │ %*s │ %*s │\n' "$w_label" "$label" "$w_res" "$result" "$w_tests" "$tests" "$w_dur" "${secs}s"
  done < "$file"
  printf '├%s┼%s┼%s┼%s┤\n' "$L" "$R" "$T" "$D"
  printf '│ %-*s │ %-*s │ %*s │ %*s │\n' "$w_label" TOTAL "$w_res" "$overall" "$w_tests" "$tot_tests" "$w_dur" "$s_dur"
  printf '└%s┴%s┴%s┴%s┘\n' "$L" "$R" "$T" "$D"
}

RESULTS_FILE=$(mktemp)
overall=0
for entry in "${SUITES[@]}"; do
  label=${entry%%:*}; dir=${entry#*:}
  echo "==================================================================="
  echo "[unit/$label] running pytest..."
  echo "==================================================================="
  out=$(mktemp); start=$(date +%s)
  ( cd "$dir" && python3 -m pytest tests/ -q ${PYTEST_ARGS:-} ) 2>&1 | tee "$out"
  rc=${PIPESTATUS[0]}
  dur=$(($(date +%s)-start)); tests=$(_count_tests "$out"); rm -f "$out"
  result=PASS; [ "$rc" -eq 0 ] || { result=FAIL; overall=1; }
  printf '%s\t%s\t%s\t%s\n' "$label" "$result" "$tests" "$dur" >> "$RESULTS_FILE"
  echo "[unit/$label] $result - $tests tests in ${dur}s"
done
_render_results_table "$RESULTS_FILE"; rm -f "$RESULTS_FILE"
exit $overall
