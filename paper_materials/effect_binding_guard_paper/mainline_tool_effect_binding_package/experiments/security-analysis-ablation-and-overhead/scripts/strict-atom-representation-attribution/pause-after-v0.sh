#!/usr/bin/env bash
# Protocol v2 PAUSE GATE (D2): controlled stop of the protocol-v1 serial
# driver AFTER the V0 full run is complete.
#
# Order of operations (fail-closed at every gate):
#   1. V0 results must have exactly 726 rows (else: refuse, V0 not done).
#   2. Read-only completeness check for V0 must pass (rc=0).
#   3. Driver manifest must contain the driver's own CHECK rc=0 line (warn if
#      absent; the local check in step 2 is authoritative).
#   4. If a V1 (opaque_whole_call) runner is already running under the v1
#      protocol: terminate the DRIVER FIRST (so it cannot launch more work),
#      then terminate the V1 runner, wait, and ARCHIVE the partial V1 run
#      directory (protocol v1 V1 semantics are invalidated by protocol v2).
#   5. Otherwise terminate the driver.
#   6. Write a pause record JSON and print the resume pointer.
#
# Usage:
#   bash experiments/security-analysis-ablation-and-overhead/scripts/\
#   strict-atom-representation-attribution/pause-after-v0.sh [DRIVER_PID]
#   (default DRIVER_PID=1448380)
#
# This script does NOT start any GPU process and does NOT touch the V0 run
# directory contents.
set -u

PKG=/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package
PY="$PKG/runs/e75_agentdojo_env/bin/python"
CHECKER="$PKG/experiments/security-analysis-ablation-and-overhead/scripts/strict-atom-representation-attribution/check-variant-completeness.py"
RUNS_BASE="$PKG/experiments/security-analysis-ablation-and-overhead/runs/strict-atom-representation-attribution"
QWEN_BASE="$RUNS_BASE/qwen32"
V0_RESULTS="$QWEN_BASE/tool_identity_only/repeat-0/paired-case-results.jsonl"
MANIFEST="$QWEN_BASE/_v0v3_full_driver_manifest_2026-08-05.log"
DRIVER_PID="${1:-1448380}"
EXPECTED_ROWS=726
ARCHIVE="$RUNS_BASE/_archive_v1_partial_protocol_v1_interrupted_2026-08-05"
RECORD="$QWEN_BASE/_pause_record_protocol_v2_2026-08-05.json"

fail() { echo "[pause] REFUSED: $1" >&2; exit 1; }

cd "$PKG"

# --- Gate 1: V0 row count ---------------------------------------------------
[ -f "$V0_RESULTS" ] || fail "missing $V0_RESULTS"
ROWS=$(wc -l < "$V0_RESULTS")
[ "$ROWS" -eq "$EXPECTED_ROWS" ] || fail "V0 has $ROWS/$EXPECTED_ROWS rows; wait for V0 to finish (do not interrupt)"

# --- Gate 2: read-only completeness check -----------------------------------
echo "[pause] running read-only completeness check for V0 ..."
PYTHONPATH=code:. "$PY" "$CHECKER" --variant tool_identity_only --scope full --repeat-index 0
[ $? -eq 0 ] || fail "V0 completeness check failed; inspect the report above before pausing"

# --- Gate 3: driver manifest CHECK line (informational) ---------------------
MANIFEST_CHECK="absent"
if [ -f "$MANIFEST" ] && grep -q "CHECK variant=tool_identity_only rc=0" "$MANIFEST"; then
  MANIFEST_CHECK="rc=0 recorded"
fi
echo "[pause] driver manifest CHECK line: $MANIFEST_CHECK"

# --- Gate 4/5: terminate driver (first) and possibly the V1 runner ----------
V1_ARCHIVED="none"
V1_ROWS=0
if kill -0 "$DRIVER_PID" 2>/dev/null; then
  echo "[pause] terminating v1 driver pid=$DRIVER_PID (SIGTERM)"
  kill -TERM "$DRIVER_PID" || fail "could not signal driver pid=$DRIVER_PID"
  for _ in 1 2 3 4 5 6; do
    kill -0 "$DRIVER_PID" 2>/dev/null || break
    sleep 5
  done
  if kill -0 "$DRIVER_PID" 2>/dev/null; then
    echo "[pause] driver still alive after 30s; sending SIGKILL"
    kill -KILL "$DRIVER_PID" || true
  fi
else
  echo "[pause] driver pid=$DRIVER_PID already exited"
fi

V1_RUNNER_PIDS=$(pgrep -f "run-strict-attribution.py --scope full --variant opaque_whole_call" || true)
if [ -n "$V1_RUNNER_PIDS" ]; then
  V1_DIR="$QWEN_BASE/opaque_whole_call/repeat-0"
  if [ -f "$V1_DIR/paired-case-results.jsonl" ]; then
    V1_ROWS=$(wc -l < "$V1_DIR/paired-case-results.jsonl")
  fi
  echo "[pause] V1 runner running under protocol v1 (pids: $V1_RUNNER_PIDS, rows=$V1_ROWS); terminating and archiving"
  for PID in $V1_RUNNER_PIDS; do kill -TERM "$PID" || true; done
  sleep 20
  for PID in $V1_RUNNER_PIDS; do
    if kill -0 "$PID" 2>/dev/null; then kill -KILL "$PID" || true; fi
  done
  # The runner's finally-block SIGTERMs its own llama.cpp server; verify.
  sleep 10
  if pgrep -f "llama_cpp.server" >/dev/null; then
    echo "[pause] WARNING: a llama_cpp.server process is still present; verify it belongs to this experiment before continuing"
  fi
  if [ -d "$V1_DIR" ]; then
    mkdir -p "$ARCHIVE"
    mv "$V1_DIR" "$ARCHIVE/opaque_whole_call-repeat-0"
    V1_ARCHIVED="$ARCHIVE/opaque_whole_call-repeat-0"
  fi
else
  echo "[pause] no V1 runner running; nothing to archive"
fi

# --- Step 6: pause record ----------------------------------------------------
cat > "$RECORD" <<EOF
{
  "record_type": "protocol_v2_pause",
  "timestamp_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "driver_pid": $DRIVER_PID,
  "v0_results": "$V0_RESULTS",
  "v0_rows": $ROWS,
  "v0_completeness_check": "PASS",
  "v0_protocol_id": "bccf19ea51b13f27",
  "driver_manifest_check_line": "$MANIFEST_CHECK",
  "v1_runner_rows_at_pause": $V1_ROWS,
  "v1_partial_archive": "$V1_ARCHIVED",
  "next_step": "paper/current-usenix/pause-resume-runbook_2026-08-05.md (resume: four-variant smoke rerun under protocol v2, then driver v2 from V1)"
}
EOF
echo "[pause] pause record written: $RECORD"
echo "[pause] DONE. Resume per paper/current-usenix/pause-resume-runbook_2026-08-05.md"
