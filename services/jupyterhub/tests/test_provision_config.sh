#!/usr/bin/env bash
# Functional tests for services/jupyterhub/conf/bin/start-platform.d/01_provision_config.sh
#
# The script under test selects between an operator overlay (/mnt/user_config) and a
# baked-in built-in (/srv/jupyterhub/jupyterhub_config.py), populating /srv/config
# every boot. This harness exercises every documented scenario by patching those
# three paths via sed onto a copy of the script and running it against tmp dirs.
#
# Exits non-zero on first failure (CI-friendly). Prints a brief summary at the end.

set -u
: "${BASH_VERSION:?bash required}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_UNDER_TEST="${SCRIPT_DIR}/../conf/bin/start-platform.d/01_provision_config.sh"

if [ ! -f "$SCRIPT_UNDER_TEST" ]; then
    echo "ERROR: script under test not found at $SCRIPT_UNDER_TEST" >&2
    exit 2
fi

bash -n "$SCRIPT_UNDER_TEST" || { echo "ERROR: script has syntax errors" >&2; exit 2; }

WORK="$(mktemp -d)"
trap 'chmod -R u+w "$WORK" 2>/dev/null; rm -rf "$WORK"' EXIT

BUILTIN_DIR="$WORK/builtin"
mkdir -p "$BUILTIN_DIR"
cat > "$BUILTIN_DIR/jupyterhub_config.py" <<'EOF'
# built-in sentinel for tests
BUILTIN = True
EOF

PASS=0
FAIL=0

# Run the script with $RUNTIME and $BUILTIN paths patched onto a tmp copy.
# Args: scenario-name user-config-dir user-config-file-name
# Echoes script stdout/stderr (prefixed) and returns the script's exit code.
run_script() {
    local name="$1" user_dir="$2" user_file="$3"
    local rt="$WORK/runtime_$name"
    rm -rf "$rt"
    mkdir -p "$rt"
    local patched="$WORK/script_$name.sh"
    sed -e "s|RUNTIME=\"/srv/config\"|RUNTIME=\"$rt\"|" \
        -e "s|BUILTIN=\"/srv/jupyterhub/jupyterhub_config.py\"|BUILTIN=\"$BUILTIN_DIR/jupyterhub_config.py\"|" \
        "$SCRIPT_UNDER_TEST" > "$patched"
    JUPYTERHUB_USER_CONFIG_DIR="$user_dir" \
    JUPYTERHUB_USER_CONFIG_FILE="$user_file" \
    bash "$patched" 2>&1 | sed "s/^/    /"
    return "${PIPESTATUS[0]}"
}

runtime_dir() { echo "$WORK/runtime_$1"; }

assert_exit() {
    local name="$1" expected="$2" actual="$3"
    if [ "$actual" -eq "$expected" ]; then
        echo "  PASS [$name] exit=$actual (expected $expected)"
        PASS=$((PASS + 1))
    else
        echo "  FAIL [$name] exit=$actual (expected $expected)" >&2
        FAIL=$((FAIL + 1))
        return 1
    fi
}

assert_contains_marker() {
    local name="$1" marker="$2"
    local rt
    rt="$(runtime_dir "$name")"
    if [ -f "$rt/jupyterhub_config.py" ] && grep -q "$marker" "$rt/jupyterhub_config.py"; then
        echo "  PASS [$name] runtime jupyterhub_config.py contains '$marker'"
        PASS=$((PASS + 1))
    else
        echo "  FAIL [$name] runtime jupyterhub_config.py missing '$marker'" >&2
        if [ -f "$rt/jupyterhub_config.py" ]; then
            echo "        actual content:" >&2
            sed 's/^/        /' "$rt/jupyterhub_config.py" >&2
        else
            echo "        runtime jupyterhub_config.py absent" >&2
        fi
        FAIL=$((FAIL + 1))
        return 1
    fi
}

