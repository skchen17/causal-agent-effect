#!/usr/bin/env bash
# V0->V3 full-run serial driver (protocol section 9, Phase 3).
#
# - Launches each variant as a separate process and WAITS for it to exit
#   before starting the next one (strictly serial; one llama.cpp server at a
#   time, tensor_split 0.5/0.5 on both GPUs).
# - A failing variant does NOT skip the remaining variants (protocol Phase 3):
#   exit codes and completeness-check results are recorded in the manifest and
#   the failed variant is re-run later with --resume.
# - Read-only per-variant completeness check runs immediately after each
#   variant finishes; it never inspects comparative headline metrics.
set -u

PKG=/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package
PY="$PKG/runs/e75_agentdojo_env/bin/python"
RUNNER="$PKG/experiments/security-analysis-ablation-and-overhead/scripts/strict-atom-representation-attribution/run-strict-attribution.py"
CHECKER="$PKG/experiments/security-analysis-ablation-and-overhead/scripts/strict-atom-representation-attribution/check-variant-completeness.py"
RUNS_BASE="$PKG/experiments/security-analysis-ablation-and-overhead/runs/strict-atom-representation-attribution/qwen32"
MANIFEST="$RUNS_BASE/_v0v3_full_driver_manifest_2026-08-05.log"
PORT=18087
REPEAT=0

cd "$PKG"
mkdir -p "$RUNS_BASE"
echo "[driver] $(date -Is) start pid=$$" >> "$MANIFEST"

for VARIANT in tool_identity_only opaque_whole_call raw_schema_fields validated_atom_fields; do
  RUN_DIR="$RUNS_BASE/$VARIANT/repeat-$REPEAT"
  LOG="/tmp/v0v3-$VARIANT.log"
  echo "[driver] $(date -Is) LAUNCH variant=$VARIANT log=$LOG run_dir=$RUN_DIR" >> "$MANIFEST"
  PYTHONPATH=code:. "$PY" "$RUNNER" \
    --scope full --variant "$VARIANT" --repeat-index "$REPEAT" \
    --port "$PORT" --resume > "$LOG" 2>&1 &
  PID=$!
  echo "[driver] $(date -Is) RUNNING variant=$VARIANT pid=$PID" >> "$MANIFEST"
  echo "[driver] launched $VARIANT pid=$PID (log: $LOG)"
  wait "$PID"
  RC=$?
  echo "[driver] $(date -Is) EXIT variant=$VARIANT pid=$PID rc=$RC" >> "$MANIFEST"
  echo "[driver] $(date -Is) CHECK variant=$VARIANT begin" >> "$MANIFEST"
  PYTHONPATH=code:. "$PY" "$CHECKER" \
    --variant "$VARIANT" --scope full --repeat-index "$REPEAT" >> "$MANIFEST" 2>&1
  CRC=$?
  echo "[driver] $(date -Is) CHECK variant=$VARIANT rc=$CRC" >> "$MANIFEST"
  echo "[driver] $VARIANT exited rc=$RC, completeness check rc=$CRC"
done

echo "[driver] $(date -Is) all variants done" >> "$MANIFEST"
echo "[driver] all variants done; manifest: $MANIFEST"
