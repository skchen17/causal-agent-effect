#!/usr/bin/env bash
# V0-resume finalizer watch (2026-08-06).
#
# Purpose: wait for the V0 (tool_identity_only) RESUME run to finish, then
# chain the protocol-v2 resume sequence automatically, fail-closed at every
# gate. Follows the v17r2_finalizer_watch.sh pattern and
# paper/current-usenix/pause-resume-runbook_2026-08-05.md.
#
# Chain after V0 completion:
#   1. V0 row-count gate (must be exactly 726).
#   2. Read-only completeness check for V0 (rc=0 required).
#   3. RESTORE protocol.json to protocol v2 bytes (sha256-verified from the
#      backup made at swap time). During the V0 resume window protocol.json
#      held the v1 bytes so that rows 394-726 carry the v1 protocol_id
#      bccf19ea51b13f27, keeping the 726-row file homogeneous (the
#      completeness checker treats protocol_id as a frozen hash field that
#      must agree across all rows).
#   4. Runbook section 2 gates: pytest (51 tests) + envelope --check +
#      smoke dry-run expecting protocol_id e830b9b24138f8ad.
#   5. GPU-idle confirmation (no llama_cpp.server leftover).
#   6. Pause record JSON (pause-after-v0.sh step 6 analog; the driver/V1
#      termination steps of pause-after-v0.sh are not applicable here: the
#      resume runner was launched standalone, and no V1 runner exists).
#   7. smoke-v2: four variants serial, --repeat-index 1 (repeat-1 dirs; never
#      touches the V0 repeat-0 file; runbook section 3).
#   8. driver v2: V1->V2->V3 full serial (runbook section 4).
#
# This script never kills the V0 runner, never adds GPU concurrency, and
# never mutates the V0 results file.
set -u

PKG=/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package
PY="$PKG/runs/e75_agentdojo_env/bin/python"
SCRIPTS="$PKG/experiments/security-analysis-ablation-and-overhead/scripts/strict-atom-representation-attribution"
RUNNER="$SCRIPTS/run-strict-attribution.py"
CHECKER="$SCRIPTS/check-variant-completeness.py"
EVAL_DIR="$PKG/experiments/security-analysis-ablation-and-overhead/evaluation/strict-atom-representation-attribution"
QWEN_BASE="$PKG/experiments/security-analysis-ablation-and-overhead/runs/strict-atom-representation-attribution/qwen32"
V0_RESULTS="$QWEN_BASE/tool_identity_only/repeat-0/paired-case-results.jsonl"
LOG="$PKG/v0_resume_watch_2026-08-06.log"
V2_BACKUP="$EVAL_DIR/protocol-v2-backup_2026-08-06.json"
V2_EXPECTED=e830b9b24138f8ad5ac6cafbfa101dc4e9734765b2bb043eff3e32eb29319f22
V1_EXPECTED_ID=bccf19ea51b13f27
V2_EXPECTED_ID=e830b9b24138f8ad
PORT=18087

log() { echo "[v0-watch] $(date -Is) $*" >> "$LOG"; }
abort() { log "ABORT: $1"; echo "[v0-watch] ABORT: $1" >&2; exit 1; }

log "watch started (waiting for V0 resume runner)"

# --- Phase 0: wait for the V0 resume runner to exit (poll every 3 min) -----
for i in $(seq 1 1000); do
  # Anchored pattern: match ONLY the python runner process, never the
  # orphaned nohup wrapper shell whose cmdline contains the same text.
  if ! pgrep -f "^runs/e75_agentdojo_env/bin/python experiments/.*run-strict-attribution.py --scope full" > /dev/null 2>&1; then
    log "V0 resume runner exited (poll $i)"
    break
  fi
  sleep 180
done

# Wait for the llama.cpp server to release the GPUs (runner's finally block
# SIGTERMs it; give it time).
for i in $(seq 1 120); do
  if ! pgrep -f "llama_cpp.server.*$PORT" > /dev/null 2>&1; then
    log "llama_cpp server on $PORT exited (poll $i)"
    break
  fi
  sleep 30
done
sleep 30
cd "$PKG" || abort "cannot cd to package root"

# --- Phase 1: V0 completeness gate ------------------------------------------
ROWS=$(wc -l < "$V0_RESULTS" 2>/dev/null || echo 0)
log "V0 rows=$ROWS"
[ "$ROWS" -eq 726 ] || abort "V0 has $ROWS/726 rows; do NOT proceed (inspect /tmp/v0-resume.log; re-run with --resume if needed)"

PYTHONPATH=code:. "$PY" "$CHECKER" --variant tool_identity_only --scope full --repeat-index 0 >> "$LOG" 2>&1
[ $? -eq 0 ] || abort "V0 completeness check failed (report above); investigate before any next step"
log "V0 completeness check PASS (726 rows, homogeneous frozen fields incl. protocol_id=$V1_EXPECTED_ID)"