assert_runtime_empty() {
    local name="$1"
    local rt
    rt="$(runtime_dir "$name")"
    if [ -z "$(ls -A "$rt" 2>/dev/null)" ]; then
        echo "  PASS [$name] runtime is empty (no copy on validation failure)"
        PASS=$((PASS + 1))
    else
        echo "  FAIL [$name] runtime is non-empty: $(ls -A "$rt")" >&2
        FAIL=$((FAIL + 1))
        return 1
    fi
}

assert_no_pycache() {
    local name="$1" dir="$2"
    if [ ! -d "$dir/__pycache__" ]; then
        echo "  PASS [$name] no __pycache__ written to $dir"
        PASS=$((PASS + 1))
    else
        echo "  FAIL [$name] __pycache__ leaked into $dir" >&2
        FAIL=$((FAIL + 1))
        return 1
    fi
}

# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

echo
echo "=== S1: /mnt/user_config absent => silent fallback to built-in ==="
run_script s1 "$WORK/nonexistent" "jupyterhub_config.py"
rc=$?
assert_exit s1 0 "$rc" && assert_contains_marker s1 "BUILTIN = True"

echo
echo "=== S2: only valid root file => operator config used ==="
mkdir -p "$WORK/s2"
echo "OPERATOR_S2 = True" > "$WORK/s2/jupyterhub_config.py"
run_script s2 "$WORK/s2" "jupyterhub_config.py"
rc=$?
assert_exit s2 0 "$rc" && assert_contains_marker s2 "OPERATOR_S2 = True"

echo
echo "=== S3: root + sibling helpers => all copied ==="
mkdir -p "$WORK/s3"
cat > "$WORK/s3/jupyterhub_config.py" <<'EOF'
from helpers import value
OPERATOR_S3 = value
EOF
echo "value = 42" > "$WORK/s3/helpers.py"
echo "extra = 'x'" > "$WORK/s3/auth.py"
run_script s3 "$WORK/s3" "jupyterhub_config.py"
rc=$?
assert_exit s3 0 "$rc"
rt="$(runtime_dir s3)"
for f in jupyterhub_config.py helpers.py auth.py; do
    if [ -f "$rt/$f" ]; then
        echo "  PASS [s3] sibling $f copied"
        PASS=$((PASS + 1))
    else
        echo "  FAIL [s3] sibling $f missing in $rt" >&2
        FAIL=$((FAIL + 1))
    fi
done

echo
echo "=== S4: only siblings (no root) => built-in fallback ==="
mkdir -p "$WORK/s4"
echo "noise = True" > "$WORK/s4/helpers.py"
run_script s4 "$WORK/s4" "jupyterhub_config.py"
rc=$?
assert_exit s4 0 "$rc" && assert_contains_marker s4 "BUILTIN = True"

echo
echo "=== S5: only yaml (no root) => built-in fallback ==="
mkdir -p "$WORK/s5"
echo "key: val" > "$WORK/s5/volumes_dictionary.yml"
run_script s5 "$WORK/s5" "jupyterhub_config.py"
rc=$?
assert_exit s5 0 "$rc" && assert_contains_marker s5 "BUILTIN = True"

echo
echo "=== S6: empty root => exit 1, no copy ==="
mkdir -p "$WORK/s6"
: > "$WORK/s6/jupyterhub_config.py"
run_script s6 "$WORK/s6" "jupyterhub_config.py"
rc=$?
assert_exit s6 1 "$rc" && assert_runtime_empty s6

echo
echo "=== S7: syntax error in root => exit 1, no copy, no __pycache__ on user dir ==="
mkdir -p "$WORK/s7"
echo "c.JupyterHub.bind_url = (" > "$WORK/s7/jupyterhub_config.py"
run_script s7 "$WORK/s7" "jupyterhub_config.py"
rc=$?
assert_exit s7 1 "$rc" && assert_runtime_empty s7
assert_no_pycache s7 "$WORK/s7"

