#!/usr/bin/env bash
# Functional-test harness orchestrator (LOCAL ONLY). Boots an ISOLATED throwaway
# deployment (project stellars-functest), runs the Playwright suite in a
# `run --rm tests` container, then tears the harness down. Lives OUTSIDE the
# Makefile on purpose: a multi-line recipe with $(MAKE) in it ALSO runs under
# `make -n`, which silently executed the whole suite - the footgun that motivated
# this split. The make targets are now one-liners that call this.
#
# Boot is `up -d --wait duoptimum-hub` + `run --rm tests`, NOT
# `up --abort-on-container-exit`: some tests stop/restart the hub container (e.g.
# test_hub_unreachable); abort mode would kill the run the instant the hub exits.
#
# Usage: run.sh <regime>
#   signup            default - signup off + no env pw + fresh DB -> bootstrap window; GPU autodetect
#   gpu               GPU autodetect via a MOCK gpuinfo sidecar (runs on ANY host)
#   gpu-missing       GPU autodetect but the sidecar cannot start (absent image) -> GPU off, CPU-only lab (DEF-24)
#   env               signup off + env-password admin (restart-to-provision on fresh DB)
#   signup-open       signup on + env-password admin authorises a self-signup
#   signup-bootstrap  signup on + NO env pw -> admin self-signup auto-authorised
#   traefik           Traefik + TLS front; /traefik dashboard route reached over HTTPS (OPEN)
#   traefik-closed    same front, TRAEFIK_DASHBOARD_ENABLED=false; /traefik must be unreachable
#   all               every regime in turn; non-zero if any failed
#   clean             tear the harness down and exit
# Env: PYTEST_ARGS passed through to pytest (e.g. PYTEST_ARGS="-k redirect");
#      REMOVE_IMAGES=1 also removes pulled images on clean.

set -uo pipefail
cd "$(dirname "$0")/../.."   # repo root - compose -f paths are relative to it

PROJECT=stellars-functest
BASE=tests/functional/compose.functional.yml
ENV_OVERLAY=tests/functional/compose.functional-env.yml
SIGNUPOPEN_OVERLAY=tests/functional/compose.functional-signup-open.yml
SIGNUPBOOTSTRAP_OVERLAY=tests/functional/compose.functional-signup-bootstrap.yml
GPU_OVERLAY=tests/functional/compose.functional-gpu.yml
GPU_MISSING_OVERLAY=tests/functional/compose.functional-gpu-missing.yml
TRAEFIK_OVERLAY=tests/functional/compose.functional-traefik.yml
GPUINFO_MOCK_IMAGE=stellars/duoptimum-gpuinfo-mock:latest
FUNCTEST_IMAGES="quay.io/jupyterhub/singleuser:latest mcr.microsoft.com/playwright/python:v1.49.0-noble"
REPORTS_DIR=tests/functional/reports

# tear down everything the harness created - idempotent. gpuinfo-nvidia and the
# per-user functestadmin volumes are hub-created, not labelled with the project.
clean() {
  echo "[functional] cleaning harness (containers, network, volumes)..."
  docker compose -p "$PROJECT" -f "$BASE" down -v --remove-orphans >/dev/null 2>&1 || true
  docker ps -aq --filter "label=com.docker.compose.project=$PROJECT" | xargs -r docker rm -f >/dev/null 2>&1 || true
  docker rm -f gpuinfo-nvidia >/dev/null 2>&1 || true
  docker volume ls -q --filter "name=^${PROJECT}_" | xargs -r docker volume rm >/dev/null 2>&1 || true
  docker volume rm jupyterlab-functestadmin_home jupyterlab-functestadmin_workspace jupyterlab-functestadmin_cache >/dev/null 2>&1 || true
  docker network rm "${PROJECT}_network" >/dev/null 2>&1 || true
  [ -n "${REMOVE_IMAGES:-}" ] && docker rmi $FUNCTEST_IMAGES >/dev/null 2>&1 || true
  echo "[functional] cleanup complete (pulled images kept)"
}