# --- Phase 2: restore protocol.json to v2 (sha256-verified) -----------------
[ -f "$V2_BACKUP" ] || abort "missing $V2_BACKUP"
BACKUP_HASH=$(sha256sum "$V2_BACKUP" | cut -d' ' -f1)
[ "$BACKUP_HASH" = "$V2_EXPECTED" ] || abort "v2 backup hash $BACKUP_HASH != expected $V2_EXPECTED"
cp "$V2_BACKUP" "$EVAL_DIR/protocol.json"
RESTORED=$(sha256sum "$EVAL_DIR/protocol.json" | cut -d' ' -f1)
[ "$RESTORED" = "$V2_EXPECTED" ] || abort "protocol.json restore verification failed ($RESTORED)"
log "protocol.json restored to protocol v2 (sha256=$RESTORED)"

# --- Phase 3: runbook section 2 pre-restart gates ---------------------------
PYTHONPATH=code:. "$PY" -m pytest shared/compatibility/tests/tests/test_strict_atom_representation_attribution.py -q >> "$LOG" 2>&1
[ $? -eq 0 ] || abort "pytest gate failed (51-test suite)"
log "pytest gate PASS"

PYTHONPATH=code:. "$PY" "$SCRIPTS/build-whole-call-envelopes.py" --check >> "$LOG" 2>&1
[ $? -eq 0 ] || abort "envelope --check gate failed"
log "envelope --check PASS"

PYTHONPATH=code:. "$PY" "$RUNNER" --scope smoke --variants all --dry-run > /tmp/v0-watch-smoke-dryrun.json 2>&1
[ $? -eq 0 ] || abort "smoke dry-run refused (see /tmp/v0-watch-smoke-dryrun.json)"
grep -q "\"protocol_id\": \"$V2_EXPECTED_ID\"" /tmp/v0-watch-smoke-dryrun.json || abort "smoke dry-run protocol_id is not $V2_EXPECTED_ID"
log "smoke dry-run PASS under protocol v2 ($V2_EXPECTED_ID)"

if pgrep -f "llama_cpp.server" > /dev/null 2>&1; then
  abort "unexpected llama_cpp.server still present after V0; GPU not clean"
fi
log "GPU clean (no llama_cpp.server)"

# --- Phase 4: pause record (pause-after-v0.sh step 6 analog) ----------------
RECORD="$QWEN_BASE/_resume_record_protocol_v2_2026-08-06.json"
cat > "$RECORD" <<EOF
{
  "record_type": "protocol_v2_v0_resume_complete",
  "timestamp_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "v0_results": "$V0_RESULTS",
  "v0_rows": $ROWS,
  "v0_completeness_check": "PASS",
  "v0_protocol_id": "$V1_EXPECTED_ID",
  "v0_resume_note": "rows 1-393 produced by original v1 driver (2026-08-05); rows 394-726 produced by --resume (2026-08-06) under protocol.json temporarily restored to v1 bytes so all 726 rows carry $V1_EXPECTED_ID; protocol.json then restored to v2 ($V2_EXPECTED_ID)",
  "protocol_json_current": "$V2_EXPECTED_ID",
  "next_step": "smoke-v2 (repeat-index 1) then driver v2 (V1->V2->V3)"
}
EOF
log "resume record written: $RECORD"

# --- Phase 5: smoke-v2 (four variants serial, repeat-index 1) ---------------
SMOKE_MANIFEST="$QWEN_BASE/_smoke_v2_rerun_manifest_2026-08-05.log"
echo "[smoke-v2] $(date -Is) start (four variants serial, repeat-index 1; launched by v0-resume watch)" >> "$SMOKE_MANIFEST"
log "smoke-v2 start (repeat-index 1)"
SMOKE_OK=1
for V in tool_identity_only opaque_whole_call raw_schema_fields validated_atom_fields; do
  echo "[smoke-v2] $(date -Is) LAUNCH $V" >> "$SMOKE_MANIFEST"
  PYTHONPATH=code:. "$PY" "$RUNNER" --scope smoke --variants "$V" \
    --repeat-index 1 --port "$PORT" >> "/tmp/smoke-v2-$V.log" 2>&1
  RC=$?
  PYTHONPATH=code:. "$PY" "$CHECKER" --variant "$V" --scope smoke --repeat-index 1 >> "$SMOKE_MANIFEST" 2>&1
  CRC=$?
  echo "[smoke-v2] $(date -Is) $V runner_rc=$RC check_rc=$CRC" >> "$SMOKE_MANIFEST"
  log "smoke-v2 variant=$V runner_rc=$RC check_rc=$CRC"
  if [ "$RC" -ne 0 ] || [ "$CRC" -ne 0 ]; then
    log "smoke-v2 FAILED at $V; NOT starting driver v2 (investigate /tmp/smoke-v2-$V.log)"
    SMOKE_OK=0
    break
  fi
done
[ "$SMOKE_OK" -eq 1 ] || abort "smoke-v2 failed; full runs must not start"
echo "[smoke-v2] $(date -Is) ALL FOUR VARIANTS PASSED" >> "$SMOKE_MANIFEST"
log "smoke-v2 ALL FOUR VARIANTS PASSED"

# --- Phase 6: driver v2 (V1 -> V2 -> V3 serial; own preflight re-verifies) --
log "launching driver v2"
bash "$SCRIPTS/run-v0v3-full-serial-driver-v2.sh" > /tmp/driver-v2.log 2>&1
DRC=$?
log "driver v2 exited rc=$DRC (log: /tmp/driver-v2.log, manifest: $QWEN_BASE/_v1v3_full_driver_v2_protocol_v2_manifest_2026-08-05.log)"
exit $DRC