echo
echo "=== S8: env-var override JUPYTERHUB_USER_CONFIG_FILE=my_cfg.py => alias jupyterhub_config.py written ==="
mkdir -p "$WORK/s8"
echo "OPERATOR_RENAMED = True" > "$WORK/s8/my_cfg.py"
run_script s8 "$WORK/s8" "my_cfg.py"
rc=$?
assert_exit s8 0 "$rc"
rt="$(runtime_dir s8)"
if [ -f "$rt/jupyterhub_config.py" ] && [ -f "$rt/my_cfg.py" ]; then
    if grep -q "OPERATOR_RENAMED = True" "$rt/jupyterhub_config.py"; then
        echo "  PASS [s8] aliased jupyterhub_config.py mirrors my_cfg.py content"
        PASS=$((PASS + 1))
    else
        echo "  FAIL [s8] aliased jupyterhub_config.py does not match my_cfg.py" >&2
        FAIL=$((FAIL + 1))
    fi
else
    echo "  FAIL [s8] expected both jupyterhub_config.py and my_cfg.py in $rt" >&2
    FAIL=$((FAIL + 1))
fi

echo
echo "=== S9: read-only user_config (production-realistic, valid root) => operator used ==="
mkdir -p "$WORK/s9"
echo "OPERATOR_S9 = True" > "$WORK/s9/jupyterhub_config.py"
chmod -R a-w "$WORK/s9"
run_script s9 "$WORK/s9" "jupyterhub_config.py"
rc=$?
assert_exit s9 0 "$rc" && assert_contains_marker s9 "OPERATOR_S9 = True"
assert_no_pycache s9 "$WORK/s9"
chmod -R u+w "$WORK/s9"

echo
echo "=== S10: read-only user_config + syntax error => exit 1, no __pycache__ leakage ==="
mkdir -p "$WORK/s10"
echo "def broken(:" > "$WORK/s10/jupyterhub_config.py"
chmod -R a-w "$WORK/s10"
run_script s10 "$WORK/s10" "jupyterhub_config.py"
rc=$?
assert_exit s10 1 "$rc" && assert_runtime_empty s10
assert_no_pycache s10 "$WORK/s10"
chmod -R u+w "$WORK/s10"

echo
echo "=== S11: stale runtime contents wiped on every boot ==="
# Pre-populate runtime with a stale operator file, then run with no operator overlay -> built-in
rt="$(runtime_dir s11)"
rm -rf "$rt"; mkdir -p "$rt"
echo "STALE = True" > "$rt/jupyterhub_config.py"
echo "STALE_HELPER = True" > "$rt/old_helper.py"
patched="$WORK/script_s11.sh"
sed -e "s|RUNTIME=\"/srv/config\"|RUNTIME=\"$rt\"|" \
    -e "s|BUILTIN=\"/srv/jupyterhub/jupyterhub_config.py\"|BUILTIN=\"$BUILTIN_DIR/jupyterhub_config.py\"|" \
    "$SCRIPT_UNDER_TEST" > "$patched"
JUPYTERHUB_USER_CONFIG_DIR="$WORK/nonexistent" \
JUPYTERHUB_USER_CONFIG_FILE="jupyterhub_config.py" \
bash "$patched" 2>&1 | sed "s/^/    /"
rc="${PIPESTATUS[0]}"
assert_exit s11 0 "$rc" && assert_contains_marker s11 "BUILTIN = True"
if [ ! -f "$rt/old_helper.py" ]; then
    echo "  PASS [s11] stale sibling old_helper.py wiped"
    PASS=$((PASS + 1))
else
    echo "  FAIL [s11] stale sibling old_helper.py persisted across boots" >&2
    FAIL=$((FAIL + 1))
fi

echo
echo "============================================================"
echo "  Tests passed: $PASS"
echo "  Tests failed: $FAIL"
echo "============================================================"

[ "$FAIL" -eq 0 ]