# ── Results table ──────────────────────────────────────────────────────────
# Each regime appends one TSV record (label<TAB>result<TAB>tests<TAB>secs) to
# $RESULTS_FILE; _render_results_table draws a standardised box table with a
# TOTAL row. run_all owns the file (one table for the whole suite); a standalone
# regime owns its own (one-row table). Atomic test count = pytest passed+failed+errors.
_rep() { local n=$1 c=$2 s=''; while [ "$n" -gt 0 ]; do s="$s$c"; n=$((n-1)); done; printf '%s' "$s"; }

_record() { printf '%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" >> "$RESULTS_FILE"; }

_count_tests() {  # sum passed+failed+errors from the pytest summary in file $1
  local f=$1 p fa er
  p=$(grep -oE '[0-9]+ passed' "$f" | tail -1 | grep -oE '^[0-9]+'); p=${p:-0}
  fa=$(grep -oE '[0-9]+ failed' "$f" | tail -1 | grep -oE '^[0-9]+'); fa=${fa:-0}
  er=$(grep -oE '[0-9]+ error'  "$f" | tail -1 | grep -oE '^[0-9]+'); er=${er:-0}
  echo $((p + fa + er))
}

_render_results_table() {
  local file=$1
  [ -s "$file" ] || return 0
  local label result tests secs
  local w_label=6 w_res=6 w_tests=5 w_dur=8 tot_tests=0 tot_secs=0 overall=PASS
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
  printf '│ %-*s │ %-*s │ %*s │ %*s │\n' "$w_label" Regime "$w_res" Result "$w_tests" Tests "$w_dur" Duration
  printf '├%s┼%s┼%s┼%s┤\n' "$L" "$R" "$T" "$D"
  while IFS=$'\t' read -r label result tests secs; do
    printf '│ %-*s │ %-*s │ %*s │ %*s │\n' "$w_label" "$label" "$w_res" "$result" "$w_tests" "$tests" "$w_dur" "${secs}s"
  done < "$file"
  printf '├%s┼%s┼%s┼%s┤\n' "$L" "$R" "$T" "$D"
  printf '│ %-*s │ %-*s │ %*s │ %*s │\n' "$w_label" TOTAL "$w_res" "$overall" "$w_tests" "$tot_tests" "$w_dur" "$s_dur"
  printf '└%s┴%s┴%s┴%s┘\n' "$L" "$R" "$T" "$D"
}

# ── HTML sign-off report ─────────────────────────────────────────────────────
# EVERY run renders reports/signoff.html from the per-regime JSON sidecars the
# conftest writes (results + acceptance-criteria coverage) + the board TSV.
_reset_reports() { mkdir -p "$REPORTS_DIR"; rm -f "$REPORTS_DIR"/regime-*.json 2>/dev/null || true; }
_gen_report() {
  local board=$1 img
  img=$(docker image inspect stellars/duoptimum-hub:latest --format '{{.Id}}' 2>/dev/null | sed 's/sha256://' | cut -c1-19)
  python3 tests/functional/gen_signoff.py --board "$board" --reports-dir "$REPORTS_DIR" \
    --out "$REPORTS_DIR/signoff.html" --image "${img:-unknown}" \
    --timestamp "$(date '+%Y-%m-%d %H:%M:%S %Z')" \
    && echo "[functional] sign-off report -> $REPORTS_DIR/signoff.html"
}

# boot hub -> (optional provision restart) -> run suite -> clean. ALWAYS cleans,
# returns the pytest exit code. $1 label, $2 GPU_ENABLED, $3 restart(0/1), rest -f files
run_regime() {
  local label=$1 gpu=$2 restart=$3; shift 3
  local cf=() f; for f in "$@"; do cf+=(-f "$f"); done
  local dc=(docker compose -p "$PROJECT" "${cf[@]}")
  local own=0
  [ -z "${RESULTS_FILE:-}" ] && { RESULTS_FILE=$(mktemp); own=1; _reset_reports; }
  local start; start=$(date +%s)
  echo "[functional/$label] booting isolated deployment ($PROJECT) [GPU_ENABLED=$gpu]..."
  if ! FUNCTEST_GPU_ENABLED=$gpu "${dc[@]}" up -d --wait duoptimum-hub; then
    clean
    _record "$label" FAIL 0 "$(($(date +%s)-start))"
    [ "$own" = 1 ] && { _render_results_table "$RESULTS_FILE"; _gen_report "$RESULTS_FILE"; rm -f "$RESULTS_FILE"; }
    return 1
  fi
  if [ "$restart" = 1 ]; then
    echo "[functional/$label] restarting hub to provision the env-password admin..."
    FUNCTEST_GPU_ENABLED=$gpu "${dc[@]}" restart duoptimum-hub
    FUNCTEST_GPU_ENABLED=$gpu "${dc[@]}" up -d --wait duoptimum-hub
  fi
  local out; out=$(mktemp)
  FUNCTEST_GPU_ENABLED=$gpu FUNCTEST_REGIME=$label "${dc[@]}" run --rm tests 2>&1 | tee "$out"
  local rc=${PIPESTATUS[0]}
  clean
  local dur=$(($(date +%s)-start)) tests; tests=$(_count_tests "$out"); rm -f "$out"
  local result=PASS; [ "$rc" -eq 0 ] || result=FAIL
  _record "$label" "$result" "$tests" "$dur"
  echo "[functional/$label] $result - $tests tests in ${dur}s (boot + tests + teardown)"
  [ "$own" = 1 ] && { _render_results_table "$RESULTS_FILE"; _gen_report "$RESULTS_FILE"; rm -f "$RESULTS_FILE"; }
  return $rc
}

# every regime in turn, cleaning between each; report which passed, non-zero if any failed.
# Owns RESULTS_FILE (exported so each child regime appends its row), renders one table at the end.
run_all() {
  local overall=0 failed="" setup
  RESULTS_FILE=$(mktemp); export RESULTS_FILE
  _reset_reports
  for setup in signup gpu gpu-missing env signup-open signup-bootstrap traefik traefik-closed; do
    echo "==================================================================="
    echo "[functional/all] setup: $setup"
    echo "==================================================================="
    "$0" "$setup" || { overall=1; failed="$failed $setup"; }
  done
  echo "==================================================================="
  _render_results_table "$RESULTS_FILE"; _gen_report "$RESULTS_FILE"; rm -f "$RESULTS_FILE"
  if [ "$overall" -eq 0 ]; then echo "[functional/all] ALL SETUPS PASSED"; else echo "[functional/all] FAILED SETUPS:$failed"; fi
  return $overall
}

case "${1:-signup}" in
  signup)           run_regime signup 0 0 "$BASE" ;;   # GPU off: gpu-overlay tests (net/sidecar) belong to the gpu regime that adds the overlay
  gpu)
    echo "[functional/gpu] building mock gpuinfo image ($GPUINFO_MOCK_IMAGE)..."
    docker build -q -t "$GPUINFO_MOCK_IMAGE" tests/functional/mock_gpuinfo >/dev/null
    run_regime gpu 1 0 "$BASE" "$GPU_OVERLAY" ;;
  gpu-missing)
    # GPU autodetect ON but the gpuinfo image is absent -> sidecar self-start returns ""
    # -> GPU off, CPU-only lab. No mock image is built (absence is the point). DEF-24.
    run_regime gpu-missing 1 0 "$BASE" "$GPU_MISSING_OVERLAY" ;;
  env)              run_regime env 0 1 "$BASE" "$ENV_OVERLAY" ;;
  signup-open)      run_regime signup-open 0 1 "$BASE" "$SIGNUPOPEN_OVERLAY" ;;
  signup-bootstrap) run_regime signup-bootstrap 0 0 "$BASE" "$SIGNUPBOOTSTRAP_OVERLAY" ;;
  traefik)          run_regime traefik 0 0 "$BASE" "$TRAEFIK_OVERLAY" ;;
  traefik-closed)
    # toggle off: gate the dashboard router so /traefik is unreachable. Both vars are
    # exported so the docker-compose label/env ${...} interpolation picks them up.
    export TRAEFIK_DASHBOARD_ENABLED=false FUNCTEST_AUTH_MODE=traefikclosed
    run_regime traefik-closed 0 0 "$BASE" "$TRAEFIK_OVERLAY" ;;
  all)              run_all ;;
  clean)            clean ;;
  *) echo "run.sh: unknown regime '${1:-}' (signup|gpu|gpu-missing|env|signup-open|signup-bootstrap|traefik|traefik-closed|all|clean)" >&2; exit 2 ;;
esac
