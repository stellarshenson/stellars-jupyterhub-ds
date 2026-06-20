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
#   env               signup off + env-password admin (restart-to-provision on fresh DB)
#   signup-open       signup on + env-password admin authorises a self-signup
#   signup-bootstrap  signup on + NO env pw -> admin self-signup auto-authorised
#   traefik           Traefik + TLS front; /traefik dashboard route reached over HTTPS
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
TRAEFIK_OVERLAY=tests/functional/compose.functional-traefik.yml
GPUINFO_MOCK_IMAGE=stellars/duoptimum-gpuinfo-mock:latest
FUNCTEST_IMAGES="quay.io/jupyterhub/singleuser:latest mcr.microsoft.com/playwright/python:v1.49.0-noble"

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

# host has a usable NVIDIA GPU? -> autodetect mode for the default regime
detect_gpu() { if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then echo 1; else echo 0; fi; }

# boot hub -> (optional provision restart) -> run suite -> clean. ALWAYS cleans,
# returns the pytest exit code. $1 label, $2 GPU_ENABLED, $3 restart(0/1), rest -f files
run_regime() {
  local label=$1 gpu=$2 restart=$3; shift 3
  local cf=() f; for f in "$@"; do cf+=(-f "$f"); done
  local dc=(docker compose -p "$PROJECT" "${cf[@]}")
  local start; start=$(date +%s)
  echo "[functional/$label] booting isolated deployment ($PROJECT) [GPU_ENABLED=$gpu]..."
  if ! FUNCTEST_GPU_ENABLED=$gpu "${dc[@]}" up -d --wait duoptimum-hub; then clean; return 1; fi
  if [ "$restart" = 1 ]; then
    echo "[functional/$label] restarting hub to provision the env-password admin..."
    FUNCTEST_GPU_ENABLED=$gpu "${dc[@]}" restart duoptimum-hub
    FUNCTEST_GPU_ENABLED=$gpu "${dc[@]}" up -d --wait duoptimum-hub
  fi
  FUNCTEST_GPU_ENABLED=$gpu "${dc[@]}" run --rm tests
  local rc=$?
  clean
  echo "[functional/$label] total time (boot + tests + teardown): $(($(date +%s)-start))s; test-suite total is the pytest 'in Xs' line above"
  return $rc
}

# every regime in turn, cleaning between each; report which passed, non-zero if any failed
run_all() {
  local overall=0 failed="" setup
  for setup in signup gpu env signup-open signup-bootstrap traefik; do
    echo "==================================================================="
    echo "[functional/all] setup: $setup"
    echo "==================================================================="
    "$0" "$setup" || { overall=1; failed="$failed $setup"; }
  done
  echo "==================================================================="
  if [ "$overall" -eq 0 ]; then echo "[functional/all] ALL SETUPS PASSED"; else echo "[functional/all] FAILED SETUPS:$failed"; fi
  return $overall
}

case "${1:-signup}" in
  signup)           run_regime signup "$(detect_gpu)" 0 "$BASE" ;;
  gpu)
    echo "[functional/gpu] building mock gpuinfo image ($GPUINFO_MOCK_IMAGE)..."
    docker build -q -t "$GPUINFO_MOCK_IMAGE" tests/functional/mock_gpuinfo >/dev/null
    run_regime gpu 1 0 "$BASE" "$GPU_OVERLAY" ;;
  env)              run_regime env 0 1 "$BASE" "$ENV_OVERLAY" ;;
  signup-open)      run_regime signup-open 0 1 "$BASE" "$SIGNUPOPEN_OVERLAY" ;;
  signup-bootstrap) run_regime signup-bootstrap 0 0 "$BASE" "$SIGNUPBOOTSTRAP_OVERLAY" ;;
  traefik)          run_regime traefik 0 0 "$BASE" "$TRAEFIK_OVERLAY" ;;
  all)              run_all ;;
  clean)            clean ;;
  *) echo "run.sh: unknown regime '${1:-}' (signup|gpu|env|signup-open|signup-bootstrap|traefik|all|clean)" >&2; exit 2 ;;
esac
